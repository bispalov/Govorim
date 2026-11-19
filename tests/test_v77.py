# v77: «Азбука» по образцу «⌨️ Писать» из «Мій голос»: закреплённый верх (фраза с набираемыми буквами + «Сказать так»,
# ряд значков «⌫ Слово / 🗑 / режим / ⋯»), клавиатура сразу под ним с высотой клавиш по экрану, нижний ряд
# «я, в, на…» / «␣ пробел» / ⌫, служебные слова на месте букв; без отдельной строки «фраза + набранное».
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
AUDIT = open(os.path.join(TESTS, 'audit_dark.js'), encoding='utf-8').read()
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
LINE = {'ru': ['я', 'хочу'], 'uk': ['я', 'хочу'], 'en': ['I', 'want']}
INMAIN = """(sel=>{const m=document.querySelector('#main').getBoundingClientRect();const e=[...document.querySelectorAll(sel)];return e.length>0&&e.every(x=>{const r=x.getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom+1})})"""
HOVER = "document.documentElement.scrollWidth>document.documentElement.clientWidth+1||[...document.querySelectorAll('#main *')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>document.documentElement.clientWidth+1&&!e.closest('.abcfln')})"
def st(W, H, L, extra=None):
    s = {'level': 'L3', 'theme': 'dark'}; s.update(extra or {})
    return page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}, W, H)
def openabc(pg, line):
    pg.evaluate(f"abcLine={json.dumps(line, ensure_ascii=False)};abcOpen()"); pg.wait_for_timeout(150)
ok = lambda pg, sel: pg.evaluate(INMAIN, sel)

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. Вёрстка: нет отдельной строки фразы, верх закреплён, клавиатура под ним целиком (где помещается)
    for L in ['ru', 'uk', 'en']:
        for W, H in [(360, 640), (313, 556), (277, 492), (800, 1280)]:
            for mode in ['free', 'prefix']:
                tag = f'{L} {W}x{H} {mode}'
                pg = st(W, H, L, {'abcMode': mode, 'abcLayout': 'qw'}); openabc(pg, LINE[L])
                if mode == 'free': pg.evaluate("abc.typed='po'.replace('po',lang==='en'?'to':'по');render()"); pg.wait_for_timeout(80)
                check(f'{tag}: no separate phrase field', pg.locator('.kbline').count() == 0)
                check(f'{tag}: phrase, «Say it», action row visible at top', ok(pg, '.abchead .build') and ok(pg, '.abchead .abcsay') and ok(pg, '.abcact .ab'))
                check(f'{tag}: keyboard right under the top', pg.evaluate("(()=>{const h=document.querySelector('.abchead').getBoundingClientRect(),k=document.querySelector('.kb').getBoundingClientRect();return k.top>=h.bottom-1&&k.top-h.bottom<16})()"))
                if mode == 'free' or H >= 556:
                    check(f'{tag}: whole keyboard visible (suggestions, letters, bottom row)', ok(pg, '.kb .lt') and ok(pg, '.kbbot .lt'))
                kh = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('.kb')).getPropertyValue('--kh'))")
                lo = 36 if H < 600 else 40
                check(f'{tag}: key height {lo}–64 px ({kh})', lo <= kh <= 64)
                check(f'{tag}: no horizontal overflow', not pg.evaluate(HOVER))
                check(f'{tag}: app title row hidden on narrow ABC screen' if W < 640 else f'{tag}: title shown on wide screen', (not pg.locator('header h1').is_visible()) == (W < 640))
                if W == 360 and L == 'ru':
                    pg.evaluate("document.querySelector('#main').scrollTop=9999"); pg.wait_for_timeout(60)
                    check(f'{tag}: top stays in place when the screen scrolls', ok(pg, '.abchead .abcsay'))
                pg.context.close()
    # 2. Свободный набор: набранное во фразе вверху, пробел, ⌫, «Сказать так» с набранным
    pg = st(360, 640, 'ru', {'abcMode': 'free'}); openabc(pg, ['я', 'хочу'])
    check('space disabled with nothing typed', pg.locator('.kbbot .sp').is_disabled())
    for c in 'зюзя': pg.locator('.kb .letters .lt', has_text=c.upper()).first.click(); pg.wait_for_timeout(30)
    check('typed letters in the phrase at the top, with caret', pg.inner_text('.abchead .build .typed') == 'ЗЮЗЯ' and pg.locator('.abchead .build .caret').count() == 1)
    pg.locator('.kbbot .bk').click(); pg.wait_for_timeout(40)
    check('⌫ deletes a letter', pg.evaluate('abc.typed') == 'зюз')
    pg.locator('.kb .letters .lt', has_text='Я').first.click(); pg.locator('.kbbot .sp').click(); pg.wait_for_timeout(60)
    check('space adds typed text as a word', pg.evaluate("abc.line.join(' ')") == 'я хочу зюзя' and pg.evaluate('abc.typed') == '')
    pg.locator('.kbbot .bk').click(); pg.wait_for_timeout(40)
    check('⌫ with nothing typed removes last word (undo offered)', pg.evaluate("abc.line.join(' ')") == 'я хочу' and pg.locator('.abcact .undo').count() == 1)
    pg.locator('.abcact .undo').click(); pg.wait_for_timeout(40)
    check('↶ undo restores the word', pg.evaluate("abc.line.join(' ')") == 'я хочу зюзя')
    pg.locator('.kb .letters .lt', has_text='Д').first.click(); pg.locator('.kb .letters .lt', has_text='А').first.click()
    pg.locator('.abchead .abcsay').click(); pg.wait_for_timeout(80)
    check('«Say it» speaks the line together with typed letters', 'я хочу зюзя да' in spoken(pg) if 'spoken' in dir() else pg.evaluate("window.__spoken.some(t=>t.includes('я хочу зюзя да'))"))
    pg.evaluate("closeOv()"); pg.wait_for_timeout(60)
    check('after saying: line and typed cleared, «Say it» disabled', pg.evaluate("abc.line.length+abc.typed.length") == 0 and pg.locator('.abchead .abcsay').is_disabled())
    pg.context.close()
    # 3. «Я, в, на…» на месте клавиатуры
    for mode in ['free', 'prefix']:
        pg = st(360, 640, 'ru', {'abcMode': mode}); openabc(pg, ['я'])
        pg.locator('.kbbot .fnk').click(); pg.wait_for_timeout(60)
        check(f'{mode}: function words open in place of the letters', pg.locator('.kb .fnp').count() == 1 and pg.locator('.kb .letters').count() == 0 and pg.locator('.kb .fnp .fnl').first.is_visible())
        pg.locator('.kbfnh .ab').click(); pg.wait_for_timeout(60)
        check(f'{mode}: «⌨️ Letters» returns the keyboard without adding', pg.locator('.kb .letters').count() == 1 and pg.evaluate("abc.line.join(' ')") == 'я')
        pg.locator('.kbbot .fnk').click(); pg.locator('.kb .fnp .chip').get_by_text('не', exact=True).first.click(); pg.wait_for_timeout(60)
        check(f'{mode}: choosing a word adds it and brings the keyboard back', pg.evaluate("abc.line.join(' ')") == 'я не' and pg.locator('.kb .letters').count() == 1)
        pg.locator('.kbbot .fnk').click(); pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(60)
        check(f'{mode}: system Back closes the function words first', pg.locator('.kb .letters').count() == 1 and pg.evaluate("abc.line.join(' ')") == 'я не')
        pg.context.close()
    pg = st(277, 492, 'uk', {'abcMode': 'free'}); openabc(pg, ['я'])
    pg.locator('.kbbot .fnk').click(); pg.wait_for_timeout(60)
    check('277x492: function-word panel scrolls inside, back button visible', ok(pg, '.kbfnh .ab') and pg.evaluate("getComputedStyle(document.querySelector('.kb .fnp')).overflowY") == 'auto' and not pg.evaluate(HOVER))
    pg.context.close()
    # 4. Ряд кнопок и «⋯»
    pg = st(360, 640, 'ru', {'abcMode': 'prefix'}); openabc(pg, ['я'])
    check('🗑 disabled with one word', pg.locator('.abcact .cl').is_disabled())
    pg.locator('.abcact .op').click(); pg.wait_for_timeout(40)
    labs = pg.locator('.abcopts .ab').all_inner_texts()
    check('⋯ (letters mode): hide letters and size', len(labs) == 2 and 'Скрыть' in labs[0] and 'Мельче' in labs[1])
    pg.locator('.abcopts .ab').first.click(); pg.wait_for_timeout(40)
    check('hide letters: one «show letters» button, options closed', pg.locator('.kb .kbshow').count() == 1 and pg.locator('.kb .letters').count() == 0 and pg.locator('.abcopts').count() == 0)
    pg.locator('.kb .kbshow').click(); pg.wait_for_timeout(40)
    check('show letters again', pg.locator('.kb .letters').count() == 1)
    pg.locator('.abcact .op').click(); pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(40)
    check('Back closes ⋯ options first', pg.locator('.abcopts').count() == 0 and pg.evaluate('!!abc'))
    pg.locator('.abcact .md').click(); pg.wait_for_timeout(40)
    check('mode button → free typing (saved)', pg.evaluate('abc.mode') == 'free' and json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['abcMode'] == 'free')
    pg.locator('.abcact .op').click()
    check('⋯ (free typing): hide, layout, size', len(pg.locator('.abcopts .ab').all_inner_texts()) == 3)
    pg.context.close()
    # 5. Обучение и справка
    pg = st(360, 640, 'ru'); openabc(pg, ['я', 'хочу'])
    pg.evaluate("tourStart('abc')"); pg.wait_for_timeout(150)
    seen = []
    for _ in range(6):
        t = pg.evaluate("TOUR&&TOUR.cur?TOUR.cur.t:null")
        if not t: break
        seen.append((t, pg.evaluate("TOUR.els.length")))
        pg.locator('#tourBox button.go').click(); pg.wait_for_timeout(120)
    check('tour ABC: letters, function-words key, say + actions, ⋯ — all found', [x[0] for x in seen if x[1]] == ['a_kb', 'a_fn', 'a_say', 'a_kbh'] or all(x[1] for x in seen) and {'a_kb', 'a_fn', 'a_say', 'a_kbh'} <= {x[0] for x in seen})
    pg.context.close()
    for L, words in [('ru', ['пробел', '«⋯»', 'нижнем ряду']), ('uk', ['пробіл', '«⋯»', 'нижньому ряду']), ('en', ['space', '“⋯”', 'bottom row'])]:
        pg = st(360, 640, L); openabc(pg, ['x']); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        ht = pg.evaluate("document.querySelector('#help').textContent")
        check(f'help {L}: ' + ', '.join(words), all(w in ht for w in words))
        pg.context.close()
    # 6. Тёмная тема на новых частях
    pg = st(277, 492, 'ru', {'abcMode': 'free'}); openabc(pg, ['я', 'хочу'])
    bad = []
    for js in ["abc.typed='по';render()", "abc.opts=true;render()", "abc.opts=false;abc.fn=true;render()", "abc.fn=false;abc.kbOff=true;render()", "abc.kbOff=false;abc.mode='prefix';abc.prefix='п';render()"]:
        pg.evaluate(js); pg.wait_for_timeout(60); f = pg.evaluate(AUDIT)
        if f: bad.append((js, f[:2]))
    check('dark: no light backgrounds under text in all ABC states', not bad)
    if bad: print(bad)
    pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
