# v81: проверка возможностей браузера — окно при первом открытии не в Chrome, строка в «О приложении»,
# пункт справки «🌐 Браузеры», загрузка без озвучки. Браузеры имитируются UA и удалением возможностей до загрузки.
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
from playwright.sync_api import sync_playwright
AUDIT = open(os.path.join(TESTS, 'audit_dark.js'), encoding='utf-8').read()
results, errors = [], []
def check(name, ok):
    results.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name)
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
UA = {
 'chrome': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36',
 'firefox': 'Mozilla/5.0 (Android 13; Mobile; rv:132.0) Gecko/132.0 Firefox/132.0',
 'samsung': 'Mozilla/5.0 (Linux; Android 13; SM-A536B) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/26.0 Chrome/122.0.0.0 Mobile Safari/537.36',
 'edge': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Mobile Safari/537.36 EdgA/131.0.0.0',
 'fb': 'Mozilla/5.0 (Linux; Android 13; Pixel 7; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/131.0.0.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/480.0.0.0;]',
}
VOICES = {'all': "[{lang:'uk-UA',name:'uk'},{lang:'ru-RU',name:'ru'},{lang:'en-US',name:'en'}]", 'en': "[{lang:'en-US',name:'en'}]", 'none': "[]"}
def mk(b, ua, L='ru', sr=True, tts=True, voices='all', ls=None, W=360, H=640, theme='dark'):
    ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H}, user_agent=UA[ua])
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    init = ""
    if sr: init += "if(!window.webkitSpeechRecognition){window.webkitSpeechRecognition=function(){this.start=()=>{};this.stop=()=>{};this.abort=()=>{}}}"
    else: init += "for(const k of ['SpeechRecognition','webkitSpeechRecognition']){try{delete window[k]}catch(e){}try{Object.defineProperty(window,k,{value:undefined,configurable:true,writable:true})}catch(e){}}"
    if tts: init += f";try{{const vs={VOICES[voices]};speechSynthesis.getVoices=()=>vs}}catch(e){{}}"
    else: init += ";delete Window.prototype.speechSynthesis;delete window.speechSynthesis;delete window.SpeechSynthesisUtterance"
    s = {'level': 'L3', 'theme': theme}
    data = {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}; data.update(ls or {})
    pg.add_init_script(init + ";if(!sessionStorage.__i){" + ''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in data.items() if v is not None) + "}sessionStorage.__i=1;")
    pg.goto(URL); pg.wait_for_timeout(400); return pg
LI = lambda pg: pg.evaluate("[...document.querySelectorAll('#brw li')].map(e=>e.textContent)")

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. Chrome со всем — окна нет; «О приложении»
    pg = mk(b, 'chrome'); pg.wait_for_timeout(300)
    check('Chrome with everything: no window', pg.locator('#brw').count() == 0)
    pg.click('#settingsBtn'); pg.evaluate("settSet('about')"); pg.wait_for_timeout(80)
    check('About: «распознавание речи ✔, озвучка ✔»', 'Этот браузер: распознавание речи ✔, озвучка ✔' in pg.inner_text('#aboutBox'))
    pg.context.close()
    # 2. Firefox Android: нет распознавания
    pg = mk(b, 'firefox', sr=False)
    check('Firefox: window shown', pg.locator('#brw').count() == 1 and pg.locator('#brw').is_visible())
    li = LI(pg)
    check('Firefox: one item — recognition does not work', len(li) == 1 and 'Распознавание речи не работает' in li[0])
    a = pg.locator('#brw a.go')
    check('Firefox: «Open in Chrome» intent button', a.count() == 1 and 'package=com.android.chrome' in a.get_attribute('href'))
    check('note names the backup button', '💾 Сохранить копию данных' in pg.inner_text('#brw'))
    check('buttons ≥ 52 px', all(x >= 52 for x in pg.evaluate("[...document.querySelectorAll('#brw .brwb .ans')].map(e=>e.getBoundingClientRect().height)")))
    pg.locator('#brw .ok').click(); pg.wait_for_timeout(80)
    check('«Понятно» closes and remembers', pg.locator('#brw').count() == 0 and pg.evaluate("localStorage.getItem('aac.brw.seen')") == 'sr')
    pg.click('#settingsBtn'); pg.evaluate("settSet('about')"); pg.wait_for_timeout(80)
    check('About in Firefox: «распознавание речи ✖»', 'распознавание речи ✖' in pg.inner_text('#aboutBox'))
    pg.reload(); pg.wait_for_timeout(500)
    check('second time not shown', pg.locator('#brw').count() == 0)
    pg.context.close()
    pg = mk(b, 'firefox', sr=False); pg.evaluate("history.back()"); pg.wait_for_timeout(300)
    check('system Back closes the window (and remembers)', pg.locator('#brw').count() == 0 and pg.evaluate("localStorage.getItem('aac.brw.seen')") == 'sr' and pg.evaluate("!!document.body"))
    pg.context.close()
    pg = mk(b, 'edge', sr=False)
    check('Edge on Android (no recognition): window with Chrome button', pg.locator('#brw li').count() == 1 and pg.locator('#brw a.go').count() == 1)
    pg.context.close()
    # 3. Samsung Internet — с ограничениями
    pg = mk(b, 'samsung', L='uk')
    li = LI(pg)
    check('Samsung: «з обмеженнями»', len(li) == 1 and 'з обмеженнями' in li[0] and pg.locator('#brw a.go').count() == 1)
    pg.locator('#brw .ok').click(); pg.click('#settingsBtn'); pg.evaluate("settSet('about')"); pg.wait_for_timeout(80)
    check('About in Samsung (uk): «розпізнавання мовлення — з обмеженнями»', 'розпізнавання мовлення — з обмеженнями' in pg.inner_text('#aboutBox'))
    pg.context.close()
    # 4. Нет голоса для языка — только пункт про голос, без кнопки Chrome
    pg = mk(b, 'chrome', voices='en')
    li = LI(pg)
    check('no voice for Russian: only the voice item', len(li) == 1 and '«Русский»' in li[0] and 'Синтез речи' in li[0])
    check('no voice: no «Open in Chrome» (voice comes from the phone)', pg.locator('#brw a.go').count() == 0)
    pg.locator('#brw .ok').click(); pg.wait_for_timeout(50)
    check('voice key remembered', pg.evaluate("localStorage.getItem('aac.brw.seen')") == 'voice-ru')
    pg.click('#settingsBtn'); pg.select_option('#setLang', 'en'); pg.wait_for_timeout(300)
    check('switching to a language with a voice: no window', pg.locator('#brw').count() == 0)
    pg.select_option('#setLang', 'uk'); pg.wait_for_timeout(300)
    check('switching to another language without a voice: shown again', pg.locator('#brw').count() == 1 and '«Українська»' in ' '.join(LI(pg)))
    pg.context.close()
    # 5. Пустой список голосов — про голос молчим
    pg = mk(b, 'chrome', voices='none'); pg.wait_for_timeout(1700)
    check('empty voice list (still loading): no window', pg.locator('#brw').count() == 0)
    pg.context.close()
    # 6. Нет озвучки — загрузка без ошибок, пункт, работа экранов
    n0 = len(errors)
    pg = mk(b, 'chrome', tts=False)
    check('no speech output: app loads without errors', len(errors) == n0 and pg.locator('#main .tile').count() > 0)
    li = LI(pg)
    check('no speech output in Chrome: item, no «Open in Chrome» (already Chrome)', any('Озвучка не работает' in x for x in li) and pg.locator('#brw a.go').count() == 0)
    pg.locator('#brw .ok').click(); pg.wait_for_timeout(50)
    pg.locator('#main .tile').first.click(); pg.wait_for_timeout(200)
    pg.evaluate("closeOv&&closeOv()"); pg.click('#micBtn'); pg.wait_for_timeout(100)
    pg.evaluate("hearTab='show';openHear()"); pg.wait_for_timeout(100); pg.click('#showMic'); pg.wait_for_timeout(150)
    pg.evaluate("abcOpen()"); pg.wait_for_timeout(100)
    check('no speech output: tiles, 🎤 (both tabs), ABC — no script errors', len(errors) == n0)
    pg.click('#settingsBtn'); pg.evaluate("settSet('about')"); pg.wait_for_timeout(80)
    check('About without speech output: «озвучка ✖»', 'озвучка ✖' in pg.inner_text('#aboutBox'))
    pg.context.close()
    # 7. Другой набор проблем — показ снова
    pg = mk(b, 'firefox', sr=False, tts=False, ls={'aac.brw.seen': 'sr'})
    check('new set of problems (sr + tts after sr): shown again', pg.locator('#brw').count() == 1 and pg.locator('#brw li').count() == 2 and pg.evaluate("document.querySelector('#brw').dataset.key") == 'sr,tts')
    pg.context.close()
    # 8. Встроенный браузер Facebook — плашка вместо окна
    pg = mk(b, 'fb', sr=False)
    check('Facebook in-app browser: yellow plaque, no window', pg.locator('#iab').count() == 1 and pg.locator('#brw').count() == 0)
    pg.context.close()
    # 9. Обучение не перекрывает окно
    pg = mk(b, 'firefox', sr=False, ls={'aac.tour.seen': None}); pg.wait_for_timeout(1200)
    check('tour is not offered while the window is open', pg.locator('#brw').count() == 1 and pg.evaluate("!TOUR"))
    pg.context.close()
    # 10. Справка
    for L, t in [('ru', '🌐 Браузеры: что где работает'), ('uk', '🌐 Браузери: що де працює'), ('en', '🌐 Browsers: what works where')]:
        pg = mk(b, 'chrome', L=L)
        r = pg.evaluate(f"(()=>{{const i=HELP_KEYS.indexOf('browser'),d=U['{L}'].helpDoc;return {{n:HELP_KEYS.length,m:d.s.length,t:d.s[i]&&d.s[i][0],prev:HELP_KEYS[i-1],next:HELP_KEYS[i+1]}}}})()")
        check(f'help {L}: «browser» after «install», title in place, counts equal', r['n'] == r['m'] and r['t'] == t and r['prev'] == 'install' and r['next'] == 'tips')
        pg.click('#micBtn'); pg.wait_for_timeout(80); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        check(f'help {L}: in the 🎤 screen help', t in pg.evaluate("document.querySelector('#help').textContent"))
        pg.context.close()
    # 11. Вёрстка окна: 360/313/277/240 × ru/uk/en, тёмная тема
    for L in ['ru', 'uk', 'en']:
        for W, H in [(360, 640), (313, 556), (277, 492), (240, 480)]:
            pg = mk(b, 'firefox', sr=False, L=L, tts=True, voices='en', W=W, H=H)
            r = pg.evaluate("""(()=>{const W=document.documentElement.clientWidth,p=document.querySelector('.brwp');
              const out=[...p.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.width&&(r.right>W+1||r.left<-1)}).length;
              const ok=document.querySelector('#brw .ok');ok.scrollIntoView({block:'nearest'});const o=ok.getBoundingClientRect();
              return {out,ok:o.top>=0&&o.bottom<=innerHeight&&o.height>=52,pr:p.getBoundingClientRect().right<=W}})()""")
            f = pg.evaluate(AUDIT)
            bad = [x for x in f if 'brw' in x['el']]
            check(f'layout {L} {W}x{H}: window fits, «OK» reachable, dark panel', r['out'] == 0 and r['ok'] and r['pr'] and not bad)
            if W == 240 and L == 'uk':
                pg.locator('#brw .ok').click(); pg.wait_for_timeout(50)
                check('after closing, the app works', pg.locator('#brw').count() == 0 and pg.locator('#main .tile').count() > 0)
            pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
