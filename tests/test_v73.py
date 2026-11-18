# v73: размер плиток — колонки, шрифт от ширины плитки, «Маленький»
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
EXP={'s':{277:3,313:3,360:4,412:4},'m':{277:2,313:2,360:2,412:2},'l':{277:2,313:2,360:2,412:2},'xl':{277:1,313:1,360:1,412:1}}
COLS="(()=>{const g=[...document.querySelectorAll('#main .tg')].at(-1);return getComputedStyle(g).gridTemplateColumns.split(' ').length})()"
FIT="(()=>{const ts=[...document.querySelectorAll('#main .tg .tile')];return ts.every(t=>t.scrollWidth<=t.clientWidth+1&&[...t.children].every(c=>c.getBoundingClientRect().right<=t.getBoundingClientRect().right+1))&&document.querySelector('#main').scrollWidth<=document.querySelector('#main').clientWidth+1})()"
MET="(()=>{const t=[...document.querySelectorAll('#main .tg .tile')].at(-1);const sp=t.querySelector('span:not(.em)'),em=t.querySelector('.em');return {f:parseFloat(getComputedStyle(sp).fontSize),e:em?parseFloat(getComputedStyle(em).fontSize):0,h:t.getBoundingClientRect().height}})()"
with sync_playwright() as p:
    b=p.chromium.launch()
    for lv in ['L1','L2','L3']:
        for L in ['uk','ru','en']:
            for W in [277,313,360,412,800]:
                pg=page(b,{'aac.lang':L,'aac.tour.seen':allseen,'aac.settings':json.dumps({'level':lv})},W,700)
                met={}
                for sz in ['s','m','l','xl']:
                    pg.evaluate(f"settings.size='{sz}';applyUI();render()");pg.wait_for_timeout(60)
                    c=pg.evaluate(COLS)
                    if W in EXP[sz]: check(f'{lv} {L} {W} {sz}: {EXP[sz][W]} columns',c==EXP[sz][W])
                    else: met[sz+'c']=c
                    check(f'{lv} {L} {W} {sz}: labels fit, no h-scroll',pg.evaluate(FIT))
                    met[sz]=pg.evaluate(MET)
                    if W in (277,360) and lv=='L2' and L=='uk': pg.screenshot(path=f'{OUT}/size_{sz}_{W}.png')
                if W==800: check(f'{lv} {L} 800: at least as many columns as at 412',met['sc']>=4 and met['mc']>=2 and met['lc']>=2)
                check(f'{lv} {L} {W}: font grows s<m<l<xl, s>=12',met['s']['f']>=12 and met['s']['f']<=met['m']['f']<=met['l']['f']<=met['xl']['f'] and met['s']['f']<met['xl']['f'])
                check(f'{lv} {L} {W}: icon grows s→xl, l taller than m',met['s']['e']<=met['m']['e']<=met['l']['e']<=met['xl']['e'] and met['l']['h']>met['m']['h'])
                pg.context.close()
    # настройки: 4 варианта, сразу применяется и сохраняется после перезапуска
    pg=page(b,{'aac.lang':'uk','aac.tour.seen':allseen},277,560)
    pg.click('#settingsBtn');pg.click('#sett .sg[data-g=home] .sgh')
    check('settings: 4 options, s first',pg.evaluate("[...$('#setSize').options].map(o=>o.value)")==['s','m','l','xl'])
    pg.select_option('#setSize','s');pg.wait_for_timeout(150)
    check('settings: applied at once',pg.evaluate("document.documentElement.dataset.size")=='s')
    pg.click('#sett .sg[data-g=main] .sgh')
    check('summary fits at 277',pg.evaluate("(()=>{const e=document.querySelector('#sett .sg[data-g=home] .sgs');return e.getBoundingClientRect().right<=innerWidth+1&&document.querySelector('#sett').scrollWidth<=document.querySelector('#sett').clientWidth+1})()"))
    pg.click('#closeSettBtn');pg.reload();pg.wait_for_timeout(300)
    check('size s survives restart',pg.evaluate("settings.size")=='s' and pg.evaluate(COLS)==3)
    # фото на плитке и картинка в окне вопроса
    png='data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    pg.evaluate(f"tree[0].img='{png}';render()")
    for sz in ['s','m','l','xl']:
        pg.evaluate(f"settings.size='{sz}';applyUI();render()")
        r=pg.evaluate("(()=>{const i=document.querySelector('#main .tg .tile img');const r=i.getBoundingClientRect();return [r.width,r.height]})()")
        check(f'photo on tile shown ({sz})',r[0]>=30 and abs(r[0]-r[1])<1)
    pg.evaluate("ask(Object.assign({},tree.find(n=>!n.c)||tree[0],{img:'%s'}))"%png);pg.wait_for_timeout(100)
    bi=pg.evaluate("(()=>{const i=document.querySelector('#ov .big img');if(!i)return null;const r=i.getBoundingClientRect();return [r.width,r.height]})()")
    check('picture in question window unchanged',bi is not None and bi[0]>=60)
    pg.evaluate("closeOv()")
    # слова «Азбуки» — прежняя сетка
    pg.click('#abcBtn');pg.evaluate("abc.prefix='м';render()");pg.wait_for_timeout(80)
    check('ABC words keep their own grid',pg.evaluate("!!document.querySelector('.abcres .grid')&&!document.querySelector('.abcres .tg')"))
    check('no script errors',not errors)
    b.close()
print('errors:',errors)
print(sum(r for _,r in results),'/',len(results),'passed')
