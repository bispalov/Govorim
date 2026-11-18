# v63: «При запуске открывать экран, на котором закончили»
import json, os, shutil, threading, http.server, functools
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
window.__spoken=[];
const ss={cancel(){},speak(u){window.__spoken.push(u.text);setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
window.__recs=[];
class FakeSR{constructor(){window.__recs.push(this)}start(){setTimeout(()=>this.onstart&&this.onstart(),1)}stop(){this.onend&&this.onend()}abort(){this.onend&&this.onend()}}
window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
window.confirm=()=>true;
"""
results = []; errors = []
def check(n, c):
    results.append((n, bool(c))); print(('PASS ' if c else 'FAIL ') + n)

def ctxpage(b, ls, W=412, H=860):
    ctx = b.new_context(service_workers='block', viewport={'width': W, 'height': H})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
    init = STUB + ''.join(f"if(!sessionStorage.__i){{localStorage.setItem({json.dumps(k)},{json.dumps(v)})}}" for k, v in ls.items()) + "sessionStorage.__i=1;"
    pg.add_init_script(init); pg.goto(URL); pg.wait_for_timeout(300)
    return pg
def relaunch(pg):
    pg.reload(); pg.wait_for_timeout(300)
scr = lambda pg: pg.evaluate("hearOn?'hear:'+hearTab:abc?'abc':path.length?'path:'+path.map(n=>n.id).join('/'):'home'")
home_ok = lambda pg: scr(pg) == 'home' and pg.evaluate("document.body.classList.contains('at-home')")

with sync_playwright() as p:
    b = p.chromium.launch()
    base = {'aac.lang': 'ru'}

    # 1. По умолчанию выключено: всегда главный экран
    pg = ctxpage(b, base)
    check('default: resume off', pg.evaluate('settings.resume') is False)
    pg.click('#micBtn'); pg.locator('.tabs .tab').nth(1).click(); pg.wait_for_timeout(50)
    check('last screen remembered even when off', json.loads(pg.evaluate("localStorage.getItem('aac.lastScr')")) == {'v': 'hear'})
    relaunch(pg)
    check('off: starts on home screen', home_ok(pg))
    # 2. Включаем в настройках
    pg.click('#settingsBtn'); pg.click('#sett .sg[data-g=home] .sgh')
    check('checkbox is first in «Главный экран и плитки»', pg.evaluate("document.querySelector('#sett .sg[data-g=home] .sgb input').id") == 'setResume')
    check('label text', 'закончили' in pg.inner_text('#sett .sg[data-g=home] .sgb'))
    pg.check('#setResume'); pg.click('#sett .sg[data-g=main] .sgh')
    check('summary mentions it', 'последнего экрана' in pg.inner_text('#sett .sg[data-g=home] .sgs'))
    pg.click('#closeSettBtn')
    check('saved', pg.evaluate('JSON.parse(localStorage.getItem("aac.settings")).resume') is True)
    # 🎤 «Говорит собеседник»
    pg.click('#micBtn'); pg.wait_for_timeout(50)
    check('🎤 tab is «Говорит собеседник»', pg.evaluate('hearTab') == 'show')
    nrec = pg.evaluate('window.__recs.length')
    relaunch(pg)
    check('resume: 🎤 «Говорит собеседник»', scr(pg) == 'hear:show' and 'Говорит собеседник' in pg.inner_text('.tabs .tab.on'))
    check('resume: microphone not started', pg.evaluate('window.__recs.length') == 0)
    check('resume: title is 🎤 screen', pg.inner_text('#ttl').startswith('🎤'))
    # другая вкладка
    pg.locator('.tabs .tab').nth(0).click(); relaunch(pg)
    check('resume: 🎤 «Говорит человек»', scr(pg) == 'hear:sug')
    # «Назад» с восстановленного экрана ведёт на главный
    pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(50)
    check('Back from resumed 🎤 goes home', home_ok(pg))
    relaunch(pg)
    check('closed on home → starts on home', home_ok(pg))
    # «Азбука»
    pg.click('#abcBtn'); relaunch(pg)
    check('resume: ABC', scr(pg) == 'abc' and pg.locator('.letters').count() > 0)
    # раздел плиток
    pg.click('#home'); pg.locator('#main .tile').nth(0).click(); pg.wait_for_timeout(50)
    want = scr(pg); title = pg.inner_text('#ttl')
    ch = pg.locator('#main .tile')
    if ch.count(): ch.nth(0).click(); pg.wait_for_timeout(50)
    if pg.evaluate("document.querySelector('#ov').style.display==='flex'"): pg.click('#bar button[data-k=back]')
    want2 = scr(pg); title2 = pg.inner_text('#ttl')
    relaunch(pg)
    check('resume: tile section (deep path)', want2.startswith('path:') and scr(pg) == want2 and pg.inner_text('#ttl') == title2)
    pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(50)
    check('Back from resumed section goes one level up', scr(pg) in (want, 'home') and scr(pg) != want2)
    # уровень сменился — раздел не восстанавливается
    pg.evaluate("localStorage.setItem('aac.lastScr',JSON.stringify({v:'path',ids:['x_no_such'],lv:'L2'}))"); relaunch(pg)
    check('unknown section → home', home_ok(pg))
    pg.evaluate("localStorage.setItem('aac.lastScr','{bad json')"); relaunch(pg)
    check('broken record → home', home_ok(pg))
    check('no script errors', not errors)
    pg.context.close()

    # 3. L1: «Азбуки» нет — главный экран
    pg = ctxpage(b, {**base, 'aac.settings': json.dumps({'resume': True, 'level': 'L1'}), 'aac.lastScr': json.dumps({'v': 'abc'})})
    check('L1 + saved ABC → home', home_ok(pg))
    pg.context.close()

    # 4. Другой уровень — раздел не открывается
    pg = ctxpage(b, {**base, 'aac.settings': json.dumps({'resume': True, 'level': 'L3'}), 'aac.lastScr': json.dumps({'v': 'path', 'ids': ['pain'], 'lv': 'L2'})})
    check('section from another level → home', home_ok(pg))
    pg.context.close()

    # 5. Вёрстка группы на узком экране, uk/en
    for L, word in [('uk', 'закінчили'), ('en', 'finished')]:
        pg = ctxpage(b, {'aac.lang': L}, 277, 492)
        pg.click('#settingsBtn'); pg.click('#sett .sg[data-g=home] .sgh'); pg.wait_for_timeout(100)
        check(f'{L}: label', word in pg.inner_text('#sett .sg[data-g=home] .sgb'))
        check(f'{L} 277px: nothing sticks out', pg.evaluate('document.querySelector("#sett").scrollWidth<=document.querySelector("#sett").clientWidth'))
        pg.locator('#sett .sg[data-g=home]').screenshot(path=f'{OUT}/resume_{L}.png')
        pg.click('#closeSettBtn'); pg.click('#helpBtn')
        check(f'{L}: help item', ('останнього екрана' if L == 'uk' else 'last screen') in pg.text_content('#help'))
        pg.context.close()
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
