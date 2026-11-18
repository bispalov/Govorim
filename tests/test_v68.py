# v68: обучение — настоящие нажатия, подгонка прокрутки, сжатие окна
import json, os, shutil, threading, http.server, functools
from playwright.sync_api import sync_playwright
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
window.__spoken=[];window.__recStarts=0;window.__speaking=false;
const ss={cancel(){window.__speaking=false},speak(u){window.__spoken.push(u.text);window.__speaking=true;setTimeout(()=>{window.__speaking=false;u.onend&&u.onend()},30)},get speaking(){return window.__speaking},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
class FakeSR{start(){window.__recStarts++}stop(){}abort(){}};window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
window.confirm=()=>true;
"""
results = []; errors = []
def check(n, c):
    results.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n)
def page(b, ls, W, H):
    ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H}, has_touch=False)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(STUB + "if(!sessionStorage.__i){" + ''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in ls.items()) + "}sessionStorage.__i=1;")
    pg.goto(URL); pg.wait_for_timeout(250); return pg
touring = lambda pg: pg.evaluate("TOUR?TOUR.scr:null")
step = lambda pg: pg.evaluate("TOUR&&TOUR.cur?TOUR.cur.t:null")
VIS = r"""(()=>{
  if(!TOUR||!TOUR.els.length)return null;
  const els=TOUR.els.filter(e=>e.isConnected);if(!els.length)return {gone:true};
  const r=tourRect(els),st=document.querySelector('#stage').getBoundingClientRect(),box=document.querySelector('#tourBox').getBoundingClientRect();
  const inter=(a,b)=>!(a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top);
  const fixed=els.some(e=>e.closest('#bar')||e.closest('header'));
  const tall=r.height>st.height-8;
  const onScreen=fixed||(tall?r.top>=st.top-1&&r.top<st.bottom:r.top>=st.top-1&&r.bottom<=st.bottom+1);
  const fitsBoth=r.height+box.height+12<=st.height-8;
  return {onScreen,covered:fitsBoth&&inter(r,box),r:[Math.round(r.top),Math.round(r.bottom)],st:[Math.round(st.top),Math.round(st.bottom)]};
})()"""
def click_center(pg, sel_js):
    bx = pg.evaluate(f"(()=>{{const e={sel_js};if(!e)return null;e.scrollIntoView({{block:'nearest'}});const r=e.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]}})()")
    if bx: pg.mouse.click(bx[0], bx[1])
    return bx

with sync_playwright() as p:
    b = p.chromium.launch()
    for L in ['uk', 'ru']:
        for W, H in [(360, 640), (277, 492), (800, 1280)]:
            tag = f'{L} {W}x{H}'
            pg = page(b, {'aac.lang': L, 'aac.settings': json.dumps({'level': 'L2', 'quick': False})}, W, H)
            bad = []
            def human(scr):
                # предложение → «Да» → по шагам; на шаге wait нажимаем подсвеченное, ждём 2 с и проверяем область
                pg.wait_for_timeout(900)
                if not pg.evaluate("!!(TOUR&&TOUR.scr==='offer')"): bad.append((scr, 'no offer')); return
                pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(150)
                n = 0
                while touring(pg) == scr and n < 12:
                    st = step(pg)
                    if pg.evaluate('TOUR.waitNow'):
                        click_center(pg, "TOUR.els[0].querySelector('.tile')||TOUR.els[0]")
                        pg.wait_for_timeout(2000)
                        v = pg.evaluate(VIS)
                        if v and not v.get('gone') and (not v['onScreen'] or v['covered']): bad.append((scr, step(pg), 'after tap', v))
                    else:
                        pg.wait_for_timeout(250)
                        v = pg.evaluate(VIS)
                        if v and not v.get('gone') and (not v['onScreen'] or v['covered']): bad.append((scr, st, v))
                        # искусственно уводим прокрутку в конец — область должна вернуться
                        if n == 0 and pg.evaluate("!!(TOUR&&TOUR.els.length&&tourScrollable(TOUR.els))"):
                            pg.evaluate("document.querySelector('#main').scrollTop=1e6"); pg.wait_for_timeout(300)
                            v2 = pg.evaluate(VIS)
                            if v2 and not v2.get('gone') and not v2['onScreen']: bad.append((scr, st, 'scrolled away', v2))
                        if touring(pg) == scr: pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(120)
                    n += 1
            human('home')
            pg.evaluate("tourEnd()")
            # раздел плиток (плитка с вопросом «…?»)
            pg.evaluate("closeOv();path=[tree.find(n=>n.c&&n.c.some(x=>!x.c&&!x.crit))];render()")
            human('tiles'); pg.evaluate("tourEnd();closeOv()")
            pg.evaluate("path=[];render()")
            # 🎤 «Говорить людина» с собранной фразой
            pg.evaluate("hearTab='sug';settings.hearTab='sug';hearBuild=['я','хочу','пити'];hearOpen=true;openHear()")
            human('hear'); pg.evaluate("tourEnd()")
            pg.evaluate("hearTab='show';settings.hearTab='show';render();showShow('Я скоро прийду, чекай на мене вдома',false)")
            human('show'); pg.evaluate("tourEnd()")
            pg.evaluate("abcOpen()"); human('abc'); pg.evaluate("tourEnd()")
            check(f'{tag}: human path — area visible and not covered on every step', not bad)
            if bad: print('   ', bad[:5])
            check(f'{tag}: microphone never started', pg.evaluate('window.__recStarts') == 0)
            pg.context.close()

    # нажатие внутри области на шаге без ожидания: окно сжато, нажатие сработало
    pg = page(b, {'aac.lang': 'uk', 'aac.tour.seen': json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})}, 360, 640)
    pg.evaluate("abcOpen()"); pg.wait_for_timeout(100)
    pg.evaluate("tourStart('abc')"); pg.wait_for_timeout(150)
    check('abc step 1 is letters, not waiting', step(pg) == 'a_kb' and not pg.evaluate('TOUR.waitNow'))
    full_h = pg.evaluate("document.querySelector('#tourBox').offsetHeight")
    click_center(pg, "document.querySelector('.kb .letters .lt')"); pg.wait_for_timeout(200)
    check('tap inside area works (letter chosen)', pg.evaluate('abc.prefix.length') == 1)
    check('box shrinks to buttons', pg.evaluate("document.querySelector('#tourBox').classList.contains('compact')") and pg.evaluate("document.querySelector('#tourBox').offsetHeight") < full_h)
    check('tutorial still on (elements re-found after render)', touring(pg) == 'abc' and pg.evaluate("TOUR.els.every(e=>e.isConnected)"))
    pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(150)
    check('next step: box full again', not pg.evaluate("document.querySelector('#tourBox').classList.contains('compact')"))
    pg.evaluate('tourEnd()')
    # опасные кнопки по-прежнему не срабатывают
    pg.click('#home'); pg.evaluate("tourStart('home')"); pg.wait_for_timeout(100)
    while step(pg) != 'h_sos': pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(60)
    pg.locator('#bar button[data-k=help]').click(force=True); pg.wait_for_timeout(100)
    check('Help still blocked, box not compact', not pg.evaluate("ov.classList.contains('red')") and not pg.evaluate("document.querySelector('#tourBox').classList.contains('compact')"))
    pg.evaluate('tourEnd()')
    # человек сам листает — обучение не возвращает прокрутку
    pg.evaluate("abcOpen();abc.prefix='п';render()"); pg.evaluate("tourStart('abc')"); pg.wait_for_timeout(100)
    pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(150)   # шаг «слова»
    pg.mouse.move(180, 300); pg.mouse.wheel(0, 400); pg.wait_for_timeout(300)
    s1 = pg.evaluate("document.querySelector('#main').scrollTop"); pg.wait_for_timeout(300)
    check('user scroll is respected on this step', pg.evaluate('TOUR.userScroll') and pg.evaluate("document.querySelector('#main').scrollTop") == s1)
    pg.evaluate('tourEnd()')
    # автопрокрутка приложения молчит во время обучения
    pg.evaluate("hearTab='show';settings.hearTab='show';openHear()"); pg.evaluate("tourStart('show')"); pg.wait_for_timeout(100)
    s0 = pg.evaluate("document.querySelector('#main').scrollTop")
    pg.evaluate("fullyVisible(document.querySelector('#showClip'));document.querySelector('#main').scrollTop"); pg.wait_for_timeout(100)
    check('fullyVisible does nothing during tutorial', pg.evaluate("document.querySelector('#main').scrollTop") == s0)
    pg.evaluate('tourEnd()')
    check('no script errors', not errors)
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
