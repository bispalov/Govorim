# v64: ✉️ сообщение близкому (WhatsApp / SMS / меню «Поделиться») из окна «Сказано» и с экрана «Помощь»
import json, os, shutil, threading, http.server, functools
from urllib.parse import unquote
from playwright.sync_api import sync_playwright

import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
STUB = r"""
try{if(!localStorage.getItem('aac.tour.seen'))localStorage.setItem('aac.tour.seen',JSON.stringify({home:1,tiles:1,hear:1,show:1,abc:1}))}catch(e){}
window.__spoken=[];window.__opened=[];window.__shared=[];
const ss={cancel(){},speak(u){window.__spoken.push(u.text);setTimeout(()=>u.onend&&u.onend(),5)},getVoices(){return []},onvoiceschanged:null};
Object.defineProperty(window,'speechSynthesis',{value:ss,configurable:true});
window.SpeechSynthesisUtterance=function(t){this.text=t};
window.open=(u)=>{window.__opened.push(u);return null};
Object.defineProperty(navigator,'share',{value:(d)=>{window.__shared.push(d);return Promise.resolve()},configurable:true});
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
sends = lambda pg: pg.locator('#ov .send')

with sync_playwright() as p:
    b = p.chromium.launch()
    # 1. По умолчанию выключено
    pg = page(b, {'aac.lang': 'ru', 'aac.settings': json.dumps({'sos': [{'n': 'Саша', 't': '+380671234567'}, {'n': '', 't': ''}]})})
    check('default msg off', pg.evaluate('settings.msg') == 'off')
    pg.evaluate("say('Я хочу пить')"); pg.wait_for_timeout(50)
    check('off: no send button in «Сказано»', sends(pg).count() == 0)
    pg.click('#bar button[data-k=help]'); pg.wait_for_timeout(50)
    check('off: no send button on Help', sends(pg).count() == 0)
    pg.locator('#ov .ans').last.click()
    # 2. Настройка через ⚙️
    pg.click('#settingsBtn'); pg.click('#sett .sg[data-g=sos] .sgh')
    check('group renamed', 'Близкие: звонок и сообщение' in pg.inner_text('#sett .sg[data-g=sos] .sgh'))
    opts = pg.evaluate("[...document.querySelectorAll('#setMsg option')].map(o=>o.value)")
    check('options off/wa/sms/share', opts == ['off', 'wa', 'sms', 'share'])
    pg.fill('#setSosN1', 'Мама'); pg.fill('#setSosT1', '067 765 43 21')
    pg.select_option('#setMsg', 'wa'); pg.wait_for_timeout(50)
    note = pg.inner_text('#msgNote')
    check('note explains WhatsApp + warns about local number', 'WhatsApp' in note and 'кода страны' in note and '⚠️' in note)
    pg.fill('#setSosT1', '+380677654321'); pg.wait_for_timeout(50)
    check('warning gone after country code', '⚠️' not in pg.inner_text('#msgNote'))
    pg.fill('#setSosT1', '0677654321')
    pg.dispatch_event('#sett .sg[data-g=main] .sgh', 'click'); pg.wait_for_timeout(50)
    check('summary shows WhatsApp', 'WhatsApp' in pg.inner_text('#sett .sg[data-g=sos] .sgs'))
    pg.click('#closeSettBtn')
    check('saved', pg.evaluate('settings.msg') == 'wa')
    # 3. Плитка → «Сказано» → кнопка WhatsApp
    pg.evaluate("settings.quick=true"); pg.locator('#main .tile').first.click(); pg.wait_for_timeout(100)
    if pg.locator('#ov .said').count() == 0:
        t = pg.locator('#main .tile');
        while pg.locator('#ov .said').count() == 0 and t.count():
            t.first.click(); pg.wait_for_timeout(80)
            if pg.locator('#ov .ans.yes').count() and pg.locator('#ov .said').count() == 0: pg.locator('#ov .ans.yes').first.click(); pg.wait_for_timeout(80)
    said = pg.inner_text('#ov .said')
    check('tile phrase reaches «Сказано»', len(said) > 1)
    check('one WhatsApp button (local number skipped)', sends(pg).count() == 1 and 'WhatsApp: Саша' in sends(pg).first.inner_text())
    sends(pg).first.click(); pg.wait_for_timeout(50)
    op = pg.evaluate('window.__opened')
    check('opens wa.me with number and text', len(op) == 1 and op[0].startswith('https://wa.me/380671234567?text=') and unquote(op[0].split('text=')[1]) == said)
    check('diary records the message', any('✉️' in x['s'] and said in x['s'] for x in pg.evaluate("JSON.parse(localStorage.getItem('aac.log'))")))
    check('«Сказано» stays open after sending', pg.locator('#ov .said').count() == 1)
    pg.locator('#ov .ans.yes').last.click()
    # 4. 🎤 рамка → «Сказать»
    pg.evaluate("say('Приезжай скорее',false,{recent:1,e:'💬'})"); pg.wait_for_timeout(50)
    sends(pg).first.click()
    check('frame phrase text sent', unquote(pg.evaluate('window.__opened')[-1]).endswith('text=Приезжай скорее'))
    pg.locator('#ov .ans.yes').last.click()
    # 5. «Помощь»
    pg.click('#bar button[data-k=help]'); pg.wait_for_timeout(50)
    check('Help: WhatsApp button', sends(pg).count() == 1)
    check('Help: alarm running', pg.evaluate('tmr!==null'))
    sends(pg).first.click(); pg.wait_for_timeout(50)
    check('Help: sends help phrase', unquote(pg.evaluate('window.__opened')[-1].split('text=')[1]) == 'Помогите! Мне нужна помощь!')
    check('Help: alarm quiet after sending', pg.evaluate('tmr===null'))
    check('Help: red screen stays', pg.evaluate("document.querySelector('#ov').className") == 'red')
    pg.locator('#ov .ans').last.click()
    # 6. SMS и «Поделиться»
    pg.evaluate("settings.msg='sms'"); pg.evaluate("say('Тест')")
    check('SMS: both contacts (local number ok)', sends(pg).count() == 2 and 'SMS: Мама' in sends(pg).nth(1).inner_text())
    pg.locator('#ov .ans.yes').last.click()
    pg.evaluate("settings.msg='share'"); pg.evaluate("say('Позвони мне')")
    check('Share: one «Отправить…» button', sends(pg).count() == 1 and 'Отправить' in sends(pg).first.inner_text())
    sends(pg).first.click(); pg.wait_for_timeout(50)
    check('Share: navigator.share with text', pg.evaluate('window.__shared') == [{'text': 'Позвони мне'}])
    pg.locator('#ov .ans.yes').last.click()
    # 7. Нет номеров — нет кнопок
    pg.evaluate("settings.msg='wa';settings.sos=[{n:'',t:''},{n:'',t:''}]"); pg.evaluate("say('Тест')")
    check('no numbers → no WhatsApp button', sends(pg).count() == 0)
    check('no script errors', not errors)
    pg.context.close()
    # 8. Вёрстка на узком экране, две кнопки, uk/en
    for L, word, hw in [('uk', 'WhatsApp: Мама', 'Допоможіть'), ('en', 'WhatsApp: Mum', 'Help!')]:
        for W, H in [(277, 492), (360, 640)]:
            pg = page(b, {'aac.lang': L, 'aac.settings': json.dumps({'msg': 'wa', 'sos': [{'n': 'Олександр Петрович', 't': '+380671234567'}, {'n': 'Мама' if L == 'uk' else 'Mum', 't': '+380677654321'}]})}, W, H)
            pg.evaluate("say('Я хочу додому, забери мене сьогодні ввечері')"); pg.wait_for_timeout(80)
            check(f'{L} {W}: two buttons', sends(pg).count() == 2 and word in sends(pg).nth(1).inner_text())
            ok = pg.evaluate("(()=>{const o=document.querySelector('#ov');return o.scrollWidth<=o.clientWidth&&[...o.querySelectorAll('.send,.ans')].every(e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+0.5})})()")
            check(f'{L} {W}: nothing sticks out', ok)
            # кнопка «Готово» достижима прокруткой
            pg.locator('#ov .ans.yes').last.scroll_into_view_if_needed()
            check(f'{L} {W}: «Done» reachable', pg.locator('#ov .ans.yes').last.is_visible())
            pg.evaluate("document.querySelector('#ov').scrollTop=0")
            pg.screenshot(path=f'{OUT}/msg_{L}_{W}.png')
            pg.locator('#ov .ans.yes').last.click()
            pg.click('#bar button[data-k=help]'); pg.wait_for_timeout(50)
            pg.screenshot(path=f'{OUT}/msg_sos_{L}_{W}.png')
            check(f'{L} {W}: Help buttons fit', pg.evaluate("document.querySelector('#ov').scrollWidth<=document.querySelector('#ov').clientWidth") and sends(pg).count() == 2)
            pg.locator('#ov .ans').last.click()
            pg.click('#helpBtn')
            check(f'{L} {W}: help item', '✉️' in pg.text_content('#help') and 'WhatsApp' in pg.text_content('#help'))
            pg.context.close()
    b.close()
print('errors:', errors)
print(sum(r for _, r in results), '/', len(results), 'passed')
