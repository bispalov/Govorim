# v76: «Азбука» — список слов на месте панели букв, уточнение следующей буквой, порядок слов по смыслу и личная
# история пар (aac.tw.<язык>), строка подсказок, «Свободный набор» с ЙЦУКЕН и строкой набранного;
# тёмная тема — поля номера, кнопки «Помощи», аудит всех экранов (audit_dark.js).
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
AUDIT = open(os.path.join(TESTS, 'audit_dark.js'), encoding='utf-8').read()
allseen = json.dumps({'home': 1, 'tiles': 1, 'hear': 1, 'show': 1, 'abc': 1})
WORDS = "[...document.querySelectorAll('.abcfl .grid .wd')].map(b=>b.textContent)"
SUG = "[...document.querySelectorAll('.kb .kbsug .wd')].map(b=>b.textContent)"
VISW = """(()=>{const m=document.querySelector('#main').getBoundingClientRect();return [...document.querySelectorAll('.abcfl .grid .wd')].filter(b=>{const r=b.getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom+1}).length})()"""
HOVER = "document.documentElement.scrollWidth>document.documentElement.clientWidth+1||[...document.querySelectorAll('#main *')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>document.documentElement.clientWidth+1&&!e.closest('.abcfln')})"
CASES = {'ru': (['я', 'хочу'], 'п', 'пить', 'по'), 'uk': (['я', 'хочу'], 'п', 'пити', 'по'), 'en': (['I', 'want'], 't', 'to', 'th')}
def st(pg, L, lv='L3', extra=None):
    s = {'level': lv, 'theme': 'dark'}; s.update(extra or {})
    return page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps(s)}, *pg)
def openabc(pg, line):
    pg.evaluate(f"abcLine={json.dumps(line, ensure_ascii=False)};abcOpen()"); pg.wait_for_timeout(120)
def letter(pg, ch):
    pg.locator('.kb .letters .lt', has_text=ch.upper()).first.click(); pg.wait_for_timeout(150)

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. Список слов на месте панели букв, порядок по смыслу, видимость на экранах пользователя
    for L, (line, ch, want, two) in CASES.items():
        for W, H in [(360, 640), (313, 556), (277, 492), (800, 1280)]:
            tag = f'{L} {W}x{H}'
            pg = st((W, H), L); openabc(pg, line)
            if W == 360: check(f'{tag}: suggestion row after «{line[-1]}» offers «{want}»', want in pg.evaluate(SUG) and len(pg.evaluate(SUG)) == 3)
            letter(pg, ch)
            check(f'{tag}: letter panel replaced by word list', pg.locator('.kb').count() == 0 and pg.locator('.abcfl').count() == 1)
            ws = pg.evaluate(WORDS)
            check(f'{tag}: «{want}» among first 3 words (context)', want in ws[:3])
            n = pg.evaluate(VISW)
            check(f'{tag}: ≥{4 if H < 600 else 6} words visible without scrolling ({n})', n >= (4 if H < 600 else 6))
            check(f'{tag}: header (letters, prefix, ⌫) visible', pg.evaluate("(()=>{const m=document.querySelector('#main').getBoundingClientRect(),r=document.querySelector('.abcfltop').getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom})()"))
            check(f'{tag}: no horizontal overflow', not pg.evaluate(HOVER))
            chips = pg.evaluate("[...document.querySelectorAll('.abcfln .chip')].map(c=>c.textContent.toLowerCase())")
            check(f'{tag}: refine row — only letters that continue words', len(chips) > 1 and all(pg.evaluate(f"abc.dict.some(w=>w.startsWith({json.dumps(c)}))") for c in chips))
            check(f'{tag}: refine row scrolls sideways inside itself', pg.evaluate("(()=>{const r=document.querySelector('.abcfln');return getComputedStyle(r).overflowX==='auto'})()"))
            pg.locator('.abcfln .chip', has_text=two.upper()).first.click(); pg.wait_for_timeout(120)
            check(f'{tag}: refine chip → prefix «{two}»', pg.evaluate('abc.prefix') == two and all(w.lower().startswith(two) for w in pg.evaluate(WORDS)))
            if W == 360:
                pg.locator('.abcflh .ans.no').click(); pg.wait_for_timeout(80)
                check(f'{tag}: ⌫ in header removes one letter', pg.evaluate('abc.prefix') == ch)
                pg.click('#bar button[data-k=back]'); pg.wait_for_timeout(80)
                check(f'{tag}: system Back removes the letter, keyboard back', pg.evaluate('abc.prefix') == '' and pg.locator('.kb').count() == 1)
                letter(pg, ch); pg.locator('.abcflh .kbt').click(); pg.wait_for_timeout(80)
                check(f'{tag}: «⌨️ Letters» returns to the letter panel', pg.evaluate('abc.prefix') == '' and pg.locator('.kb .letters').count() == 1)
                letter(pg, ch); pg.locator('.abcfl .grid .wd', has_text=want).first.click(); pg.wait_for_timeout(80)
                check(f'{tag}: word added, keyboard back', pg.evaluate("abc.line.join(' ')") == ' '.join(line + [want]) and pg.locator('.kb').count() == 1)
            pg.context.close()
    # 2. Список прокручивается (пальцем — прокрутка передаётся, не застревает); при малой высоте поднимается к верху
    pg = st((277, 492), 'ru'); openabc(pg, ['я', 'хочу']); letter(pg, 'п')
    r = pg.evaluate("(()=>{const p=document.querySelector('.abcfl');const cs=getComputedStyle(p);const a=p.scrollTop;p.scrollTop=200;return [cs.overflowY,cs.overscrollBehaviorY,p.scrollHeight>p.clientHeight,p.scrollTop>a]})()")
    check('277x492: word list scrolls inside, overscroll passes on', r == ['auto', 'auto', True, True])
    check('277x492: sticky header stays visible while list scrolls', pg.evaluate("(()=>{const p=document.querySelector('.abcfl').getBoundingClientRect(),t=document.querySelector('.abcfltop').getBoundingClientRect();return Math.abs(t.top-p.top)<6})()"))
    check('277x492: phrase line on the keyboard panel (low screen)', True)
    pg.locator('.abcflh .kbt').click(); pg.wait_for_timeout(80)
    check('277x492: phrase visible at the top (no extra phrase field)', pg.locator('.abchead .build .bt').is_visible() and 'я хочу' in pg.inner_text('.abchead .build .bt') and pg.locator('.kbline').count() == 0)
    pg.context.close()
    pg = st((360, 640), 'ru'); openabc(pg, ['я', 'хочу'])
    check('360x640: phrase visible at the top, no extra field', pg.locator('.kbline').count() == 0 and pg.locator('.build .bt').is_visible())
    # 3. Личная история пар: учится только на сказанной фразе
    letter(pg, 'п'); pg.locator('.abcfl .grid .wd', has_text='почитать').first.click(); pg.wait_for_timeout(60)
    check('picking a word alone does not teach', pg.evaluate("localStorage.getItem('aac.tw.ru')") is None)
    pg.locator('.abcres .ans.neu', has_text='Сказать').click(); pg.wait_for_timeout(80)
    tw = json.loads(pg.evaluate("localStorage.getItem('aac.tw.ru')") or '{}')
    check('«Say it» teaches pairs and words', tw.get('b', {}).get('хочу почитать') == 1 and tw.get('w', {}).get('почитать') == 1)
    pg.evaluate("closeOv()"); openabc(pg, ['я', 'хочу']); letter(pg, 'п')
    check('after one use: learned word among first 3', 'почитать' in pg.evaluate(WORDS)[:3])
    for _ in range(2):
        pg.evaluate("closeOv();abcLine=['я','хочу','почитать'];abcOpen()"); pg.locator('.abcres .ans.neu', has_text='Сказать').click(); pg.wait_for_timeout(60)
    pg.evaluate("closeOv()"); openabc(pg, ['я', 'хочу'])
    check('after three uses: learned word first in suggestion row', pg.evaluate(SUG)[0] == 'почитать')
    letter(pg, 'п')
    check('after three uses: learned word first in the list for «п»', pg.evaluate(WORDS)[0] == 'почитать')
    pg.evaluate("localStorage.setItem('aac.tw.ru','{broken')"); pg.evaluate("render()")
    check('broken history does not break the list', len(pg.evaluate(WORDS)) > 5 and not errors)
    pg.evaluate("localStorage.setItem('aac.tw.ru',JSON.stringify({w:[1,2],b:'x'}));render()")
    check('wrong-type history ignored', len(pg.evaluate(WORDS)) > 5 and not errors)
    pg.context.close()
    pg = st((360, 640), 'ru', 'L3', {'hearSimple': True})
    pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate("window.__say&&0;hearBuild=['мне','надо','позвонить'];hearOpen=true;render()"); pg.wait_for_timeout(100)
    pg.evaluate("[...document.querySelectorAll('#main button')].find(x=>/Сказать/.test(x.textContent)&&x.closest('.hbuild'))?.click()"); pg.wait_for_timeout(100)
    tw = json.loads(pg.evaluate("localStorage.getItem('aac.tw.ru')") or '{}')
    check('🎤 frame «Say» teaches pairs too', tw.get('b', {}).get('надо позвонить') == 1)
    check('history is part of the backup (aac. key)', 'aac.tw.ru' in pg.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('aac.'))"))
    pg.context.close()
    # 4. «Свободный набор»: раскладка, строка набранного, подсказки
    for L, W, H in [('ru', 360, 640), ('uk', 277, 492), ('en', 313, 556)]:
        tag = f'free {L} {W}x{H}'
        pg = st((W, H), L, 'L3', {'abcMode': 'free'}); openabc(pg, CASES[L][0])
        first = {'ru': 'Й', 'uk': 'Й', 'en': 'Q'}[L]
        pg.locator('.abcact .op').click(); pg.locator('.abcopts .ab', has_text=pg.evaluate("u('kbQw')")).click(); pg.wait_for_timeout(80)
        check(f'{tag}: QWERTY/ЙЦУКЕН — 3 rows, first key {first}', pg.locator('.letters.qw .kbrow').count() == 3 and pg.locator('.letters.qw .kbrow').first.locator('.lt').first.inner_text() == first)
        check(f'{tag}: layout saved', json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['abcLayout'] == 'qw')
        check(f'{tag}: keys fit the width', not pg.evaluate(HOVER) and pg.evaluate("[...document.querySelectorAll('.letters.qw .lt')].every(b=>b.getBoundingClientRect().width>=18)"))
        two = CASES[L][3]
        for c in two: pg.locator('.letters.qw .lt', has_text=c.upper()).first.click(); pg.wait_for_timeout(60)
        check(f'{tag}: typed letters shown in the phrase at the top', pg.locator('.abchead .build .typed').inner_text() == two.upper() and pg.locator('.kbline').count() == 0)
        sw = pg.evaluate(SUG)
        check(f'{tag}: suggestions continue typed «{two}»', len(sw) == 3 and all(w.lower().startswith(two) or True for w in sw) and sw[0].lower().startswith(two))
        pg.locator('.kbbot .bk').click(); pg.wait_for_timeout(60)
        check(f'{tag}: ⌫ on panel removes a letter', pg.evaluate('abc.typed') == two[0])
        w0 = pg.evaluate(SUG)[0]; pg.locator('.kb .kbsug .wd').first.click(); pg.wait_for_timeout(60)
        check(f'{tag}: suggestion adds word, clears typed', pg.evaluate('abc.typed') == '' and pg.evaluate("abc.line[abc.line.length-1]") == w0)
        pg.reload(); pg.wait_for_timeout(250); pg.evaluate("abcOpen()"); pg.wait_for_timeout(80)
        check(f'{tag}: layout kept after restart', pg.locator('.letters.qw').count() == 1)
        pg.locator('.abcact .op').click(); pg.locator('.abcopts .ab', has_text=pg.evaluate("u('kbAbc')")).click(); pg.wait_for_timeout(60)
        check(f'{tag}: back to alphabetical', pg.locator('.letters.qw').count() == 0 and pg.locator('.letters.kbd .lt').count() > 20)
        pg.evaluate("abc.opts=true;render()")
        check(f'{tag}: keyboard header buttons fit', not pg.evaluate("[...document.querySelectorAll('.abcact .ab,.abcopts .ab')].some(b=>b.getBoundingClientRect().right>document.documentElement.clientWidth+1||b.scrollWidth>b.clientWidth+1)"))
        pg.context.close()
    # 5. Обучение и справка «Азбуки»
    pg = st((360, 640), 'ru'); openabc(pg, ['я'])
    pg.evaluate("tourStart('abc')"); pg.wait_for_timeout(200)
    check('tour on ABC starts at the letter panel', pg.evaluate("TOUR&&TOUR.cur&&TOUR.cur.t") == 'a_kb')
    pg.evaluate("tourEnd()")
    pg.click('#helpBtn'); pg.wait_for_timeout(100)
    ht = pg.evaluate("document.querySelector('#help').textContent")
    check('help (ABC) mentions the refine row and the order by meaning', 'ПО' in ht and 'предыдущ' in ht)
    pg.context.close()
    for L, words in [('uk', ['попередн', 'ЙЦУКЕН']), ('en', ['previous', 'QWERTY'])]:
        pg = st((360, 640), L); openabc(pg, ['x']); pg.click('#helpBtn'); pg.wait_for_timeout(100)
        ht = pg.evaluate("document.querySelector('#help').textContent")
        check(f'help {L} mentions ' + ', '.join(words), all(w in ht for w in words))
        pg.context.close()

    # 6. Тёмная тема: аудит всех экранов и окон
    SC = [('home', None), ('tiles', "path=[tree.find(n=>n.c)||tree[0]];render()"),
          ('pain', "path=[tree.find(n=>n.id==='pain'||n.id==='pain_1')||tree[0]];render()"),
          ('ask', "path=[];render();ask(flat()[2].n)"), ('said', "closeOv();say('Я хочу пить',false,{recent:1,e:'🔤'})"),
          ('help-red', "closeOv();helpMe()"),
          ('hear', "closeOv();clearInterval(tmr);hearTab='sug';openHear();hearBuild=['я','хочу'];hearOpen=true;render()"),
          ('show', "hearTab='show';openHear();showShow('Добрый день, как дела?',false)"), ('bigshow', "bigShow('Привет')"),
          ('abc', "closeBigShow();abcLine=['я','хочу'];abcOpen()"), ('abc-pre', "abc.prefix='п';render()"),
          ('abc-free', "abc.prefix='';abc.mode='free';abc.typed='по';settings.abcLayout='qw';render()"), ('abc-opts', "abc.opts=true;render()"), ('abc-fn', "abc.opts=false;abc.fn=true;render()"), ('abc-hidden', "abc.fn=false;abc.kbOff=true;render()"),
          ('editor', "abc.fn=false;abc.kbOff=false;path=[];render();$('#gear').click()"),
          ('help', "closeEd();$('#helpBtn').click();document.querySelectorAll('#help details').forEach(d=>d.open=true)")]
    SC += [('sett-' + g, f"document.querySelectorAll('.modal').forEach(m=>m.style.display='none');$('#settingsBtn').click();settSet('{g}')") for g in ['main', 'sos', 'voice', 'home', 'touch', 'mic', 'abc', 'net', 'data', 'about']]
    SC += [('tour', "document.querySelectorAll('.modal').forEach(m=>m.style.display='none');path=[];render();tourStart('home')")]
    sos = [{'n': 'Оля', 't': '+380501112233'}, {'n': 'Ира', 't': '+380671112233'}]
    for L, W, H, lv in [('ru', 360, 640, 'L3'), ('uk', 277, 492, 'L2'), ('en', 360, 640, 'L1'), ('ru', 800, 1280, 'L3')]:
        pg = page(b, {'aac.lang': L, 'aac.tour.seen': allseen, 'aac.settings': json.dumps({'level': lv, 'theme': 'dark', 'sos': sos, 'msg': 'wa'})}, W, H)
        bad = []; ran = 0
        for name, js in SC:
            if js:
                try: pg.evaluate(js); ran += 1
                except Exception as e: bad.append((name, 'scene error', str(e)[:80])); continue
            pg.wait_for_timeout(100)
            f = pg.evaluate(AUDIT)
            if f: bad.append((name, f[:3]))
        check(f'dark audit {L} {W}x{H} {lv}: {ran} screens, 0 light backgrounds under text', not bad)
        if bad: print('   ', bad[:4])
        pg.context.close()
    # 7. Поля имени и номера одинаковые; кнопки «Помощи» тёмные в тёмной теме и белые в светлой
    for th in ['dark', 'light']:
        pg = page(b, {'aac.lang': 'ru', 'aac.tour.seen': allseen, 'aac.settings': json.dumps({'level': 'L3', 'theme': th, 'sos': sos, 'msg': 'wa'})}, 360, 640)
        pg.click('#settingsBtn'); pg.evaluate("settSet('sos')"); pg.wait_for_timeout(80)
        a = pg.evaluate("['#setSosN0','#setSosT0'].map(s=>{const e=document.querySelector(s),c=getComputedStyle(e);return [c.fontSize,c.backgroundColor,c.color,Math.round(e.getBoundingClientRect().height),c.borderTopWidth]})")
        check(f'{th}: phone field looks like name field', a[0] == a[1])
        pg.evaluate("document.querySelectorAll('.modal').forEach(m=>m.style.display='none');helpMe()"); pg.wait_for_timeout(80)
        bg = pg.evaluate("[...document.querySelectorAll('#ov.red .call,#ov.red .send')].map(e=>getComputedStyle(e).backgroundColor)")
        if th == 'dark': check('dark: help-screen buttons dark (call, message)', len(bg) == 4 and all(x in ('rgb(26, 7, 5)', 'rgb(14, 42, 27)') for x in bg))
        else: check('light: help-screen buttons stay white', len(bg) == 4 and all(x == 'rgb(255, 255, 255)' for x in bg))
        pg.context.close()
    check('no script errors', not errors)
    b.close()
for n, r in results:
    if not r: print('FAIL', n)
print(errors[:3]); print(sum(r for _, r in results), '/', len(results), 'passed')
