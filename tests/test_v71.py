# v71: «потянуть вниз — перезагрузить» отключено; что теряется при перезагрузке
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
lost={}
with sync_playwright() as p:
    b=p.chromium.launch()
    for W,H in [(360,640),(277,492)]:
        pg=page(b,{'aac.lang':'uk','aac.tour.seen':allseen},W,H)
        cs=lambda q,prop: pg.evaluate(f"(()=>{{const e=document.querySelector({json.dumps(q)});return e?getComputedStyle(e).{prop}:null}})()")
        check(f'{W}: html overscroll-y none', cs('html','overscrollBehaviorY')=='none')
        check(f'{W}: body overscroll-y none', cs('body','overscrollBehaviorY')=='none')
        for q in ['#main','#ov','#sett','#help','#tourBox']:
            if q=='#tourBox': pg.evaluate("tourStart('home')")
            check(f'{W}: {q} contain', cs(q,'overscrollBehaviorY')=='contain')
            if q=='#tourBox': pg.evaluate("tourEnd()")
        pg.evaluate("hearTab='sug';settings.hearTab='sug';hearBuild=['я','хочу','пити'];hearOpen=true;openHear()");pg.wait_for_timeout(80)
        check(f'{W}: 🎤 frame contain', cs('.hbuild','overscrollBehaviorY')=='contain')
        # прокрутка #main и окон по-прежнему работает
        pg.evaluate("hearBuild=[];refreshHear();path=[];hearOn=false;render()")
        pg.evaluate("document.querySelector('#main').scrollTop=200");check(f'{W}: #main scrolls', pg.evaluate("document.querySelector('#main').scrollTop")>0)
        pg.click('#helpBtn');pg.evaluate("helpEl.scrollTop=300");check(f'{W}: help scrolls', pg.evaluate("helpEl.scrollTop")>0)
        pg.screenshot(path=f'{OUT}/v71_{W}.png');pg.locator('#help .helphead button').click()
        if W==360:
            # что теряется при перезагрузке (для отчёта пользователю)
            pg.evaluate("hearTab='sug';settings.hearTab='sug';hearBuild=['я','хочу','пити'];hearOpen=true;openHear()")
            pg.evaluate("abcLine=['мені','потрібно']")
            pg.evaluate("hearTab='show';settings.hearTab='show';render();showShow('Зараз прийде лікар',false)")
            pg.reload();pg.wait_for_timeout(400)
            lost=pg.evaluate("({frame:hearBuild.join(' '),abc:abcLine.join(' '),show:showText,hist:(JSON.parse(localStorage.getItem('aac.showhist')||'[]')||[]).length,screen:hearOn?'hear':(path.length?'path':'home')})")
            print('after reload:',lost)
        pg.context.close()
    check('no script errors', not errors)
    b.close()
print('errors:',errors)
print(sum(r for _,r in results),'/',len(results),'passed')
