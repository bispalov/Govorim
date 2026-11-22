# v80: звук нажатия кнопок (⚙️ → «Управление и нажатия»): выключен / тихий / громкий, короткий низкий щелчок WebAudio.
# Щёлкает только принятое нажатие (не удержание-отказ, не слишком быстрый повтор), не во время распознавания,
# кнопки окна настроек не щёлкают; при выборе громкости — образец.
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
SPY = """(()=>{window.__cl=[];window.__vib=0;
  navigator.vibrate=()=>{window.__vib++;return true};
  const P=AudioContext.prototype,o=P.createOscillator,gn=P.createGain;
  P.createOscillator=function(){const x=o.call(this),f=x.frequency.setValueAtTime.bind(x.frequency),
    r=x.frequency.exponentialRampToValueAtTime.bind(x.frequency),c={f:[],g:0};window.__cl.push(c);
    x.frequency.setValueAtTime=(v,t)=>{c.f.push(v);return f(v,t)};x.frequency.exponentialRampToValueAtTime=(v,t)=>{c.f.push(v);return r(v,t)};return x};
  P.createGain=function(){const x=gn.call(this),sv=x.gain.setValueAtTime.bind(x.gain);
    x.gain.setValueAtTime=(v,t)=>{const c=window.__cl[window.__cl.length-1];if(c&&!c.g)c.g=v;return sv(v,t)};return x};
})()"""
N = lambda pg: pg.evaluate("window.__cl.length")
def st(W, H, L, extra=None):
    s = {'level': 'L3', 'theme': 'dark'}; s.update(extra or {})
    pg = page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}, W, H)
    pg.evaluate(SPY); return pg
def opengroup(pg, g='touch'):
    pg.click('#settingsBtn'); pg.evaluate(f"settSet('{g}')"); pg.wait_for_timeout(80)
def closesett(pg):
    pg.evaluate("[...document.querySelectorAll('.modal')].filter(m=>getComputedStyle(m).display!=='none').forEach(m=>{const c=m.querySelector('.helphead button');c&&c.click()})"); pg.wait_for_timeout(80)
TILE = '#main .tile'

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. По умолчанию выключено
    pg = st(360, 640, 'ru')
    check('default: tapSound off in settings', pg.evaluate('settings.tapSound') == 0)
    pg.locator(TILE).first.click(); pg.wait_for_timeout(60)
    check('default: no click sound on a tile', N(pg) == 0)
    # 2. Выбор громкости: образец, сохранение, сводка; кнопки окна настроек не щёлкают
    opengroup(pg)
    check('setting shown with 3 options', pg.locator('#setTapSound option').count() == 3 and pg.locator('#setTapSound').is_visible())
    n0 = N(pg); pg.locator('#sett .sgh').first.click(); pg.wait_for_timeout(60); pg.evaluate("settSet('touch')"); pg.wait_for_timeout(60)
    pg.select_option('#setTapSound', '1'); pg.wait_for_timeout(100)
    check('choosing «quiet» plays one sample click (settings buttons silent)', N(pg) == n0 + 1)
    check('saved immediately', json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['tapSound'] == 1)
    pg.evaluate("settSet('main')"); pg.wait_for_timeout(60)
    check('collapsed group summary mentions the sound', 'звук: тихий' in pg.evaluate("document.querySelector('.sg[data-g=touch] .sgh').textContent"))
    pg.evaluate("settSet('touch')"); pg.select_option('#setTapSound', '0'); pg.wait_for_timeout(80)
    check('choosing «off» plays nothing', N(pg) == n0 + 1)
    pg.select_option('#setTapSound', '1'); pg.wait_for_timeout(60); closesett(pg)
    # 3. Щелчок на плитке и на кнопке панели; низкая частота; громкость
    n0 = N(pg); pg.locator(TILE).first.click(); pg.wait_for_timeout(80)
    c = pg.evaluate("window.__cl[window.__cl.length-1]")
    check('tile tap clicks once', N(pg) == n0 + 1)
    check('click is low: all frequencies ≤ 700 Hz', c and max(c['f']) <= 700 and min(c['f']) >= 300)
    check('quiet level gain 0.18', c and abs(c['g'] - 0.18) < 1e-6)
    pg.evaluate("closeOv&&closeOv()"); pg.wait_for_timeout(60)
    n0 = N(pg); pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(80)
    check('bar button taps click', N(pg) == n0 + 1)
    pg.reload(); pg.wait_for_timeout(250); pg.evaluate(SPY)
    check('setting kept after restart', pg.evaluate('settings.tapSound') == 1)
    pg.evaluate("settings.tapSound=2"); pg.locator(TILE).first.click(); pg.wait_for_timeout(80)
    check('loud level gain 0.55', abs(pg.evaluate("window.__cl[window.__cl.length-1].g") - 0.55) < 1e-6)
    pg.context.close()
    # 4. Отклонённое нажатие не щёлкает: быстрый повтор при защите, короткое касание при «выборе удержанием»
    pg = st(360, 640, 'ru', {'tapSound': 1, 'guard': 1500})
    n0 = N(pg); pg.click('#bar button[data-k=rep]'); pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(80)
    check('guard: fast repeat tap ignored — one click only', N(pg) == n0 + 1)
    pg.context.close()
    pg = st(360, 640, 'ru', {'tapSound': 1, 'holdSel': True})
    n0 = N(pg); pg.locator(TILE).first.click(); pg.wait_for_timeout(100)
    check('hold-to-select: short tap ignored — no click', N(pg) == n0)
    bb = pg.locator(TILE).first.bounding_box(); pg.mouse.move(bb['x'] + 20, bb['y'] + 20); pg.mouse.down(); pg.wait_for_timeout(650); pg.mouse.up(); pg.wait_for_timeout(100)
    check('hold-to-select: completed hold clicks', N(pg) == n0 + 1)
    pg.context.close()
    # 5. Во время распознавания щелчка нет, вибрация остаётся
    pg = st(360, 640, 'ru', {'tapSound': 2, 'vib': True})
    pg.click('#micBtn'); pg.wait_for_timeout(100)
    n0, v0 = N(pg), pg.evaluate('window.__vib')
    pg.click('#micGo'); pg.wait_for_timeout(100)
    check('starting the mic: click before recognition starts', N(pg) == n0 + 1)
    check('recognition is on', pg.evaluate('!!rec'))
    n1, v1 = N(pg), pg.evaluate('window.__vib')
    pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(80)
    check('during recognition: no click', N(pg) == n1)
    check('during recognition: vibration still works', pg.evaluate('window.__vib') > v1)
    pg.evaluate("stopRec()"); pg.wait_for_timeout(80)
    n2 = N(pg); pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(1600); pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(80)
    check('after the mic stops: clicks again', N(pg) > n2)
    pg.evaluate("hearTab='show';openHear()"); pg.wait_for_timeout(100)
    pg.click('#showMic'); pg.wait_for_timeout(100)
    if pg.evaluate('!!rec2'):
        n3 = N(pg); pg.click('#bar button[data-k=rep]'); pg.wait_for_timeout(80)
        check('other-person tab recognition: no click', N(pg) == n3)
    else:
        check('other-person tab recognition started', False)
    pg.context.close()
    # 6. Вёрстка группы на узких экранах, три языка
    for L in ['ru', 'uk', 'en']:
        for W, H in [(360, 640), (313, 556), (277, 492), (240, 480)]:
            pg = st(W, H, L, {'tapSound': 2}); opengroup(pg)
            pg.evaluate("document.querySelector('#setTapSound').scrollIntoView({block:'center'})"); pg.wait_for_timeout(50)
            r = pg.evaluate("""(()=>{const m=document.querySelector('#sett'),W=document.documentElement.clientWidth;
              const bad=[...m.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>W+1});
              const s=document.querySelector('#setTapSound'),sr=s.getBoundingClientRect(),n=document.querySelector('[data-i=s_tapnote]');
              return {bad:bad.length,sel:sr.width>100&&sr.right<=W+1,txt:s.options[s.selectedIndex].text,note:n&&n.textContent.length>20}})()""")
            check(f'layout {L} {W}x{H}: touch group fits, select and note shown', r['bad'] == 0 and r['sel'] and r['note'] and r['txt'] == {'ru': 'громкий', 'uk': 'гучний', 'en': 'loud'}[L])
            pg.context.close()
    # 7. Справка
    for L, w in [('ru', 'звук при нажатии кнопок'), ('uk', 'звук під час натискання кнопок'), ('en', 'sound on button taps')]:
        pg = st(360, 640, L); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        check(f'help {L}: tap sound described', w in pg.evaluate("document.querySelector('#help').textContent"))
        pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
