# v66: справка — оглавление на главном экране, справка по режиму внутри режима
import json, os, shutil, threading, http.server, functools
from playwright.sync_api import sync_playwright
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
const ss={cancel(){},speak(u){setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
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
    pg.add_init_script(STUB + ''.join(f"localStorage.setItem({json.dumps(k)},{json.dumps(v)});" for k, v in ls.items()))
    pg.goto(URL); pg.wait_for_timeout(300); return pg
items = lambda pg: pg.evaluate("[...document.querySelectorAll('#help details.hi')].map(d=>[d.querySelector('summary').textContent,d.open])")
opn = lambda pg: (pg.click('#helpBtn'), pg.wait_for_timeout(80))
def close(pg): pg.locator('#help .helphead button').click()

with sync_playwright() as p:
    b = p.chromium.launch()
    # согласованность: число пунктов = HELP_KEYS во всех языках, ключи режимов существуют
    pg = page(b, {'aac.lang': 'ru'})
    check('HELP_KEYS matches every language', pg.evaluate("['ru','uk','en'].every(l=>U[l].helpDoc.s.length===HELP_KEYS.length)"))
    check('context keys exist', pg.evaluate("Object.values(HELP_CTX).flat().every(k=>HELP_KEYS.includes(k))"))
    # заголовки пунктов по ключам совпадают по смыслу во всех языках
    t = pg.evaluate("Object.fromEntries(['ru','uk','en'].map(l=>[l,['abc','show','clip','msg','pain'].map(k=>U[l].helpDoc.s[HELP_KEYS.indexOf(k)][0])]))")
    check('keys point to the right items (ru)', t['ru'][0].startswith('Азбука') and t['ru'][1].startswith('Говорит собеседник') and '📋' in t['ru'][2] and '✉️' in t['ru'][3] and t['ru'][4].startswith('Боль'))
    check('keys point to the right items (uk)', t['uk'][0].startswith('Абетка') and t['uk'][1].startswith('Говорить співрозмовник') and '📋' in t['uk'][2] and '✉️' in t['uk'][3] and t['uk'][4].startswith('Біль'))
    check('keys point to the right items (en)', t['en'][0].startswith('ABC') and t['en'][1].startswith('The other person speaks') and '📋' in t['en'][2] and '✉️' in t['en'][3] and t['en'][4].startswith('Pain'))
    # главный экран: вся справка оглавлением
    opn(pg); it = items(pg)
    check('home: full help, all items', len(it) == pg.evaluate('HELP_KEYS.length'))
    check('home: all collapsed (table of contents)', not any(o for _, o in it))
    check('home: no «Full help» button', pg.locator('#help .hall').count() == 0)
    check('home: title plain', pg.inner_text('#help h2') == '❓ Справка')
    pg.locator('#help details.hi summary', has_text='Азбука (подсказка').click()
    check('tap heading expands item', pg.evaluate("[...document.querySelectorAll('#help details.hi')].filter(d=>d.open).length") == 1 and pg.locator('#help details[open] p, #help details[open] li').first.is_visible())
    pg.click('#help .hexp')
    check('expand all', all(o for _, o in items(pg)) and 'Свернуть' in pg.inner_text('#help .hexp'))
    pg.click('#help .hexp')
    check('collapse all', not any(o for _, o in items(pg)))
    close(pg)
    # 🎤 «Говорит собеседник»
    pg.evaluate("settings.hearTab='show';hearTab='show'"); pg.click('#micBtn'); opn(pg); it = items(pg)
    check('🎤 show: only its items, open', 3 <= len(it) <= 7 and all(o for _, o in it))
    check('🎤 show: right items', it[0][0].startswith('Говорит собеседник') and any('📋' in x for x, _ in it))
    check('🎤 show: title names the mode', 'Говорит собеседник' in pg.inner_text('#help h2'))
    pg.click('#help .hall'); pg.wait_for_timeout(50)
    check('«Full help» → whole help', len(items(pg)) == pg.evaluate('HELP_KEYS.length') and pg.evaluate('#help'.replace('#help', 'helpEl.scrollTop')) == 0)
    close(pg)
    pg.locator('.tabs .tab').nth(0).click(); opn(pg); it = items(pg)
    check('🎤 person: its items', it[0][0].startswith('Подсказка по сказанному') and 'Говорю я' in pg.inner_text('#help h2'))
    # Android «Назад» закрывает справку
    pg.evaluate("appBack()"); check('Back closes help', pg.evaluate("helpEl.style.display") == 'none')
    # «Азбука»
    pg.click('#abcBtn'); opn(pg); it = items(pg)
    check('ABC: its items', it[0][0].startswith('Азбука') and len(it) <= 7 and 'Азбука' in pg.inner_text('#help h2'))
    close(pg)
    # раздел плиток
    pg.click('#home'); pg.locator('#main .tile').first.click(); pg.wait_for_timeout(80)
    if pg.evaluate("document.querySelector('#ov').style.display==='flex'"): pg.evaluate("closeOv()")
    if pg.evaluate("path.length"):
        ttl = pg.inner_text('#ttl'); opn(pg); it = items(pg)
        check('tiles: section items', any(x.startswith('Боль') for x, _ in it) and ttl in pg.inner_text('#help h2'))
        close(pg)
    else:
        check('tiles: section items (entered a section)', False)
    pg.click('#home'); opn(pg)
    check('back on home → full help again', len(items(pg)) == pg.evaluate('HELP_KEYS.length'))
    check('no script errors', not errors)
    pg.context.close()
    # вёрстка
    for L in ['uk', 'en', 'ru']:
        for W, H in [(277, 492), (360, 640)]:
            pg = page(b, {'aac.lang': L, 'aac.settings': json.dumps({'hearTab': 'show'})}, W, H)
            opn(pg)
            check(f'{L} {W}: full help no horizontal scroll', pg.evaluate("helpEl.scrollWidth<=helpEl.clientWidth"))
            check(f'{L} {W}: ~fits in few screens collapsed', pg.evaluate("helpEl.scrollHeight") < H * 8)
            if W == 360: pg.screenshot(path=f'{OUT}/help_full_{L}.png')
            close(pg); pg.click('#micBtn'); opn(pg)
            check(f'{L} {W}: mode help no horizontal scroll', pg.evaluate("helpEl.scrollWidth<=helpEl.clientWidth"))
            if W == 277: pg.screenshot(path=f'{OUT}/help_show_{L}.png')
            pg.context.close()
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
