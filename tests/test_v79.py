# v79: кнопка ⌨️ у поля на вкладке «Говорит собеседник» (по умолчанию — клавиатура телефона);
# ⌫ в нижнем ряду и в режиме «по первой букве» (убирает последнее слово).
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
AUDIT = open(os.path.join(TESTS, 'audit_dark.js'), encoding='utf-8').read()
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
HOVER = "document.documentElement.scrollWidth>document.documentElement.clientWidth+1||[...document.querySelectorAll('#main *')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>document.documentElement.clientWidth+1&&!e.closest('.abcfln')})"
def st(W, H, L, extra=None):
    s = {'level': 'L3', 'theme': 'dark'}; s.update(extra or {})
    return page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}, W, H)
def show(pg):
    pg.click('#micBtn'); pg.wait_for_timeout(80); pg.evaluate("hearTab='show';openHear()"); pg.wait_for_timeout(150)
def letter(pg, scope, ch):
    pg.locator(f'{scope} .kb .letters .lt', has_text=ch.upper()).first.click(); pg.wait_for_timeout(100)
WD = {'ru': ('с', 'спасибо', 'п'), 'uk': ('д', 'дякую', 'п'), 'en': ('t', 'thank', 'p')}

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. Вкладка «Говорит собеседник»
    for L in ['ru', 'uk', 'en']:
        for W, H in [(360, 640), (313, 556), (277, 492)]:
            tag = f'show {L} {W}x{H}'
            pg = st(W, H, L); show(pg)
            check(f'{tag}: phone keyboard by default (no inputmode, app keyboard closed)', pg.evaluate("document.querySelector('#showIn').getAttribute('inputmode')") is None and pg.locator('#showKb .kb').count() == 0)
            check(f'{tag}: ⌨️ button next to the field, fits', pg.locator('#showKbBtn').is_visible() and not pg.evaluate(HOVER))
            pg.click('#showKbBtn'); pg.wait_for_timeout(150)
            check(f'{tag}: ⌨️ opens the app keyboard, phone keyboard suppressed', pg.locator('#showKb .kb .letters').count() == 1 and pg.evaluate("document.querySelector('#showIn').getAttribute('inputmode')") == 'none' and pg.evaluate("document.querySelector('#showKbBtn').classList.contains('on')"))
            check(f'{tag}: no horizontal overflow with keyboard', not pg.evaluate(HOVER))
            ch, w, ch2 = WD[L]
            letter(pg, '#showKb', ch)
            wl = pg.evaluate("[...document.querySelectorAll('#showKb .abcfl .wd')].map(b=>b.textContent)")
            pick = next((x for x in wl if x.startswith(w)), wl[0] if wl else '')
            pg.locator('#showKb .abcfl .wd', has_text=pick).first.click(); pg.wait_for_timeout(120)
            check(f'{tag}: chosen word goes into the field ({pick})', pg.input_value('#showIn').strip() == pick)
            check(f'{tag}: field stays on screen', pg.evaluate("(()=>{const r=document.querySelector('#showIn').getBoundingClientRect(),m=document.querySelector('#main').getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom+1})()"))
            if W == 360:
                bk = pg.locator('#showKb .kbbot .bk')
                check(f'{tag}: ⌫ in first-letter mode', bk.count() == 1 and not bk.is_disabled())
                bk.click(); pg.wait_for_timeout(80)
                check(f'{tag}: ⌫ removes the last word', pg.input_value('#showIn').strip() == '' and pg.locator('#showKb .kbbot .bk').is_disabled())
                pg.locator('#showKb .abcact .md').click(); pg.wait_for_timeout(50)
                for c in 'abc' if L == 'en' else 'абв': letter(pg, '#showKb', c)
                check(f'{tag}: free typing letters appear in the field', pg.input_value('#showIn') == ('abc' if L == 'en' else 'абв'))
                pg.locator('#showKb .abcact .ok').click(); pg.wait_for_timeout(80)
                check(f'{tag}: ✔ Done closes, phone keyboard back', pg.locator('#showKb .kb').count() == 0 and pg.evaluate("document.querySelector('#showIn').getAttribute('inputmode')") is None and pg.input_value('#showIn').strip() == ('abc' if L == 'en' else 'абв'))
                pg.locator('#main .ans.neu', has_text=pg.evaluate("u('show_btn')")).first.click(); pg.wait_for_timeout(100)
                check(f'{tag}: «Show and speak» shows the typed phrase', pg.evaluate('showText') == ('abc' if L == 'en' else 'абв'))
                pg.click('#showKbBtn'); pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(80)
                check(f'{tag}: Back closes the keyboard, stays on the tab', pg.locator('#showKb .kb').count() == 0 and pg.evaluate('hearOn&&hearTab') == 'show')
                pg.click('#showKbBtn'); pg.click('#showKbBtn'); pg.wait_for_timeout(60)
                check(f'{tag}: ⌨️ again closes the keyboard', pg.locator('#showKb .kb').count() == 0)
            pg.context.close()
    # 2. ⌫ в режиме «по первой букве»: «Азбука» и поле «Что услышано»; при правке слова в рамке — нет
    pg = st(360, 640, 'ru', {'abcMode': 'prefix'}); pg.evaluate("abcLine=['я','хочу'];abcOpen()"); pg.wait_for_timeout(120)
    pg.locator('.abcres .kbbot .bk').click(); pg.wait_for_timeout(60)
    check('ABC first-letter: ⌫ removes last word, undo offered', pg.evaluate("abc.line.join(' ')") == 'я' and pg.locator('.abcact .undo').count() == 1)
    pg.evaluate("abc.line.length=0;abcUndo=null;render()")
    check('ABC first-letter: ⌫ disabled on empty line', pg.locator('.abcres .kbbot .bk').is_disabled())
    pg.context.close()
    pg = st(360, 640, 'ru', {'abcMode': 'prefix', 'hearSimple': False}); pg.click('#micBtn'); pg.wait_for_timeout(100)
    pg.click('#hearIn'); letter(pg, '#hearKb', 'х'); pg.locator('#hearKb .abcfl .wd', has_text='хочу').first.click(); pg.wait_for_timeout(80)
    pg.locator('#hearKb .kbbot .bk').click(); pg.wait_for_timeout(80)
    check('field «heard», first-letter: ⌫ removes the last word', pg.input_value('#hearIn').strip() == '')
    pg.evaluate("hearKb=null;hearKbDraw();hearBuild=['я','шучу'];hearOpen=true;hearSlot=1;refreshHear()"); pg.wait_for_timeout(80)
    pg.locator('.slotbox .chip', has_text='Набрать').first.click(); pg.wait_for_timeout(100)
    check('frame word editor: no word ⌫ (nothing to remove)', pg.locator('.htyp .kbbot .bk').count() == 0)
    pg.context.close()
    # 3. Тёмная тема и справка
    pg = st(277, 492, 'ru'); show(pg); bad = []
    for js in ["0", "showKbOpen()", "showKb.prefix='п';showKbDraw()", "showKb.prefix='';showKb.opts=true;showKbDraw()"]:
        pg.evaluate(js); pg.wait_for_timeout(80); f = pg.evaluate(AUDIT)
        if f: bad.append((js, f[:2]))
    check('dark: show tab with keyboard — no light backgrounds under text', not bad)
    if bad: print(bad)
    pg.context.close()
    for L, w in [('ru', 'кнопка ⌨️ справа от поля'), ('uk', 'кнопка ⌨️ праворуч від поля'), ('en', 'the ⌨️ button next to the field')]:
        pg = st(360, 640, L); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        check(f'help {L}: ⌨️ on the other-person tab', w in pg.evaluate("document.querySelector('#help').textContent"))
        pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
