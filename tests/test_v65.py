# v65: 📋 «Показать скопированное» и автопоказ скопированного на вкладке «Говорит собеседник»
import json, os, shutil, threading, http.server, functools
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
window.__spoken=[];window.__clip='';window.__clipDeny=false;window.__clipReads=0;
const ss={cancel(){},speak(u){window.__spoken.push(u.text);setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
Object.defineProperty(navigator,'clipboard',{value:{readText(){window.__clipReads++;return window.__clipDeny?Promise.reject(new Error('denied')):Promise.resolve(window.__clip)},writeText(){return Promise.resolve()}},configurable:true});
class FakeSR{start(){}stop(){}abort(){}};window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
window.confirm=()=>true;
"""
results = []; errors = []
def check(n, c):
    results.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n)
def page(b, ls, W=412, H=860):
    ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.add_init_script(STUB + ''.join(f"if(!sessionStorage.__i)localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in ls.items()) + "sessionStorage.__i=1;")
    pg.goto(URL); pg.wait_for_timeout(300); return pg
def switch_back(pg):   # человек вернулся в приложение из мессенджера
    pg.evaluate("window.dispatchEvent(new Event('focus'))"); pg.wait_for_timeout(450)
shown = lambda pg: pg.evaluate('showText')
said = lambda pg: pg.evaluate('window.__spoken.map(x=>x.text||x)')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = page(b, {'aac.lang': 'ru', 'aac.settings': json.dumps({'hearTab': 'show'})})
    pg.click('#micBtn'); pg.wait_for_timeout(100)
    check('button on «Говорит собеседник»', pg.locator('#showClip').is_visible() and 'Показать скопированное' in pg.inner_text('#showClip'))
    # кнопка
    pg.evaluate("window.__clip=''"); pg.click('#showClip'); pg.wait_for_timeout(80)
    check('empty clipboard → hint', 'Копировать' in pg.inner_text('#showSt') and shown(pg) == '')
    pg.evaluate("window.__clip='Скоро приеду, жди'"); pg.click('#showClip'); pg.wait_for_timeout(120)
    check('button shows copied text big', shown(pg) == 'Скоро приеду, жди' and 'Скоро' in pg.inner_text('#showText'))
    check('button: text read aloud', any('Скоро приеду' in str(x) for x in pg.evaluate('window.__spoken')))
    check('full-screen button available', pg.locator('#showFull').is_visible())
    check('not written to diary', not any('Скоро приеду' in x['s'] for x in (pg.evaluate("JSON.parse(localStorage.getItem('aac.log'))") or [])))
    pg.evaluate("window.__clip='[16.11, 14:01] Саша: Я уже в пути\\n[16.11, 14:02] Саша: Буду через час'"); pg.click('#showClip'); pg.wait_for_timeout(100)
    check('WhatsApp multi-message prefixes removed', shown(pg) == 'Я уже в пути Буду через час')
    pg.click('#showClip'); pg.wait_for_timeout(100)
    check('button shows same text again', shown(pg) == 'Я уже в пути Буду через час')
    pg.evaluate("window.__clipDeny=true"); pg.click('#showClip'); pg.wait_for_timeout(80)
    check('no permission → explanation', 'Разрешите' in pg.inner_text('#showSt'))
    pg.evaluate("window.__clipDeny=false")
    # автопоказ выключен по умолчанию
    pg.evaluate("window.__clip='Новое сообщение'"); r0 = pg.evaluate('window.__clipReads'); switch_back(pg)
    check('auto off by default: nothing read', pg.evaluate('window.__clipReads') == r0 and shown(pg) != 'Новое сообщение')
    # включаем в настройках
    pg.click('#settingsBtn')
    check('settings open on 🎤 group', pg.evaluate("document.querySelector('#sett .sg.open').dataset.g") == 'mic')
    check('checkbox label', 'скопированный в мессенджере' in pg.inner_text('#sett .sg[data-g=mic] .sgb'))
    pg.check('#setClipAuto'); pg.wait_for_timeout(80)
    check('enabling asks for clipboard at once (permission prompt on a tap)', pg.evaluate('window.__clipReads') == r0 + 1)
    pg.click('#closeSettBtn'); pg.wait_for_timeout(50)
    check('saved', pg.evaluate('settings.clipAuto') is True)
    switch_back(pg)
    check('text copied before enabling is not shown', shown(pg) != 'Новое сообщение')
    pg.evaluate("window.__clip='Ты поел?'"); n0 = len(pg.evaluate('window.__spoken')); switch_back(pg)
    check('auto: new copied text shown on switching back', shown(pg) == 'Ты поел?')
    check('auto: read aloud (showAuto on)', len(pg.evaluate('window.__spoken')) > n0)
    pg.evaluate("showText='';renderShow()"); switch_back(pg)
    check('auto: same text not shown twice', shown(pg) == '')
    pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.evaluate("window.__clip='Позвони мне'"); pg.evaluate("document.dispatchEvent(new Event('visibilitychange'))"); pg.wait_for_timeout(450)
    check('auto: works on visibilitychange too', shown(pg) == 'Позвони мне')
    # не на той вкладке / не на том экране
    pg.locator('.tabs .tab').nth(0).click(); pg.evaluate("window.__clip='Другое 1'"); switch_back(pg)
    check('auto: not on «Говорит человек»', pg.evaluate('showText') != 'Другое 1')
    pg.click('#home'); switch_back(pg)
    check('auto: not on home screen', pg.evaluate('showText') != 'Другое 1')
    pg.click('#micBtn'); pg.locator('.tabs .tab').nth(1).click(); pg.wait_for_timeout(450)
    check('auto: shown when the tab is opened', shown(pg) == 'Другое 1')
    # окно поверх — не мешаем
    pg.evaluate("window.__clip='Другое 2'"); pg.click('#settingsBtn'); switch_back(pg)
    check('auto: not while settings are open', shown(pg) != 'Другое 2')
    pg.click('#closeSettBtn')
    pg.evaluate("window.__clip='   '"); switch_back(pg)
    check('auto: empty clipboard ignored silently', pg.inner_text('#showSt') == '')
    # showAuto выключен — показ без голоса
    pg.evaluate("settings.showAuto=false;window.__clip='Тихий текст'"); n0 = len(pg.evaluate('window.__spoken')); switch_back(pg)
    check('auto + showAuto off: shown silently', shown(pg) == 'Тихий текст' and len(pg.evaluate('window.__spoken')) == n0)
    check('no script errors', not errors)
    pg.context.close()
    # вёрстка и языки
    for L, word in [('uk', 'Показати скопійоване'), ('en', 'Show copied text'), ('ru', 'Показать скопированное')]:
        for W, H in [(277, 492), (360, 640)]:
            pg = page(b, {'aac.lang': L, 'aac.settings': json.dumps({'hearTab': 'show'})}, W, H)
            pg.click('#micBtn'); pg.wait_for_timeout(120)
            check(f'{L} {W}: label', word in pg.inner_text('#showClip'))
            check(f'{L} {W}: no horizontal scroll', pg.evaluate("document.querySelector('#main').scrollWidth<=document.querySelector('#main').clientWidth"))
            check(f'{L} {W}: «Говорить» still fully visible on entry', pg.evaluate("(()=>{const r=document.querySelector('#showMic').getBoundingClientRect(),m=document.querySelector('#main').getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom+1})()"))
            pg.screenshot(path=f'{OUT}/clip_{L}_{W}.png')
            pg.click('#helpBtn')
            check(f'{L} {W}: help item', '📋' in pg.text_content('#help'))
            pg.context.close()
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
