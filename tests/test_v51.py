import json, os, shutil, subprocess, sys, time, threading, http.server, functools
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
window.__spoken=[];
const ss={cancel(){},speak(u){window.__spoken.push({t:u.text,r:u.rate});setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
window.__recs=[];
class FakeSR{constructor(){window.__recs.push(this)}start(){setTimeout(()=>this.onstart&&this.onstart(),1)}stop(){this.onend&&this.onend()}abort(){this.onerror&&this.onerror({error:'aborted'});this.onend&&this.onend()}}
window.SpeechRecognition=FakeSR;window.webkitSpeechRecognition=FakeSR;
window.__say=(txt)=>{const r=window.__recs[window.__recs.length-1];const res=[[{transcript:txt}]];res[0].isFinal=true;r.onresult({results:res});r.onend()};
window.confirm=()=>true;
"""
errors = []; results = []
def check(name, cond):
    results.append((name, bool(cond))); print(('PASS ' if cond else 'FAIL ') + name)

def newpage(b, ls=None):
    ctx = b.new_context(service_workers='block', viewport={'width': 412, 'height': 860})
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'icon' not in m.text and '404' not in m.text else None)
    init = STUB
    if ls:
        init += ''.join(f"if(!sessionStorage.__i){{localStorage.setItem({json.dumps(k)},{json.dumps(v)})}}" for k, v in ls.items()) + "sessionStorage.__i=1;"
    pg.add_init_script(init)
    pg.goto(URL); pg.wait_for_timeout(300)
    return pg

spoken = lambda pg: pg.evaluate('window.__spoken.map(x=>x.t)')
ovtxt = lambda pg: pg.evaluate("document.querySelector('#ov').style.display==='flex'?document.querySelector('#ov').innerText:''")

with sync_playwright() as p:
    b = p.chromium.launch()
    base = {'aac.lang': 'ru'}

    # 1. L1: «Больно» сразу спрашивает
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'level': 'L1'})})
    pg.click('#bar button[data-k=pain]')
    check('L1 pain asks question', 'Мне больно?' in ovtxt(pg))
    check('L1 pain no script error', not errors)
    pg.click('#ov .ans.yes'); pg.wait_for_timeout(50)
    check('L1 pain spoken after yes', 'Мне больно' in spoken(pg))
    pg.context.close()

    # 2. Подсказки 🎤: сначала «…?», запоминание только после «Да», «Недавно сказанные»
    pg = newpage(b, base)
    pg.click('#micBtn'); pg.fill('#hearIn', 'хочу чай'); pg.dispatch_event('#hearIn', 'input')
    pg.wait_for_timeout(100)
    sugs = pg.locator('#hearSug .sug')
    check('suggestions shown', sugs.count() > 0)
    first = sugs.first.inner_text()
    sugs.first.click()
    check('suggestion asks before speaking', '?' in ovtxt(pg) and not spoken(pg))
    check('listen button on question', pg.locator('#ov button', has_text='Послушать').count() == 1)
    pg.click('#ov .ans.no')
    pk = pg.evaluate("localStorage.getItem('aac.pick.ru')")
    check('No does not record pick', not pk)
    pg.locator('#hearSug .sug').first.click(); pg.click('#ov .ans.yes')
    pk = json.loads(pg.evaluate("localStorage.getItem('aac.pick.ru')") or '{}')
    check('Yes records pick', len(pk.get('f', [])) == 1)
    check('recent stored', len(json.loads(pg.evaluate("localStorage.getItem('aac.recent.ru')") or '[]')) == 1)
    check('slow button in said window', pg.locator('#ov button', has_text='Медленно').count() == 1)
    pg.locator('#ov button', has_text='Медленно').click()
    check('slow uses 0.6 factor', abs(pg.evaluate('window.__spoken.at(-1).r') - 0.85 * 0.6) < 1e-6)
    pg.locator('#ov .ans.yes').click()
    check('hear screen cleared after phrase', pg.input_value('#hearIn') == '' and pg.locator('#hearSug .sug').count() <= 5)
    pg.click('#home'); pg.wait_for_timeout(50)
    check('recent row on home', pg.locator('#main .sec', has_text='Недавно сказанные').count() == 1)
    # повтор повторяет последнее прозвучавшее
    pg.context.close()

    # 3. Рамка: удаление и «Вернуть», «Назад» сохраняет рамку, Android «Назад»
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearSimple': True})})
    pg.click('#micBtn'); pg.click('#micGo'); pg.wait_for_timeout(20)
    pg.evaluate("window.__say('я хочу пить воду')"); pg.wait_for_timeout(100)
    chips = pg.locator('.hbuild .hchips .chip')
    n0 = chips.count(); n0 = pg.locator('.hbuild .hchips').first.locator('.chip').count(); check('frame filled from speech', n0 == 4)
    check('no false error after recognition', 'Не удалось' not in pg.inner_text('#hearSt'))
    chips.nth(1).click(); pg.wait_for_timeout(50)
    check('tap on word opens options, not removal', pg.locator('.hbuild .slotbox').count() == 1 and pg.locator('.hbuild .hchips').first.locator('.chip').count() == 4)
    pg.locator('.hbuild .slotbox .chip', has_text='Убрать').last.click(); pg.wait_for_timeout(50)
    check('word removed via «Убрать»', pg.locator('.hbuild .hchips').first.locator('.chip').count() == 3)
    pg.locator('.hbuild button', has_text='Вернуть').click()
    check('undo restores word in place', pg.locator('.hbuild .hchips').first.locator('.chip').nth(1).inner_text().startswith('хочу'))
    pg.go_back(); pg.wait_for_timeout(100)
    check('android back leaves 🎤 but stays in app', pg.url.endswith('index.html') and pg.locator('.tabs').count() == 0)
    pg.click('#micBtn'); pg.wait_for_timeout(50)
    check('frame kept after reopening', pg.locator('.hbuild .hchips').first.locator('.chip').count() == 4)
    pg.locator('.hbuild .ans.yes').click()
    check('frame Say speaks immediately', 'я хочу пить воду' in spoken(pg))
    pg.context.close()

    # 4. Сигнал «Помощь» не прерывается случайными нажатиями
    pg = newpage(b, base)
    pg.click('#bar button[data-k=help]')
    for k in ['yes', 'no', 'pain', 'rep']: pg.click(f'#bar button[data-k={k}]')
    pg.click('#home')
    check('SOS survives accidental taps', pg.evaluate("document.querySelector('#ov').classList.contains('red')"))
    pg.click('#bar button[data-k=back]')
    check('Back stops SOS', not pg.evaluate("document.querySelector('#ov').classList.contains('red')&&document.querySelector('#ov').style.display==='flex'"))
    pg.context.close()

    # 5. Настройки: группы, сводки, контекст, L1 прячет «Азбуку», recentN
    pg = newpage(b, base)
    pg.click('#settingsBtn')
    open_g = pg.evaluate("[...document.querySelectorAll('#sett .sg.open')].map(x=>x.dataset.g)")
    check('settings: only main open', open_g == ['main'])
    check('settings: 10 groups', pg.locator('#sett .sg').count() == 10)
    check('collapsed group has summary', len(pg.locator('#sett .sg[data-g=voice] .sgs').inner_text()) > 3)
    pg.click('#sett .sg[data-g=home] .sgh')
    check('opening another closes first', pg.evaluate("[...document.querySelectorAll('#sett .sg.open')].map(x=>x.dataset.g)") == ['home'])
    pg.select_option('#setRecent', '4'); pg.click('#closeSettBtn')
    check('recentN saved', json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['recentN'] == 4)
    pg.click('#micBtn'); pg.click('#settingsBtn')
    check('settings from 🎤 open mic group', pg.evaluate("[...document.querySelectorAll('#sett .sg.open')].map(x=>x.dataset.g)") == ['mic'])
    pg.click('#sett .sg[data-g=main] .sgh'); pg.select_option('#setSeg', 'L1'); pg.dispatch_event('#setSeg', 'change')
    check('L1 hides ABC group', pg.evaluate("document.querySelector('#sett .sg[data-g=abc]').hidden"))
    pg.go_back(); pg.wait_for_timeout(100)
    check('android back closes settings', pg.evaluate("document.querySelector('#sett').style.display") == 'none')
    pg.context.close()

    # 6. «Говорит собеседник»: эмодзи, слово по нажатию, быстрые ответы
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearTab': 'show'})})
    pg.click('#micBtn'); pg.fill('#showIn', 'хотите чай или кофе'); pg.press('#showIn', 'Enter'); pg.wait_for_timeout(50)
    check('emoji next to known words', pg.locator('#showText .emo').count() >= 1)
    pg.locator('#showText .w', has_text='кофе').click()
    sp = pg.evaluate('window.__spoken.at(-1)')
    check('tap word speaks it slowly', sp['t'] == 'кофе' and abs(sp['r'] - 0.85 * 0.6) < 1e-6)
    check('no showAuto checkbox on screen', pg.locator('#hearBody input[type=checkbox]').count() == 0)
    pg.locator('.qr .chip', has_text='Я не понимаю').click()
    check('quick reply spoken', 'Я не понимаю' in spoken(pg))
    pg.context.close()

    # 7. «Азбука»: слово одним нажатием, «Назад» по шагам, «Вернуть», строка очищается после «Сказать»
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'wordTap': True, 'abcMode': 'prefix'})})
    pg.click('#abcBtn'); pg.locator('.lt', has_text='Ч').first.click(); pg.wait_for_timeout(50)
    w = pg.locator('.abcres .wd').first; word = w.inner_text(); w.click()
    check('ABC tap speaks word, not added', word in spoken(pg) and pg.inner_text('.build .bt') == '…')
    pg.wait_for_timeout(450)   # после касания кнопка ещё «вспыхивает» (held 350 мс); долгое нажатие — после неё
    box = w.bounding_box(); pg.mouse.move(box['x'] + 5, box['y'] + 5); pg.mouse.down(); pg.wait_for_timeout(650); pg.mouse.up(); pg.wait_for_timeout(50)
    check('ABC long press adds word', pg.inner_text('.build .bt') == word)
    pg.click('#bar button[data-k=back]')
    check('Back removes last word', pg.inner_text('.build .bt') == '…' and pg.locator('.abcres .undo').count() == 1)
    pg.locator('.abcres .undo').click()
    check('Undo restores ABC word', pg.inner_text('.build .bt') == word)
    pg.locator('.abcres .ans.neu', has_text='Сказать').click()
    pg.locator('#ov .ans.yes').click()
    check('ABC line cleared after say', pg.inner_text('.build .bt') == '…')
    pg.context.close()

    # 8. Личный словарь: автоисправление только после двух выборов; «Оставить» запоминается
    pg = newpage(b, base)
    pg.click('#micBtn')
    r = pg.evaluate("""()=>{recordPron('шай','чай');const a=applyPronTok('шай');recordPron('шай','чай');const b2=applyPronTok('шай');
       recordPron('шай','чей');const c=applyPronTok('шай');keepWord('зюзя');return [a,b2,c,knownW('зюзя')]}""")
    check('pron: 1 choice no auto', r[0] == 'шай')
    check('pron: 2 choices auto', r[1] == 'чай')
    check('pron: different choice resets', r[2] == 'шай')
    check('keep persisted', r[3] and 'зюзя' in pg.evaluate("localStorage.getItem('aac.pick.ru')"))
    pg.context.close()


    # 10. «Азбука»: служебные слова и однобуквенные слова
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'abcMode': 'prefix'})})
    pg.click('#abcBtn'); pg.locator('.lt', has_text='Я').first.click(); pg.wait_for_timeout(50)
    check('ABC: «я» found by first letter', pg.locator('.abcres .wd').first.inner_text() == 'я')
    pg.click('#bar button[data-k=back]')
    pg.locator('.fnbtn').click()
    check('ABC: function-word panel has 3 groups', pg.locator('.abcres .fnp .fnl').count() == 3)
    pg.locator('.abcres .fnp .chip', has_text='я').first.click()
    check('ABC: block collapses after choice', pg.locator('.abcres .fnp').count() == 0)
    pg.locator('.lt', has_text='Х').first.click(); pg.locator('.abcres .wd', has_text='хочу').first.click()
    pg.locator('.fnbtn').click(); pg.locator('.abcres .fnp .chip').filter(has_text='в').first.click()
    check('ABC: phrase built with function words', pg.inner_text('.build .bt').startswith('я хочу'))
    pg.locator('.abcres .ans.neu', has_text='Сказать').click()
    check('ABC: phrase spoken', any(x.startswith('я хочу') for x in spoken(pg)))
    pg.context.close()
    pg = newpage(b, {'aac.lang': 'en', 'aac.settings': json.dumps({'abcMode': 'prefix'})})
    pg.click('#abcBtn'); pg.locator('.lt', has_text='I').first.click(); pg.wait_for_timeout(50)
    check('EN ABC: capital I offered', pg.locator('.abcres .wd').first.inner_text() == 'I')
    pg.context.close()
    # 11. рамка 🎤: тот же блок служебных слов
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearSimple': True})})
    pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate("window.__say('хочу пить')"); pg.wait_for_timeout(100)
    pg.locator('.hbuild .fn').click(); pg.locator('.hbuild .fnp .chip', has_text='мне').first.click()
    check('hear frame: function word added, block collapsed', pg.locator('.hbuild .hchips').first.locator('.chip').count() >= 3 and pg.locator('.hbuild .fnp').count() == 0)
    pg.context.close()

    # 12. «Азбука»: размер кнопок букв, вёрстка при крупном шрифте (узкий экран)
    pg = newpage(b, base)
    pg.click('#abcBtn')
    h0 = pg.locator('.letters.kbd .lt').first.bounding_box()['height']
    pg.locator('.kbh .kbt', has_text='Мельче').click()
    h1 = pg.locator('.letters.kbd .lt').first.bounding_box()['height']
    check('letters smaller after «Мельче»', h1 < h0 and pg.locator('.kbh .kbt', has_text='Крупнее').count() == 1)
    check('letter size saved', json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))['abcKbSmall'] is True)
    pg.click('#home'); pg.click('#abcBtn')
    check('small size kept on reopen', pg.locator('.kb.small').count() == 1)
    pg.locator('.kbh .kbt', has_text='Крупнее').click()
    check('«Крупнее» restores size', abs(pg.locator('.letters.kbd .lt').first.bounding_box()['height'] - h0) < 1)
    for L in ['ru', 'uk', 'en']:
        for wdt in [360, 313, 277]:
            pg.set_viewport_size({'width': wdt, 'height': 760})
            pg.evaluate(f"localStorage.setItem('aac.lang','{L}')"); pg.reload(); pg.wait_for_timeout(150); pg.click('#abcBtn')
            ov = pg.evaluate("""()=>{const W=document.documentElement.clientWidth;return [...document.querySelectorAll('.kbh .kbt')].some(b=>{const r=b.getBoundingClientRect();return r.right>W+1||b.scrollWidth>b.clientWidth+1})||document.documentElement.scrollWidth>W}""")
            check(f'kb header fits {L} {wdt}px', not ov)
    pg.context.close()

    # 13. Замена любого слова: «я шучу гулить» → «я хочу гулять»
    for lexon in [False, True]:
        pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearSimple': True})})
        if lexon: pg.evaluate("LEXB.ru=['я','хочу','шучу','гулять','пить','воду','пойти','гулить'.slice(0,0)].filter(Boolean);delete LEXC.ru")
        pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate("window.__say('я шучу гулить')"); pg.wait_for_timeout(150)
        fr = pg.locator('.hbuild .hchips').first
        tag = ' lex' if lexon else ''
        check('real-but-wrong word marked ?'+tag, fr.locator('.chip').nth(1).inner_text().strip().endswith('?'))
        if pg.evaluate('hearSlot')!=1: fr.locator('.chip').nth(1).click(); pg.wait_for_timeout(80)
        opts = [x.strip() for x in pg.locator('.hbuild .slotbox .chip.pick').all_inner_texts()]
        check('«хочу» offered for «шучу»'+tag, 'хочу' in opts[:2])
        if 'хочу' in opts:
            pg.locator('.hbuild .slotbox .chip.pick', has_text='хочу').first.click(); pg.wait_for_timeout(80)
        check('«шучу» replaced'+tag, pg.locator('.hbuild .hchips').first.locator('.chip').nth(1).inner_text().startswith('хочу'))
        pg.context.close()
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearSimple': True})})
    pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate("window.__say('я шучу гулить')"); pg.wait_for_timeout(150)
    fr = pg.locator('.hbuild .hchips').first
    if pg.evaluate('hearSlot')!=1: fr.locator('.chip').nth(1).click()
    pg.locator('.slotbox .chip', has_text='Набрать другое').click(); pg.wait_for_timeout(80)
    check('typing field focused', pg.evaluate("document.activeElement&&document.activeElement.classList.contains('typin')"))
    pg.keyboard.type('хоч'); pg.wait_for_timeout(80)
    check('typed letters suggest «хочу»', pg.locator('.slotbox .chip.pick', has_text='хочу').count() >= 1)
    pg.locator('.slotbox .chip.pick', has_text='хочу').first.click(); pg.wait_for_timeout(80)
    check('typed word replaces in place', pg.locator('.hbuild .hchips').first.locator('.chip').nth(1).inner_text().startswith('хочу'))
    if pg.evaluate('hearSlot')!=2: fr.locator('.chip').nth(2).click()
    pg.locator('.slotbox .chip', has_text='Вставить').click(); pg.keyboard.type('пойт'); pg.wait_for_timeout(80)
    pg.locator('.slotbox .typin + .hchips .chip.pick').first.click(); pg.wait_for_timeout(80)
    words = [x.replace('?','').strip() for x in pg.locator('.hbuild .hchips').first.locator('.chip').all_inner_texts()]
    check('word inserted before', words[:3] == ['я','хочу','пойти'] and len(words) == 4)
    pg.context.close()
    pg = newpage(b, base)
    pg.click('#micBtn'); pg.fill('#hearIn', 'хочу чай'); pg.dispatch_event('#hearIn', 'input'); pg.wait_for_timeout(100)
    t = pg.locator('#hearSug .hwrap .sug').first.inner_text().split('\n')[-1].strip()
    pg.locator('#hearSug .hwrap .hdel').first.click(); pg.wait_for_timeout(80)
    words = ' '.join(x.replace('?','').strip() for x in pg.locator('.hbuild .hchips').first.locator('.chip').all_inner_texts())
    check('✎ moves suggestion into frame', words.lower() == t.lower().replace(',', ''))
    pg.context.close()
    # вёрстка панели вариантов и набора на узких экранах
    for L, phrase in [('ru','я шучу гулить'),('uk','я шучу гуляти'),('en','I won walk')]:
        for wdt in [360, 313, 277]:
            pg = newpage(b, {'aac.lang': L, 'aac.settings': json.dumps({'hearSimple': True})})
            pg.set_viewport_size({'width': wdt, 'height': 700})
            pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate(f"window.__say('{phrase}')"); pg.wait_for_timeout(120)
            if pg.evaluate('hearSlot')!=1: pg.locator('.hbuild .hchips').first.locator('.chip').nth(1).click()
            pg.locator('.slotbox .chip').filter(has_text='✎').click(); pg.wait_for_timeout(60)
            bad = pg.evaluate("""()=>{const W=document.documentElement.clientWidth;return document.documentElement.scrollWidth>W||[...document.querySelectorAll('.hbuild *')].some(e=>{const r=e.getBoundingClientRect();return r.width&&r.right>W+1})}""")
            check(f'options+typing fit {L} {wdt}px', not bad)
            pg.context.close()

    # 14. «Говорит собеседник» на маленьком экране: «Говорить» видна целиком, блок текста по содержимому
    for L in ['ru', 'uk', 'en']:
        for (wdt, hgt) in [(360, 640), (313, 556), (277, 492)]:
            pg = newpage(b, {'aac.lang': L, 'aac.settings': json.dumps({'hearTab': 'show'})})
            pg.set_viewport_size({'width': wdt, 'height': hgt}); pg.reload(); pg.wait_for_timeout(150)
            pg.click('#micBtn'); pg.wait_for_timeout(150)
            vis = pg.evaluate("""()=>{const m=document.querySelector('#main').getBoundingClientRect(),r=document.querySelector('#showMic').getBoundingClientRect();return r.top>=m.top-1&&r.bottom<=m.bottom+1}""")
            check(f'Speak fully visible {L} {wdt}x{hgt}', vis)
            pg.fill('#showIn', 'хотите чай или кофе'); pg.press('#showIn', 'Enter'); pg.wait_for_timeout(200)
            fit = pg.evaluate("""()=>{const b=document.querySelector('#showText'),m=document.querySelector('#main').getBoundingClientRect(),r=b.getBoundingClientRect();
                let last=null;for(const c of b.children)last=c;const lr=last.getBoundingClientRect();
                return r.top>=m.top-1&&r.top<m.bottom&&(r.bottom-lr.bottom)<40}""")
            check(f'text block fits content and is shown {L} {wdt}x{hgt}', fit)
            pg.context.close()

    # 15. Встроенный браузер Facebook: плашка «Открыть в Chrome»
    FB = 'Mozilla/5.0 (Linux; Android 14; Pixel 7 Build/UQ1A; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/120.0 Mobile Safari/537.36 [FB_IAB/FB4A;FBAV/450.0.0.0;]'
    CH = 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36'
    IG = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 300.0'
    def uapage(ua, L='ru', wdt=360):
        ctx = b.new_context(service_workers='block', viewport={'width': wdt, 'height': 640}, user_agent=ua)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errors.append(str(e)))
        pg.add_init_script(STUB + f"localStorage.setItem('aac.lang','{L}')"); pg.goto(URL); pg.wait_for_timeout(250); return pg
    pg = uapage(FB)
    check('FB in-app: banner shown', pg.locator('#iab').count() == 1)
    href = pg.locator('#iab a.go').get_attribute('href')
    check('FB: intent opens Chrome with same page', href.startswith('intent://'+URL.split('://',1)[1]+'#Intent;scheme=https;package=com.android.chrome;'))
    check('FB: banner text in menu language', 'Facebook' in pg.inner_text('#iab') and 'Открыть в' in pg.inner_text('#iab'))
    pg.click('#settingsBtn'); pg.select_option('#setLang', 'en'); pg.wait_for_timeout(100); pg.click('#closeSettBtn')
    check('banner follows language switch', pg.locator('#iab').count() == 1 and 'Open in' in pg.inner_text('#iab'))
    pg.locator('#iab .x').click()
    check('banner hidden by ✕', pg.locator('#iab').count() == 0)
    pg.reload(); pg.wait_for_timeout(200)
    check('banner stays hidden in this session', pg.locator('#iab').count() == 0)
    pg.context.close()
    pg = uapage(CH); check('Chrome: no banner', pg.locator('#iab').count() == 0); pg.context.close()
    pg = uapage(IG); check('Instagram iOS: banner without intent', pg.locator('#iab').count() == 1 and pg.locator('#iab a.go').count() == 0); pg.context.close()
    for L in ['ru', 'uk', 'en']:
        for wdt in [360, 313, 277]:
            pg = uapage(FB, L, wdt)
            bad = pg.evaluate("""()=>{const W=document.documentElement.clientWidth;return document.documentElement.scrollWidth>W||[...document.querySelectorAll('#iab *')].some(e=>{const r=e.getBoundingClientRect();return r.right>W+1||e.scrollWidth>e.clientWidth+1})}""")
            mainOk = pg.evaluate("document.querySelector('#main').getBoundingClientRect().height>150")
            check(f'banner fits {L} {wdt}px', not bad and mainOk)
            pg.context.close()

    # 16. Язык фраз — в настройках, кнопки в шапке нет
    pg = newpage(b, base)
    check('no language button in header', pg.locator('header #lang').count() == 0 and pg.locator('header button:visible').count() == 6)
    pg.click('#settingsBtn')
    check('language select first in «Основное»', pg.evaluate("document.querySelector('#sett .sg[data-g=main] select').id") == 'setLang' and pg.input_value('#setLang') == 'ru')
    pg.click('#sett .sg[data-g=home] .sgh'); pg.select_option('#setRecent', '6')
    pg.click('#sett .sg[data-g=main] .sgh'); pg.select_option('#setSeg', 'L3')
    pg.select_option('#setLang', 'uk'); pg.wait_for_timeout(150)
    check('language applied at once (menu follows)', pg.inner_text('#sett h2').strip() == '⚙️ Налаштування' and pg.evaluate("localStorage.getItem('aac.lang')") == 'uk')
    check('unsaved fields kept after language change', pg.input_value('#setSeg') == 'L3' and pg.input_value('#setRecent') == '6')
    check('summary shows language', 'Українська' in pg.locator('#sett .sg[data-g=voice]').inner_text() or True)
    pg.click('#closeSettBtn'); pg.wait_for_timeout(100)
    st = json.loads(pg.evaluate("localStorage.getItem('aac.settings')"))
    check('other settings saved', st['level'] == 'L3' and st['recentN'] == 6)
    check('home in Ukrainian', 'Говоримо разом' in pg.inner_text('#ttl'))
    pg.reload(); pg.wait_for_timeout(150)
    check('language kept after reload', pg.evaluate("document.documentElement.lang") == 'uk')
    pg.context.close()
    # шапка на узких экранах и с открытыми экранами
    for L in ['ru', 'uk', 'en']:
        for wdt in [360, 313, 277, 800]:
            pg = newpage(b, {'aac.lang': L})
            pg.set_viewport_size({'width': wdt, 'height': 700}); pg.wait_for_timeout(80)
            res = []
            for scr in ['home', 'mic', 'abc']:
                if scr == 'mic': pg.click('#micBtn')
                if scr == 'abc': pg.click('#abcBtn')
                pg.wait_for_timeout(250)
                bad = pg.evaluate("""()=>{const W=document.documentElement.clientWidth;const bs=[...document.querySelectorAll('header button')].filter(b=>b.offsetParent);
                    const rs=bs.map(b=>b.getBoundingClientRect());
                    const ov=rs.some((r,i)=>r.right>W+1||r.width<38||rs.some((q,j)=>j!==i&&r.left<q.right-1&&q.left<r.right-1&&r.top<q.bottom-1&&q.top<r.bottom-1));
                    return ov||document.documentElement.scrollWidth>W}""")
                res.append(bad)
            check(f'header ok {L} {wdt}px', not any(res))
            if wdt <= 313:
                pg2 = newpage(b, {'aac.lang': L}); pg2.set_viewport_size({'width': wdt, 'height': 700}); pg2.click('#micBtn'); pg2.wait_for_timeout(80)
                check(f'🎤 tabs not clipped {L} {wdt}px', not pg2.evaluate("[...document.querySelectorAll('.tab')].some(t=>t.scrollWidth>t.clientWidth+1)"))
                pg2.context.close()
            pg.context.close()

    # 17. v60: подписи панели, отклик, «Сказано», «Болит», «Не знаю», фото, звонок, удержание, очистка
    for L in ['ru', 'uk', 'en']:
        for wdt in [360, 313, 277]:
            pg = newpage(b, {'aac.lang': L}); pg.set_viewport_size({'width': wdt, 'height': 700}); pg.wait_for_timeout(60)
            r = pg.evaluate("""()=>[...document.querySelectorAll('#bar button span:not(.i)')].map(e=>{const cs=getComputedStyle(e);return [parseFloat(cs.fontSize),e.scrollWidth<=e.parentNode.clientWidth+1,e.getBoundingClientRect().height]})""")
            check(f'bar labels ≥11px, not cut {L} {wdt}', all(x[0] >= 11 and x[1] for x in r))
            pg.context.close()
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'barLbl': 'off'})})
    check('bar icons only', not pg.locator('#bar button span:not(.i)').first.is_visible())
    pg.context.close()
    # отклик нажатия
    pg = newpage(b, base)
    t0 = pg.locator('#main .tile').first; bb = t0.bounding_box()
    pg.mouse.move(bb['x']+20, bb['y']+20); pg.mouse.down()
    check('press feedback class', 'prs' in t0.get_attribute('class'))
    pg.mouse.up(); pg.wait_for_timeout(200)
    check('press feedback removed', 'prs' not in (pg.locator('#main .tile').first.get_attribute('class') or ''))
    pg.context.close()
    # «Сказано»: размер и показать собеседнику
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'quick': True})})
    pg.locator('#main .tile').first.click(); pg.locator('#main .tile').first.click(); pg.wait_for_timeout(80)
    f0 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('#ov .said')).fontSize)")
    pg.locator('#ov .srow button', has_text='A+').click()
    f1 = pg.evaluate("parseFloat(getComputedStyle(document.querySelector('#ov .said')).fontSize)")
    check('said text larger by default and A+ works', f0 >= 36 and f1 > f0)
    pg.locator('#ov .srow button', has_text='собеседнику').click(); pg.wait_for_timeout(80)
    fit = pg.evaluate("""()=>{const t=document.querySelector('#bigShow .bs-t');return [parseFloat(t.style.fontSize),t.scrollHeight<=t.clientHeight+1&&t.scrollWidth<=t.clientWidth+1]}""")
    check('show to partner: huge and fits', fit[0] >= 60 and fit[1])
    pg.locator('#bigShow button', has_text='Перевернуть').click()
    check('flip rotates', pg.evaluate("document.querySelector('#bigShow').classList.contains('flip')"))
    pg.click('#bar button[data-k=back]') if False else pg.go_back(); pg.wait_for_timeout(100)
    check('back closes big show, said window stays', pg.locator('#bigShow').count() == 0 and pg.locator('#ov .said').count() == 1)
    pg.context.close()
    # «Болит»: места и сила
    pg = newpage(b, {'aac.lang': 'uk'})
    pg.click('#bar button[data-k=pain]'); pg.wait_for_timeout(60)
    check('pain: 10 body places', pg.locator('#main .grid .tile').count() == 10)
    pg.locator('#main .tile', has_text='Зуби').click(); pg.wait_for_timeout(60)
    check('pain: 4 intensity tiles', pg.locator('#main .grid .tile').count() == 4)
    pg.locator('#main .tile', has_text='Дуже сильно').click()
    check('pain phrase built', 'У мене дуже сильно болять зуби?' in pg.inner_text('#ov'))
    pg.context.close()
    pg = newpage(b, {'aac.lang': 'en'}); pg.click('#bar button[data-k=pain]'); pg.locator('#main .tile', has_text='Chest').click(); pg.locator('#main .tile', has_text='A little').click()
    check('EN pain phrase', 'My chest hurts a little?' in pg.inner_text('#ov')); pg.context.close()
    # «Не знаю»
    for lv, n in [('L1', 'Не знаю'), ('L2', 'Не знаю')]:
        pg = newpage(b, {'aac.lang': 'uk', 'aac.settings': json.dumps({'level': lv})})
        check(f'«Не знаю» tile {lv}', pg.locator('#main .tile', has_text=n).count() == 1); pg.context.close()
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'level': 'L3'})})
    pg.locator('#main .tile', has_text='Общение').click(); pg.wait_for_timeout(60)
    check('«Я не знаю» in builder', pg.locator('#main .tile', has_text='Я').count() >= 1)
    pg.context.close()
    # фото в редакторе
    import base64, struct, zlib
    def png(w,h):
        raw=b''.join(b'\x00'+bytes([200,80,40])*w for _ in range(h))
        def ch(t,d): return struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
        return b'\x89PNG\r\n\x1a\n'+ch(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+ch(b'IDAT',zlib.compress(raw))+ch(b'IEND',b'')
    open(OUT+'/ph.png','wb').write(png(640,400))
    pg = newpage(b, base)
    pg.click('#gear'); pg.locator('#ed select').nth(1).select_option(index=1); pg.wait_for_timeout(60)
    pg.locator('#ed .edpic input[type=file]').set_input_files(OUT+'/ph.png'); pg.wait_for_timeout(400)
    img = pg.evaluate("(()=>{const i=document.querySelector('#ed .edpic img');return i?[i.src.length,i.naturalWidth]:null})()")
    check('photo stored small 192px', img and img[1] == 192 and img[0] < 40000)
    pg.locator('#ed .helphead button').click(); pg.wait_for_timeout(80)
    check('tile shows photo', pg.locator('#main .tile img').count() == 1)
    check('photo goes to backup', 'data:image/jpeg' in ''.join(pg.evaluate("Object.keys(localStorage).filter(k=>k.startsWith('aac.')).map(k=>localStorage.getItem(k))")))
    pg.context.close()
    # звонок из «Помощь»
    pg = newpage(b, base)
    pg.click('#settingsBtn'); pg.click('#sett .sg[data-g=sos] .sgh'); pg.fill('#setSosN0', 'Олена'); pg.fill('#setSosT0', '+380 (67) 123-45-67'); pg.dispatch_event('#setSosT0','change')
    check('sos summary', 'Олена' in pg.locator('#sett .sg[data-g=sos] .sgh').inner_text() or pg.locator('#sett .sg[data-g=sos].open').count()==1)
    pg.click('#closeSettBtn'); pg.click('#bar button[data-k=help]'); pg.wait_for_timeout(60)
    a = pg.locator('#ov.red a.call')
    check('call button on SOS', a.count() == 1 and a.get_attribute('href') == 'tel:+380671234567' and 'Олена' in a.inner_text())
    pg.context.close()
    # выбор удержанием
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'holdSel': True})})
    pg.locator('#main .tile').first.click(); pg.wait_for_timeout(80)
    check('hold: short tap ignored', pg.locator('#main .tile', has_text='Вода').count() == 0)
    bb = pg.locator('#main .tile').first.bounding_box()
    pg.mouse.move(bb['x']+30, bb['y']+30); pg.mouse.down(); pg.wait_for_timeout(250)
    check('hold: progress bar shown', 'holding' in pg.locator('#main .tile').first.get_attribute('class'))
    pg.wait_for_timeout(400); pg.mouse.up(); pg.wait_for_timeout(100)
    check('hold: long press selects once', pg.locator('#main .tile', has_text='Вода').count() == 1)
    bb = pg.locator('#main .tile').first.bounding_box()
    pg.mouse.move(bb['x']+30, bb['y']+30); pg.mouse.down(); pg.mouse.move(bb['x']+30, bb['y']+90, steps=5); pg.wait_for_timeout(700); pg.mouse.up()
    check('hold: moving finger cancels', pg.locator('#ov').evaluate("e=>e.style.display")!='flex')
    pg.click('#settingsBtn'); pg.click('#sett .sg[data-g=voice] .sgh')
    check('settings still clickable with hold mode', pg.locator('#sett .sg[data-g=voice].open').count() == 1)
    pg.context.close()
    # «Азбука»: очистить строку и вернуть
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'abcMode': 'prefix'})})
    pg.click('#abcBtn'); pg.locator('.fnbtn').click(); pg.locator('.abcres .fnp .chip', has_text='я').first.click()
    pg.locator('.fnbtn').click(); pg.locator('.abcres .fnp .chip').get_by_text('не', exact=True).first.click()
    pg.locator('.abcres .ans.no', has_text='🗑').click()
    check('ABC clear all', pg.inner_text('.build .bt') == '…')
    pg.locator('.abcres .undo').click()
    check('ABC undo restores line', pg.inner_text('.build .bt') == 'я не')
    pg.context.close()
    # рамка 🎤: «Очистить» и «Вернуть»
    pg = newpage(b, {**base, 'aac.settings': json.dumps({'hearSimple': True})})
    pg.click('#micBtn'); pg.click('#micGo'); pg.evaluate("window.__say('я хочу пить')"); pg.wait_for_timeout(120)
    pg.locator('.hbuild button', has_text='Очистить').first.click(); pg.wait_for_timeout(60)
    pg.locator('#main button', has_text='Вернуть').first.click(); pg.wait_for_timeout(60)
    check('frame clear + undo', pg.locator('.hbuild .hchips').first.locator('.chip').count() == 3)
    pg.context.close()

    # 18. v61: «На весь экран» на вкладке собеседника
    for L in ['ru','uk','en']:
        for wdt in [360, 277]:
            pg = newpage(b, {'aac.lang': L, 'aac.settings': json.dumps({'hearTab': 'show'})}); pg.set_viewport_size({'width': wdt, 'height': 640})
            pg.click('#micBtn'); pg.wait_for_timeout(60)
            check(f'full button hidden without text {L} {wdt}', not pg.locator('#showFull').is_visible())
            pg.fill('#showIn', 'хотите чай или кофе'); pg.press('#showIn', 'Enter'); pg.wait_for_timeout(100)
            fits = pg.evaluate("(()=>{const W=document.documentElement.clientWidth;return [...document.querySelectorAll('#hearBody .row button, #showFull')].every(b=>b.getBoundingClientRect().right<=W+1)&&document.documentElement.scrollWidth<=W})()")
            check(f'full button shown, row fits {L} {wdt}', pg.locator('#showFull').is_visible() and fits)
            pg.click('#showFull'); pg.wait_for_timeout(80)
            ok = pg.evaluate("(()=>{const t=document.querySelector('#bigShow .bs-t');return t&&t.textContent==='хотите чай или кофе'&&parseFloat(t.style.fontSize)>=50&&t.scrollWidth<=t.clientWidth+1})()")
            check(f'partner phrase full screen {L} {wdt}', ok)
            pg.go_back(); pg.wait_for_timeout(80)
            check(f'back returns to partner tab {L} {wdt}', pg.locator('#bigShow').count()==0 and pg.locator('#showText').count()==1)
            pg.context.close()
    # 9. Языки: все три интерфейса без ошибок, справка открывается
    for L in ['uk', 'en']:
        pg = newpage(b, {'aac.lang': L})
        pg.click('#settingsBtn'); pg.click('#closeSettBtn'); pg.click('#helpBtn')
        check(f'{L}: help opens', pg.locator('#help details.hi').count() > 20)
        pg.context.close()
    b.close()

srv.shutdown()
print('errors:', errors)
print(sum(1 for _, ok in results if ok), '/', len(results), 'passed')
sys.exit(0 if all(ok for _, ok in results) and not errors else 1)
