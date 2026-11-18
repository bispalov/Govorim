# v67: 🎓 обучение по шагам
import json, os, shutil, threading, http.server, functools, re
from playwright.sync_api import sync_playwright
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
window.__spoken=[];window.__recStarts=0;window.__speaking=false;
const ss={cancel(){window.__speaking=false},speak(u){window.__spoken.push({t:u.text,l:u.lang});window.__speaking=true;setTimeout(()=>{window.__speaking=false;u.onend&&u.onend()},30)},get speaking(){return window.__speaking},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
class FakeSR{start(){window.__recStarts++;setTimeout(()=>this.onstart&&this.onstart(),1)}stop(){this.onend&&this.onend()}abort(){this.onend&&this.onend()}};window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
window.confirm=()=>true;
"""
results = []; errors = []
def check(n, c):
    results.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n)
def page(b, ls, W=412, H=860, once=True):
    ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    init = ''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in ls.items())
    if once: init = "if(!sessionStorage.__i){" + init + "}sessionStorage.__i=1;"
    pg.add_init_script(STUB + init)
    pg.goto(URL); pg.wait_for_timeout(250); return pg
offer = lambda pg: pg.evaluate("!!(TOUR&&TOUR.scr==='offer')")
touring = lambda pg: pg.evaluate("TOUR?TOUR.scr:null")
seen = lambda pg: pg.evaluate("tourSeen()")
step = lambda pg: pg.evaluate("TOUR&&TOUR.cur?TOUR.cur.t:null")
def wait_offer(pg, ms=900): pg.wait_for_timeout(ms); return offer(pg)
def nxt(pg): pg.locator('#tourBox .tbtns button.go').click(); pg.wait_for_timeout(60)
def run_steps(pg):
    seq = []
    while touring(pg) and len(seq) < 15:
        seq.append(step(pg)); nxt(pg)
    return seq
def clean(pg):
    return pg.evaluate("!document.querySelector('#tourHole')&&!document.querySelector('#tourBox')&&TOUR===null")
base = {'aac.lang': 'uk'}

with sync_playwright() as p:
    b = p.chromium.launch()
    # ---------- 1. Предложение ----------
    pg = page(b, base)
    check('offer on first home visit', wait_offer(pg))
    check('offer text in menu language', 'Показати, як тут користуватися' in pg.inner_text('#tourBox'))
    check('offer box does not speak', pg.evaluate('window.__spoken.length') == 0)
    pg.locator('#tourBox button', has_text='Не зараз').click()
    check('«Not now» remembered', seen(pg).get('home') == 1 and clean(pg))
    pg.reload(); pg.wait_for_timeout(900)
    check('no offer again on home', not offer(pg))
    pg.click('#micBtn')
    check('offer on 🎤 tab', wait_offer(pg))
    pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(80)
    check('«Yes» starts tutorial and is remembered', touring(pg) in ('hear', 'show') and seen(pg).get(touring(pg)) == 1)
    pg.evaluate('tourEnd()')
    # 🎤 обучение не включает микрофон
    check('mic not started by tutorial', pg.evaluate('window.__recStarts') == 0)
    pg.context.close()
    # выключенная настройка
    pg = page(b, {**base, 'aac.settings': json.dumps({'tourOffer': False})})
    check('setting off → no offer', not wait_offer(pg))
    pg.click('#abcBtn'); check('setting off → no offer in ABC', not wait_offer(pg))
    pg.context.close()
    # не поверх окна / во время звучания / записи
    pg = page(b, {**base, 'aac.tour.seen': json.dumps({'home': 1})})
    pg.evaluate("window.__speaking=true;speechSynthesis.__x=1"); pg.evaluate("ss=null")
    pg.evaluate("Object.defineProperty(speechSynthesis,'speaking',{get(){return true},configurable:true})")
    pg.click('#abcBtn'); check('no offer while a phrase is sounding', not wait_offer(pg))
    pg.evaluate("Object.defineProperty(speechSynthesis,'speaking',{get(){return false},configurable:true})")
    pg.click('#home'); pg.click('#micBtn'); pg.wait_for_timeout(100)
    pg.evaluate("delete window.__x")
    # окно «…?» открыто — предложения нет
    pg.evaluate("tourEnd();localStorage.setItem('aac.tour.seen',JSON.stringify({home:1}))")
    pg.click('#home'); pg.wait_for_timeout(50)
    pg.evaluate("path=[tree.find(n=>n.c&&n.c.length)];ask(path[0].c.find(x=>!x.c)||path[0].c[0]);render=render")
    pg.evaluate("tourSchedule()"); pg.wait_for_timeout(700)
    check('no offer over the «…?» window', not offer(pg))
    pg.evaluate("closeOv()")
    pg.context.close()
    # запуск с последнего экрана — только после касания
    pg = page(b, {**base, 'aac.settings': json.dumps({'resume': True}), 'aac.lastScr': json.dumps({'v': 'abc'})})
    check('resumed ABC: no offer before touch', not wait_offer(pg, 1200))
    pg.mouse.click(200, 300); pg.wait_for_timeout(1600)
    check('resumed ABC: offer after first touch', offer(pg))
    pg.context.close()
    # «Начать заново»
    pg = page(b, {**base, 'aac.tour.seen': json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})})
    check('all seen → no offer', not wait_offer(pg))
    pg.click('#settingsBtn')
    check('settings: checkbox and reset button in «Основне»', pg.locator('#sett .sg[data-g=main] #setTourOffer').count() == 1 and pg.locator('#sett .sg[data-g=main] #tourReset').is_visible())
    pg.click('#tourReset')
    check('reset clears seen', seen(pg) == {} and pg.locator('#tourResetNote').is_visible())
    pg.click('#closeSettBtn'); pg.click('#abcBtn')
    check('offer comes back after reset', wait_offer(pg))
    pg.context.close()

    # ---------- 2. Шаги по экранам и уровням ----------
    allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
    for lv in ['L1', 'L2', 'L3']:
        pg = page(b, {**base, 'aac.tour.seen': allseen, 'aac.settings': json.dumps({'level': lv})})
        pg.evaluate("tourStart('home')"); pg.wait_for_timeout(60)
        sq = run_steps(pg)
        check(f'{lv} home: steps run to the end', len(sq) >= 6 and clean(pg))
        check(f'{lv} home: ABC step only where ABC exists', ('h_abc' in sq) == (lv != 'L1'))
        pg.context.close()
    # плитки: шаг wait (Говорить одразу выключено) → окно «…?»
    pg = page(b, {**base, 'aac.tour.seen': allseen, 'aac.settings': json.dumps({'level': 'L2', 'quick': False})})
    pg.evaluate("path=[tree.find(n=>n.c&&n.c.some(x=>!x.c))];render()"); pg.wait_for_timeout(50)
    pg.evaluate("tourStart('tiles')"); pg.wait_for_timeout(60)
    check('tiles: first step waits for a tap', step(pg) == 't_tile' and pg.evaluate('TOUR.waitNow') and 'Спробуйте' in pg.inner_text('#tourBox'))
    leaf = pg.evaluate("(()=>{const t=[...document.querySelectorAll('#main .tile')];return t.length})()")
    pg.locator('#main .tile').first.click(); pg.wait_for_timeout(500)
    check('tiles: tap on highlighted tile works and moves on', step(pg) in ('t_ask', 't_back'))
    if step(pg) == 't_ask':
        check('tiles: «…?» window explained', pg.evaluate("document.querySelector('#ov').style.display") == 'flex')
        pg.locator('#ov .ans.yes').click(force=True); pg.wait_for_timeout(80)
        check('tiles: answer blocked on non-wait step', pg.evaluate("document.querySelector('#ov .said')") is None)
    pg.evaluate('tourEnd();closeOv()'); pg.context.close()
    # holdSel: короткое касание не двигает обучение, удержание — двигает
    pg = page(b, {**base, 'aac.tour.seen': allseen, 'aac.settings': json.dumps({'level': 'L2', 'quick': False, 'holdSel': True})})
    pg.evaluate("path=[tree.find(n=>n.c&&n.c.some(x=>!x.c))];render()"); pg.wait_for_timeout(50)
    pg.evaluate("tourStart('tiles')"); pg.wait_for_timeout(60)
    check('holdSel: text says press and hold', 'потримайте' in pg.inner_text('#tourBox'))
    t0 = pg.locator('#main .tile').first; bx = t0.bounding_box()
    pg.mouse.click(bx['x'] + 20, bx['y'] + 20); pg.wait_for_timeout(450)
    check('holdSel: short tap does not advance', step(pg) == 't_tile')
    pg.mouse.move(bx['x'] + 20, bx['y'] + 20); pg.mouse.down(); pg.wait_for_timeout(650); pg.mouse.up(); pg.wait_for_timeout(450)
    check('holdSel: hold advances', step(pg) != 't_tile')
    pg.evaluate('tourEnd();closeOv()'); pg.context.close()
    # опасные кнопки не срабатывают
    pg = page(b, {**base, 'aac.tour.seen': allseen})
    pg.evaluate("tourStart('home')"); pg.wait_for_timeout(60)
    while step(pg) != 'h_sos': nxt(pg)
    pg.locator('#bar button[data-k=help]').click(force=True); pg.wait_for_timeout(100)
    pg.locator('#bar button[data-k=yes]').click(force=True); pg.locator('#bar button[data-k=pain]').click(force=True); pg.wait_for_timeout(100)
    check('Help/Yes/Pain blocked during tutorial', not pg.evaluate("ov.classList.contains('red')") and pg.evaluate('path.length') == 0 and not any('Допоможіть' in x['t'] for x in pg.evaluate('window.__spoken')))
    check('still on the same step', step(pg) == 'h_sos')
    sp = pg.evaluate('window.__spoken')
    check('voice: no emoji/arrows spoken', all(not re.search('[\U0001F000-\U0001FAFF☀-➿←-⇿⌀-⏿]', x['t']) for x in sp) and len(sp) >= 4)
    check('voice: menu language', all(x['l'] == 'uk-UA' for x in sp))
    pg.evaluate("tourEnd()")
    # язык меню отличается от языка фраз
    pg.evaluate("settings.uiLang='en';applyI18n();tourStart('home')"); pg.wait_for_timeout(60)
    check('menu language en: text and voice in English, button labels from phrase strings', 'Tiles' in pg.inner_text('#tourBox') and pg.evaluate('window.__spoken.at(-1).l') == 'en-US')
    nxt(pg); check('label of Yes button taken from UI', '“Так”' in pg.inner_text('#tourBox'))
    pg.evaluate("tourEnd();settings.uiLang='auto';applyI18n()")
    # завершение: «Назад» кнопкой, popstate, смена экрана, смена языка
    pg.evaluate("tourStart('home')"); pg.wait_for_timeout(60)
    pg.locator('#bar button[data-k=back]').click(force=True); pg.wait_for_timeout(60)
    check('bar Back ends tutorial', clean(pg))
    pg.evaluate("tourStart('home')"); pg.evaluate("appBack()")
    check('system Back (appBack) ends tutorial', clean(pg))
    pg.evaluate("tourStart('home')"); pg.evaluate("openHear()")
    check('screen change ends tutorial', clean(pg))
    pg.evaluate("tourStart(tourScreen())"); pg.evaluate("setLang('ru')")
    check('language change ends tutorial', clean(pg))
    pg.click('#home'); pg.locator('#main .tile').first.click(); pg.wait_for_timeout(100)
    check('normal taps work after tutorial', pg.evaluate("path.length>0||document.querySelector('#ov').style.display==='flex'"))
    pg.evaluate("closeOv()")
    # справка: кнопка 🎓
    pg.click('#home'); pg.click('#helpBtn')
    check('help on home: 🎓 button for home', pg.locator('#help .htour').count() == 1 and 'Главный экран' in pg.inner_text('#help .htour'))
    check('HELP_KEYS matches items', pg.evaluate("['ru','uk','en'].every(l=>U[l].helpDoc.s.length===HELP_KEYS.length)") and pg.evaluate("U.ru.helpDoc.s[HELP_KEYS.indexOf('tour')][0]") == '🎓 Обучение')
    pg.click('#help .htour'); pg.wait_for_timeout(60)
    check('🎓 in help starts home tutorial, help closed', touring(pg) == 'home' and pg.evaluate("helpEl.style.display") == 'none')
    pg.evaluate('tourEnd()'); pg.click('#abcBtn'); pg.click('#helpBtn')
    check('help in ABC: 🎓 for ABC and tour item', 'Азбука' in pg.inner_text('#help .htour') and '🎓 Обучение' in pg.text_content('#help'))
    pg.click('#help .htour'); pg.wait_for_timeout(60)
    check('ABC tutorial starts', touring(pg) == 'abc')
    pg.evaluate('tourEnd()')
    check('no script errors so far', not errors)
    pg.context.close()

    # ---------- 3. Геометрия на каждом шаге ----------
    GEO = r"""(()=>{
      const hole=document.querySelector('#tourHole').getBoundingClientRect(),box=document.querySelector('#tourBox').getBoundingClientRect();
      const r=tourRect(TOUR.els),st=document.querySelector('#stage').getBoundingClientRect(),bar=document.querySelector('#bar').getBoundingClientRect();
      const inter=(a,b)=>!(a.right<=b.left||b.right<=a.left||a.bottom<=b.top||b.bottom<=a.top);
      const fitsBoth=r.height+box.height+12<=st.height-8;
      const inBar=TOUR.els.some(e=>e.closest('#bar')), inHead=TOUR.els.some(e=>e.closest('header'));
      return {fitsBoth,overlap:inter(r,box),topHidden:!inBar&&!inHead&&r.top<st.top-1,off:box.top<0||box.bottom>innerHeight+1||box.left<0||box.right>innerWidth+1,
              barCovered:inBar&&inter(r,box),topOpen:r.top>=box.top-1||r.top<box.top, wide:box.width<=innerWidth+0.5};
    })()"""
    sizes = [(360, 640), (313, 556), (277, 492), (360, 740)]
    for L in ['uk', 'ru']:
        for W, H in sizes:
            pg = page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.showhist': json.dumps([]), 'aac.settings': json.dumps({'level': 'L2'})}, W, H)
            bad = []
            def go(scr, prep):
                pg.evaluate(prep); pg.wait_for_timeout(80)
                pg.evaluate(f"tourStart('{scr}')"); pg.wait_for_timeout(120)
                n = 0
                while touring(pg) and n < 15:
                    g = pg.evaluate(GEO)
                    if g['off'] or not g['wide']: bad.append((scr, step(pg), 'off'))
                    if g['barCovered']: bad.append((scr, step(pg), 'bar'))
                    if g['fitsBoth'] and g['overlap']: bad.append((scr, step(pg), 'overlap'))
                    if g['topHidden']: bad.append((scr, step(pg), 'topHidden'))
                    if L == 'uk' and (W, H) in [(360, 640), (277, 492)] and scr in ('home', 'abc') and n in (0, 1, 3):
                        pg.screenshot(path=f'{OUT}/tour_{scr}_{W}_{n}.png')
                    nxt(pg); pg.wait_for_timeout(60); n += 1
            go('home', "closeOv();path=[];abc=null;hearOn=false;render()")
            go('tiles', "path=[tree.find(n=>n.id==='pain')||tree.find(n=>n.c)];render()")
            go('show', "path=[];hearTab='show';settings.hearTab='show';openHear();showShow('Я скоро прийду, чекай на мене',false)")
            go('hear', "hearTab='sug';settings.hearTab='sug';openHear();hearBuild=['я','хочу','пити'];hearOpen=true;refreshHear()")
            go('abc', "abcOpen();abc.prefix='п';render()")
            check(f'{L} {W}x{H}: geometry ok on all steps', not bad)
            if bad: print('   ', bad[:6])
            pg.context.close()
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
