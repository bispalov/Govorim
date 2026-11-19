# v72: заголовки групп с первого касания, черновик после перезагрузки, автосохранение настроек
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
def mclick(pg,sel):
    pg.locator(sel).first.evaluate("e=>e.scrollIntoView({block:'center'})");pg.wait_for_timeout(50)
    bx=pg.locator(sel).first.bounding_box();pg.mouse.click(bx['x']+bx['width']/2,bx['y']+bx['height']/2)
openg=lambda pg:pg.evaluate("settOpen")
stored=lambda pg:json.loads(pg.evaluate("localStorage.getItem('aac.settings')") or '{}')
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,H in [(360,640),(277,492)]:
        # ---- 1 + 3: правка поля → сразу заголовок другой группы одним касанием; значение уже сохранено ----
        pg=page(b,{'aac.lang':'uk','aac.tour.seen':allseen},W,H)
        pg.click('#settingsBtn');mclick(pg,'#sett .sg[data-g=sos] .sgh')
        check(f'{W}: sos group open',openg(pg)=='sos')
        pg.locator('#setSosT0').fill('+380671234567');pg.locator('#setSosN0').fill('Саша')          # фокус остаётся в поле
        mclick(pg,'#sett .sg[data-g=voice] .sgh');pg.wait_for_timeout(150)
        check(f'{W}: other group opens with ONE click after editing a field',openg(pg)=='voice')
        check(f'{W}: name saved without closing',stored(pg).get('sos',[{}])[0].get('n')=='Саша' and pg.evaluate("settModal.style.display")=='block')
        check(f'{W}: collapsed summary updated',('Саша' in pg.inner_text('#sett .sg[data-g=sos] .sgs')))
        # флажок, список, уровень, язык — без закрытия, прокрутка на месте
        mclick(pg,'#sett .sg[data-g=home] .sgh');pg.wait_for_timeout(100)
        pg.evaluate("settModal.scrollTop=Math.min(120,settModal.scrollHeight)");y0=pg.evaluate("settModal.scrollTop")
        pg.locator('#setResume').check();pg.wait_for_timeout(120)
        check(f'{W}: checkbox saved at once',stored(pg).get('resume') is True)
        check(f'{W}: window open, group open, scroll kept',pg.evaluate("settModal.style.display")=='block' and openg(pg)=='home' and abs(pg.evaluate("settModal.scrollTop")-y0)<=2)
        pg.locator('#setSize').select_option(index=0);pg.wait_for_timeout(120)
        check(f'{W}: select saved at once',stored(pg).get('size')==pg.evaluate("$('#setSize').value"))
        mclick(pg,'#sett .sg[data-g=main] .sgh');pg.wait_for_timeout(100);print('   open after main click:',openg(pg))
        pg.locator('#setSeg').select_option('L3');pg.wait_for_timeout(150)
        check(f'{W}: level saved at once, window stays',stored(pg).get('level')=='L3' and pg.evaluate("settModal.style.display")=='block')
        pg.locator('#setLang').select_option('ru');pg.wait_for_timeout(200)
        check(f'{W}: phrase language switched, window stays',pg.evaluate("lang")=='ru' and pg.evaluate("localStorage.getItem('aac.lang')")=='ru' and pg.evaluate("settModal.style.display")=='block')
        check(f'{W}: earlier values not lost after language switch',stored(pg).get('resume') is True and stored(pg).get('sos')[0]['n']=='Саша')
        # текстовое поле — при уходе из приложения
        mclick(pg,'#sett .sg[data-g=sos] .sgh');pg.locator('#setSosN1').fill('Мама')
        pg.evaluate("Object.defineProperty(document,'hidden',{get:()=>true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));Object.defineProperty(document,'hidden',{get:()=>false,configurable:true})")
        check(f'{W}: text field saved when app hidden',stored(pg)['sos'][1]['n']=='Мама')
        # выбор файла копии не сохраняет
        c0=pg.evaluate("localStorage.getItem('aac.settings')")
        pg.evaluate("$('#setSosN0').value='Не зберігати';$('#restoreFile').dispatchEvent(new Event('change',{bubbles:true}))");pg.wait_for_timeout(100)
        check(f'{W}: file input change does not save',pg.evaluate("localStorage.getItem('aac.settings')")==c0)
        pg.evaluate("$('#setSosN0').value='Саша'")
        # ключ API: пустое поле при автосохранении удаляет ключ, как раньше при «Закрыть»
        pg.evaluate("localStorage.setItem('aac.secret.ext',JSON.stringify({key:'abc'}))")
        mclick(pg,'#sett .sg[data-g=net] .sgh')
        if pg.locator('#setExtKey').is_visible():
            pg.locator('#setExtKey').fill('xyz');pg.locator('#setExtKey').dispatch_event('change');pg.wait_for_timeout(100)
            check(f'{W}: API key saved by autosave',json.loads(pg.evaluate("localStorage.getItem('aac.secret.ext')"))['key']=='xyz')
        # «Закрыть» и «Назад»
        pg.click('#closeSettBtn');check(f'{W}: Close closes',pg.evaluate("settModal.style.display")=='none')
        pg.click('#settingsBtn');pg.evaluate("appBack()");check(f'{W}: Back closes',pg.evaluate("settModal.style.display")=='none')
        pg.context.close()

    # ---- 2: черновик ----
    pg=page(b,{'aac.lang':'uk','aac.tour.seen':allseen,'aac.settings':json.dumps({'level':'L3'})},360,640)
    pg.click('#abcBtn');pg.evaluate("abcAdd('мені');abcAdd('потрібно');render()")
    pg.evaluate("hearBuild=['я','хочу','пити'];hearOpen=true")
    pg.wait_for_timeout(1300)
    pg.reload();pg.wait_for_timeout(400)
    check('draft: ABC line back after reload',pg.evaluate("abcLine.join(' ')")=='мені потрібно')
    check('draft: 🎤 frame back after reload',pg.evaluate("hearBuild.join(' ')")=='я хочу пити')
    pg.click('#abcBtn');pg.wait_for_timeout(80)
    check('draft: shown in ABC',('мені потрібно' in pg.inner_text('#main')))
    pg.click('#micBtn');pg.locator('.tabs .tab').nth(1 if pg.evaluate("hearTab")=='show' else 0).click();pg.evaluate("hearTab='sug';render()");pg.wait_for_timeout(80)
    check('draft: shown in 🎤 frame',pg.locator('.hbuild').count()>0 and 'пити' in pg.inner_text('.hbuild'))
    # разные языки
    pg.evaluate("setLang('ru')");pg.wait_for_timeout(100)
    check('draft: other language starts empty',pg.evaluate("abcLine.length+hearBuild.length")==0)
    pg.evaluate("abcLine.push('привет');hearBuild=['мне','плохо']");pg.evaluate("setLang('uk')");pg.wait_for_timeout(100)
    check('draft: uk draft back after switching',pg.evaluate("abcLine.join(' ')")=='мені потрібно' and pg.evaluate("hearBuild.join(' ')")=='я хочу пити')
    check('draft: ru draft kept separately',json.loads(pg.evaluate("localStorage.getItem('aac.draft.ru')"))=={'abc':['привет'],'hear':['мне','плохо']})
    # после прозвучавшей фразы — пусто
    pg.click('#abcBtn');pg.wait_for_timeout(80)
    pg.locator('.abcres .abcsay').first.click();pg.wait_for_timeout(200);pg.evaluate("closeOv()")
    pg.evaluate("hearDone()");pg.wait_for_timeout(100)
    check('draft: key removed after phrase spoken and frame done',pg.evaluate("localStorage.getItem('aac.draft.uk')") is None)
    pg.reload();pg.wait_for_timeout(300)
    check('draft: empty after reload',pg.evaluate("abcLine.length+hearBuild.length")==0)
    # не в резервной копии
    keys=pg.evaluate("(()=>{const d={};for(let i=0;i<localStorage.length;i++){const k=localStorage.key(i);if(k&&k.startsWith('aac.')&&!k.startsWith('aac.secret.')&&!k.startsWith('aac.lex.')&&!k.startsWith('aac.draft.'))d[k]=1}return d})()")
    check('draft: excluded from backup filter',pg.evaluate("String(backupSave||'')").count('aac.draft.')>0 if pg.evaluate("typeof backupSave")=='function' else 'aac.draft.' in SRC)
    # повреждённый черновик
    pg.evaluate("localStorage.setItem('aac.draft.uk','{oops')");pg.reload();pg.wait_for_timeout(300)
    check('draft: broken record does not break start',pg.evaluate("abcLine.length+hearBuild.length")==0 and pg.locator('#main .tile').count()>0)
    pg.evaluate("localStorage.setItem('aac.draft.uk',JSON.stringify({abc:'x',hear:[1,'так']}))");pg.reload();pg.wait_for_timeout(300)
    check('draft: wrong types filtered',pg.evaluate("abcLine.length")==0 and pg.evaluate("hearBuild.join()")=='так')
    # вместе с «запуском с последнего экрана»
    pg.evaluate("localStorage.setItem('aac.draft.uk',JSON.stringify({abc:['добрий','день'],hear:[]}));settings.resume=true;saveSettings();abcOpen()");pg.wait_for_timeout(200)
    pg.reload();pg.wait_for_timeout(400)
    check('draft + resume: opens ABC with the line',pg.evaluate("!!abc&&abc.line.join(' ')")=='добрий день')
    check('no script errors',not errors)
    b.close()
print('errors:',errors)
print(sum(r for _,r in results),'/',len(results),'passed')
