# v62: «ℹ️ О приложении», справка о переустановке, настоящий service worker (обновление, офлайн, копия в другой папке)
import json, os, shutil, threading, http.server, functools, base64
from playwright.sync_api import sync_playwright

import os, sys, tempfile; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *          # здесь нужен только путь к приложению: сайт для service worker тест строит сам
ROOT = tempfile.mkdtemp(prefix='govorim-sw-')
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
def put(folder, files):
    d = ROOT + folder; os.makedirs(d, exist_ok=True)
    for dst, src in files.items():
        if isinstance(src, bytes): open(d + dst, 'wb').write(src)
        else: shutil.copy(src, d + dst)
    for ic in ['icon-192.png', 'icon-512.png']: open(d + ic, 'wb').write(PNG)
srv, PORT = serve(ROOT)
B = f'http://127.0.0.1:{PORT}'

STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
const ss={cancel(){},speak(u){setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
"""
results = []; errors = []
def check(n, c):
    results.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n)


def waitv(pg, v, n=20):
    for _ in range(n):
        pg.wait_for_timeout(500)
        try:
            if pg.evaluate('typeof APP_VERSION!=="undefined"&&APP_VERSION') == v: return True
        except Exception: pass
    return False
NEW = {f: os.path.join(APP, f) for f in ['index.html', 'sw.js', 'manifest.json']}
# «старая» установленная версия — v61 (старый sw с абсолютными путями): эталонные файлы лежат в tests/
OLD = {'index.html': os.path.join(TESTS, 'index.v61.html'), 'sw.js': os.path.join(TESTS, 'sw.v61.js'), 'manifest.json': os.path.join(TESTS, 'manifest.v61.json')}

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------- 1. «ℹ️ О приложении» и справка ----------
    put('/Govorim/', NEW)
    for L, name, gname, rein in [('ru', 'Говорим вместе', 'ℹ️ О приложении', 'Переустановка'),
                                 ('uk', 'Говоримо разом', 'ℹ️ Про застосунок', 'Переустановлення'),
                                 ('en', 'Let’s talk together', 'ℹ️ About', 'Reinstalling')]:
        for W, H in [(412, 860), (277, 492)]:
            ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H})
            pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
            pg.add_init_script(STUB + f"localStorage.setItem('aac.lang','{L}')")
            pg.goto(B + '/Govorim/index.html'); pg.wait_for_timeout(300)
            pg.click('#settingsBtn')
            sg = pg.locator('#sett .sg[data-g=about]')
            check(f'{L}/{W}: about group is last', pg.evaluate("[...document.querySelectorAll('#sett .sg')].at(-1).dataset.g") == 'about')
            check(f'{L}/{W}: collapsed summary shows version', str(VER) in sg.locator('.sgs').inner_text())
            sg.locator('.sgh').click(); pg.wait_for_timeout(100)
            t = pg.inner_text('#aboutBox')
            check(f'{L}/{W}: group title', gname in sg.locator('.sgh').inner_text())
            check(f'{L}/{W}: name and version', name in t and str(VER) in t)
            a = pg.locator('#aboutBox a')
            check(f'{L}/{W}: two links', a.count() == 2)
            check(f'{L}/{W}: author link', a.nth(0).get_attribute('href') == 'https://github.com/bispalov' and '@bispalov' in a.nth(0).inner_text())
            check(f'{L}/{W}: source link', a.nth(1).get_attribute('href') == 'https://github.com/bispalov/Govorim')
            check(f'{L}/{W}: new tab, noopener', all(a.nth(i).get_attribute('target') == '_blank' and a.nth(i).get_attribute('rel') == 'noopener' for i in range(2)))
            check(f'{L}/{W}: MIT + Claude', 'MIT' in t and 'Claude' in t)
            ov = pg.evaluate("(()=>{const m=document.querySelector('#sett');const r=[...document.querySelectorAll('#aboutBox *')].filter(e=>e.getBoundingClientRect().right>m.clientWidth+1);return r.length})()")
            check(f'{L}/{W}: nothing sticks out', ov == 0 and pg.evaluate('document.querySelector("#sett").scrollWidth<=document.querySelector("#sett").clientWidth'))
            if W == 412:
                pg.screenshot(path=f'{OUT}/about_{L}.png')
            else:
                sg.screenshot(path=f'{OUT}/about_{L}_277.png')
            pg.click('#closeSettBtn'); pg.click('#helpBtn'); pg.wait_for_timeout(100)
            ht = pg.text_content('#help')
            check(f'{L}/{W}: help has about and reinstall', gname in ht and rein in ht and 'bispalov.github.io' in ht)
            ctx.close()
    # без логина в константе и не на github.io — ссылок нет, остальное показывается
    s = SRC.replace("const APP_AUTHOR_GH = 'bispalov';", "const APP_AUTHOR_GH = '';")
    put('/nologin/', {'index.html': s.encode('utf-8'), 'sw.js': NEW['sw.js'], 'manifest.json': NEW['manifest.json']})
    ctx = b.new_context(service_workers='block'); pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(STUB); pg.goto(B + '/nologin/index.html'); pg.wait_for_timeout(300)
    pg.click('#settingsBtn'); pg.locator('#sett .sg[data-g=about] .sgh').click()
    check('empty login, not github.io: no links, text shown', pg.locator('#aboutBox a').count() == 0 and 'MIT' in pg.inner_text('#aboutBox'))
    check('github.io login fallback', pg.evaluate("(()=>{const m=/^([a-z0-9-]+)\\.github\\.io$/i.exec('someone.github.io');return m&&m[1]})()") == 'someone')
    ctx.close()

    # ---------- 2. Настоящий service worker: обновление v61 → v62 ----------
    shutil.rmtree(ROOT + '/Govorim'); put('/Govorim/', OLD)
    ctx = b.new_context()
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(STUB)
    pg.goto(B + '/Govorim/index.html')
    pg.evaluate("navigator.serviceWorker.ready"); pg.reload(); pg.wait_for_timeout(500)
    check('v61 installed and controls page', pg.evaluate('!!navigator.serviceWorker.controller') and pg.evaluate('APP_VERSION') == 61)
    check('v61 cache present', 'govorim-v61' in pg.evaluate('caches.keys()'))
    pg.evaluate("caches.open('speech-rehab-v71').then(c=>c.put('/SpeechRehab/x',new Response('x')))")
    # публикуем v62
    put('/Govorim/', NEW)
    pg.reload()
    for _ in range(40):          # update → install → controllerchange → одна перезагрузка
        pg.wait_for_timeout(500)
        try:
            if pg.evaluate('APP_VERSION') == VER: break
        except Exception: pass
        if _ in (15, 30):            # под нагрузкой проверка обновления иногда опаздывает — ещё одно открытие
            try: pg.reload()
            except Exception: pass
    pg.wait_for_timeout(500)
    check('installed v61 updated to the current version on first opening', pg.evaluate('APP_VERSION') == VER)
    keys = pg.evaluate('caches.keys()')
    check('new cache name with folder', f'govorim-v{VER}:/Govorim/' in keys)
    check('old v61 cache removed', 'govorim-v61' not in keys)
    check('other app cache kept', 'speech-rehab-v71' in keys)
    check('sw scope /Govorim/', pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.scope)") == B + '/Govorim/')
    cached = pg.evaluate(("caches.open('govorim-v%d:/Govorim/').then(c=>c.keys()).then(k=>k.map(r=>new URL(r.url).pathname).sort())" % VER))
    check('precache paths under /Govorim/', cached == sorted(['/Govorim/', '/Govorim/index.html', '/Govorim/manifest.json', '/Govorim/icon-192.png', '/Govorim/icon-512.png']))
    ctx.set_offline(True)
    pg.reload(); waitv(pg, VER)
    check('offline: app opens', pg.evaluate('APP_VERSION') == VER and pg.locator('#main .tile').count() > 0)
    try: pg.goto(B + '/Govorim/')
    except Exception as e: print('goto', e)
    waitv(pg, VER)
    check('offline: folder URL opens', pg.evaluate('typeof APP_VERSION!=="undefined"&&APP_VERSION') == VER)
    ctx.set_offline(False)
    # манифест: те же адреса, что и в v61
    def res(path, man):
        m = json.load(open(man, encoding='utf-8'))
        return pg.evaluate("([u,m])=>{const r=x=>new URL(x,u).href;return {id:r(m.id),start:r(m.start_url),scope:r(m.scope),icons:m.icons.map(i=>r(i.src))}}", [B + path, m])
    check('manifest resolves to the same URLs as v61', res('/Govorim/manifest.json', NEW['manifest.json']) == res('/Govorim/manifest.json', OLD['manifest.json']))
    check('page links manifest relatively', pg.evaluate("document.querySelector('link[rel=manifest]').href") == B + '/Govorim/manifest.json')

    # ---------- 3. Копия в другой папке того же сайта ----------
    m = json.load(open(NEW['manifest.json'], encoding='utf-8')); m['id'] = '/rehab/'
    put('/rehab/', {'index.html': NEW['index.html'], 'sw.js': NEW['sw.js'], 'manifest.json': json.dumps(m, ensure_ascii=False).encode('utf-8')})
    pg2 = ctx.new_page(); pg2.on('pageerror', lambda e: errors.append(str(e))); pg2.add_init_script(STUB)
    pg2.goto(B + '/rehab/index.html'); pg2.evaluate("navigator.serviceWorker.ready"); pg2.reload(); pg2.wait_for_timeout(500)
    check('/rehab/: own sw scope', pg2.evaluate("navigator.serviceWorker.getRegistration().then(r=>r.scope)") == B + '/rehab/')
    keys = pg2.evaluate('caches.keys()')
    check('/rehab/: own cache, /Govorim/ cache kept', f'govorim-v{VER}:/rehab/' in keys and f'govorim-v{VER}:/Govorim/' in keys and 'speech-rehab-v71' in keys)
    cached = pg2.evaluate(("caches.open('govorim-v%d:/rehab/').then(c=>c.keys()).then(k=>k.map(r=>new URL(r.url).pathname))" % VER))
    check('/rehab/: precache in its folder', all(x.startswith('/rehab/') for x in cached) and len(cached) == 5)
    ctx.set_offline(True)
    pg2.reload(); waitv(pg2, VER)
    check('/rehab/ offline: app opens', pg2.evaluate('APP_VERSION') == VER and pg2.locator('#main .tile').count() > 0)
    pg.reload(); waitv(pg, VER)
    check('/Govorim/ still offline-ready after /rehab/ install', pg.evaluate('APP_VERSION') == VER)
    ctx.set_offline(False)
    mr = pg2.evaluate("fetch('manifest.json').then(r=>r.json()).then(m=>({id:new URL(m.id,location.href).pathname,start:new URL(m.start_url,location.origin+'/rehab/manifest.json').pathname,scope:new URL(m.scope,location.origin+'/rehab/manifest.json').pathname}))")
    check('/rehab/ manifest resolves into /rehab/', mr == {'id': '/rehab/', 'start': '/rehab/index.html', 'scope': '/rehab/'})
    ctx.close(); b.close()

print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
