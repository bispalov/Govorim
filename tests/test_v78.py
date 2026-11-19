# v78: клавиатура «Азбуки» на экране 🎤 — правка слова в рамке («✎ Набрать другое слово», «＋ Вставить слово
# перед ним») и поле «Напечатать / Вписать или исправить текст»; клавиатура телефона — запасной вариант в «⋯».
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
AUDIT = open(os.path.join(TESTS, 'audit_dark.js'), encoding='utf-8').read()
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
HOVER = "document.documentElement.scrollWidth>document.documentElement.clientWidth+1||[...document.querySelectorAll('#main *')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>document.documentElement.clientWidth+1&&!e.closest('.abcfln')})"
FRAME = "hearBuild.join(' ')"
def st(W, H, L, extra=None):
    s = {'level': 'L3', 'theme': 'dark'}; s.update(extra or {})
    pg = page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}, W, H)
    pg.click('#micBtn'); pg.wait_for_timeout(100); return pg
def frame(pg, words, slot):
    pg.evaluate(f"hearBuild={json.dumps(words, ensure_ascii=False)};hearOpen=true;hearSlot={slot};hearTyp=null;refreshHear()"); pg.wait_for_timeout(80)
def open_typer(pg, which):
    pg.locator('.slotbox .chip', has_text=which).first.click(); pg.wait_for_timeout(120)
def letter(pg, scope, ch):
    pg.locator(f'{scope} .kb .letters .lt', has_text=ch.upper()).first.click(); pg.wait_for_timeout(120)
WORDS = lambda pg, scope: pg.evaluate(f"[...document.querySelectorAll('{scope} .abcfl .wd')].map(b=>b.textContent)")
REP = {'ru': (['у', 'оксаны', 'есть', 'прогуны'], 3, 'п', 'подруги', 'Набрать', 'Вставить'),
       'uk': (['у', 'оксани', 'є', 'прогуни'], 3, 'п', 'подруги', 'Набрати', 'Вставити'),
       'en': (['call', 'my', 'sistor'], 2, 's', 'sister', 'Type another', 'Insert')}

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. Замена слова: клавиатура приложения, слова по звучанию и соседям, запоминание
    for L, (ws, i, ch, want, t_rep, t_ins) in REP.items():
        for simple in [True, False]:
            for W, H in [(360, 640), (277, 492)]:
                tag = f'{L} {W}x{H} {"simple" if simple else "full"}'
                pg = st(W, H, L, {'hearSimple': simple})
                frame(pg, ws, i); open_typer(pg, t_rep)
                check(f'{tag}: app keyboard opens (no phone-keyboard field)', pg.locator('.htyp .kb .letters').count() == 1 and pg.locator('.slotbox .typin').count() == 0 and pg.evaluate("!document.activeElement||document.activeElement.tagName!=='INPUT'"))
                check(f'{tag}: target line shows the word being replaced', ws[i] in pg.inner_text('.htyp .kbtarget'))
                sg = pg.evaluate("[...document.querySelectorAll('.htyp .kbsug .wd')].map(b=>b.textContent)")
                check(f'{tag}: suggestions without letters sound like «{ws[i]}»', len(sg) >= 1 and all(pg.evaluate(f"sndSim(norm({json.dumps(ws[i])}).trim(),norm({json.dumps(x)}).trim())>=0.6") for x in sg))
                check(f'{tag}: no horizontal overflow (keyboard)', not pg.evaluate(HOVER))
                letter(pg, '.htyp', ch)
                wl = WORDS(pg, '.htyp')
                check(f'{tag}: «{want}» among first 3 after «{ch.upper()}» ({wl[:3]})', want in wl[:3])
                check(f'{tag}: no horizontal overflow (list)', not pg.evaluate(HOVER))
                pg.locator('.htyp .abcfl .wd', has_text=want).first.click(); pg.wait_for_timeout(100)
                check(f'{tag}: word replaced in place, keyboard closed', pg.evaluate(f"hearBuild[{i}]") == want and pg.locator('.htyp').count() == 0)
                if W == 360 and simple:
                    pk = pg.evaluate(f"localStorage.getItem('aac.pick.{L}')") or ''
                    check(f'{tag}: replacement remembered in the pronunciation dictionary', want in pk and ws[i] in pk)
                pg.context.close()
    # 2. Свободный набор: слово как есть; вставка с учётом соседей; служебные слова; «Назад»; ✕
    pg = st(360, 640, 'ru', {'hearSimple': True})
    frame(pg, ['я', 'хочу', 'чай'], 2); open_typer(pg, 'Вставить')
    check('insert: target line says «before»', 'перед' in pg.inner_text('.htyp .kbtarget') and 'чай' in pg.inner_text('.htyp .kbtarget'))
    letter(pg, '.htyp', 'п')
    check('insert: next word counts («хочу _ чай» → «пить» first)', WORDS(pg, '.htyp')[0] == 'пить')
    pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(80)
    check('Back removes the letter first', pg.locator('.htyp .kb .letters').count() == 1 and pg.evaluate('hearTyp.k.prefix') == '')
    pg.locator('.htyp .kbbot .fnk').click(); pg.wait_for_timeout(60)
    check('function words open in place of letters', pg.locator('.htyp .kb .fnp').count() == 1)
    pg.locator('.htyp .kb .fnp .chip').get_by_text('не', exact=True).first.click(); pg.wait_for_timeout(80)
    check('function word inserted before «чай»', pg.evaluate(FRAME) == 'я хочу не чай')
    frame(pg, ['я', 'хочу', 'чай'], 2); open_typer(pg, 'Набрать')
    pg.locator('.htyp .abcact .md').click(); pg.wait_for_timeout(60)
    check('mode switch → free typing in the frame editor', pg.evaluate('hearTyp.k.mode') == 'free' and pg.locator('.htyp .kbbot .sp').count() == 1)
    for c in 'зюзя': letter(pg, '.htyp', c)
    check('typed letters shown in the target line', 'ЗЮЗЯ' in pg.inner_text('.htyp .kbtarget'))
    pg.locator('.htyp .kbbot .bk').click(); pg.wait_for_timeout(50)
    check('⌫ deletes a letter', pg.evaluate('hearTyp.k.typed') == 'зюз')
    letter(pg, '.htyp', 'я'); pg.locator('.htyp .kbbot .sp').click(); pg.wait_for_timeout(80)
    check('space puts the typed word as is', pg.evaluate(FRAME) == 'я хочу зюзя')
    frame(pg, ['я', 'хочу', 'чай'], 2); open_typer(pg, 'Набрать'); letter(pg, '.htyp', 'к')
    pg.click('#bar button[data-k=back]'); pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(80)
    check('Back: letters, then closes the keyboard', pg.locator('.htyp').count() == 0 and pg.evaluate('!hearTyp'))
    open_typer(pg, 'Набрать'); pg.locator('.htyp .abcact .cl').click(); pg.wait_for_timeout(60)
    check('✕ closes without changes', pg.locator('.htyp').count() == 0 and pg.evaluate(FRAME) == 'я хочу чай')
    # 3. Запасной вариант: клавиатура телефона и обратно
    open_typer(pg, 'Набрать'); pg.locator('.htyp .abcact .op').click(); pg.wait_for_timeout(60)
    pg.locator('.htyp .abcopts .ab', has_text='Клавиатура телефона').click(); pg.wait_for_timeout(150)
    check('⋯ → phone keyboard: old field focused', pg.locator('.slotbox .typin').count() == 1 and pg.evaluate("document.activeElement&&document.activeElement.classList.contains('typin')") and json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['typSys'] is True)
    pg.locator('.slotbox .kbapp').click(); pg.wait_for_timeout(120)
    check('«App keyboard» brings ours back', pg.locator('.htyp .kb').count() == 1 and json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['typSys'] is False)
    pg.context.close()
    # 4. Поле «Что услышано» (полный вид) и «Вписать или исправить текст» (упрощённый)
    for L, W, H in [('ru', 360, 640), ('uk', 277, 492), ('en', 313, 556)]:
        tag = f'field {L} {W}x{H}'
        pg = st(W, H, L, {'hearSimple': False})
        check(f'{tag}: phone keyboard suppressed on the field', pg.evaluate("document.querySelector('#hearIn').getAttribute('inputmode')") == 'none')
        pg.click('#hearIn'); pg.wait_for_timeout(120)
        check(f'{tag}: app keyboard opens under the field', pg.locator('#hearKb .kb .letters').count() == 1)
        check(f'{tag}: no horizontal overflow', not pg.evaluate(HOVER))
        w1 = {'ru': 'хочу', 'uk': 'хочу', 'en': 'want'}[L]
        letter(pg, '#hearKb', w1[0]); pg.locator('#hearKb .abcfl .wd', has_text=w1).first.click(); pg.wait_for_timeout(100)
        check(f'{tag}: word goes into the field', pg.input_value('#hearIn').strip() == w1)
        pg.locator('#hearKb .abcact .md').click(); pg.wait_for_timeout(50)
        w2 = {'ru': 'чай', 'uk': 'чай', 'en': 'tea'}[L]
        for c in w2: letter(pg, '#hearKb', c)
        check(f'{tag}: typed letters appear in the field', pg.input_value('#hearIn') == w1 + ' ' + w2)
        check(f'{tag}: ready phrases suggested as when typing', pg.locator('#hearSug .sug').count() > 0)
        pg.locator('#hearKb .kbbot .sp').click(); pg.wait_for_timeout(50)
        pg.locator('#hearKb .kbbot .bk').click(); pg.wait_for_timeout(50)
        check(f'{tag}: ⌫ with nothing typed removes the last word', pg.input_value('#hearIn').strip() == w1)
        pg.locator('#hearKb .abcact .ok').click(); pg.wait_for_timeout(60)
        check(f'{tag}: ✔ Done closes the keyboard', pg.locator('#hearKb .kb').count() == 0)
        pg.click('#hearIn'); pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(60)
        check(f'{tag}: Back closes the keyboard first', pg.locator('#hearKb .kb').count() == 0 and pg.evaluate('hearOn'))
        pg.context.close()
    pg = st(360, 640, 'ru', {'hearSimple': True})
    pg.locator('button.lnk', has_text='Вписать').click(); pg.wait_for_timeout(120)
    check('simple: «Type or correct» opens the app keyboard', pg.locator('#hearKb .kb .letters').count() == 1)
    letter(pg, '#hearKb', 'х'); pg.locator('#hearKb .abcfl .wd', has_text='хочу').first.click()
    letter(pg, '#hearKb', 'п'); pg.locator('#hearKb .abcfl .wd', has_text='пить').first.click(); pg.wait_for_timeout(80)
    pg.locator('#hearKb .abcact .ok').click(); pg.wait_for_timeout(120)
    check('simple: ✔ Done puts the words into the phrase', pg.evaluate(FRAME) == 'хочу пить')
    pg.locator('button.lnk', has_text='Вписать').click(); pg.wait_for_timeout(80)
    pg.locator('#hearKb .abcact .op').click(); pg.locator('#hearKb .abcopts .ab', has_text='Клавиатура телефона').click(); pg.wait_for_timeout(150)
    check('field: ⋯ → phone keyboard (inputmode restored)', pg.evaluate("document.querySelector('#hearIn').getAttribute('inputmode')") is None)
    pg.locator('#hearKb .kbapp').click(); pg.wait_for_timeout(150)
    check('field: back to app keyboard', pg.evaluate("document.querySelector('#hearIn').getAttribute('inputmode')") == 'none')
    pg.context.close()
    # 5. Тёмная тема
    pg = st(277, 492, 'ru', {'hearSimple': True}); bad = []
    for js in ["hearBuild=['у','оксаны','есть','прогуны'];hearOpen=true;hearSlot=3;hearTyp={i:3,mode:'rep',q:''};refreshHear()",
               "hearTyp.k.prefix='п';refreshHear()", "hearTyp.k.prefix='';hearTyp.k.fn=true;refreshHear()",
               "hearTyp.k.fn=false;hearTyp.k.opts=true;hearTyp.k.mode='free';hearTyp.k.typed='по';refreshHear()",
               "hearTyp=null;hearSlot=-1;refreshHear();hearType=true;render();hearKbOpen()"]:
        pg.evaluate(js); pg.wait_for_timeout(80); f = pg.evaluate(AUDIT)
        if f: bad.append((js[:30], f[:2]))
    check('dark: no light backgrounds under text in the 🎤 keyboard', not bad)
    if bad: print(bad)
    pg.context.close()
    # 6. Справка
    for L, words in [('ru', ['та же клавиатура', 'Клавиатура телефона']), ('uk', ['та сама клавіатура', 'Клавіатура телефона']), ('en', ['same keyboard', 'Phone keyboard'])]:
        pg = st(360, 640, L); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        ht = pg.evaluate("document.querySelector('#help').textContent")
        check(f'help {L}: ' + ', '.join(words), all(w in ht for w in words))
        pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
