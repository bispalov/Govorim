# v70: вкладки 🎤 «Говорю я» / «Говорит собеседник»
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
NAMES={'ru':('Говорю я','Говорит собеседник'),'uk':('Говорю я','Говорить співрозмовник'),'en':('I’m speaking','The other person speaks')}
with sync_playwright() as p:
    b=p.chromium.launch()
    for L,(a,c) in NAMES.items():
        for W,H in [(277,492),(360,640)]:
            pg=page(b,{'aac.lang':L,'aac.tour.seen':allseen},W,H)
            pg.click('#micBtn');pg.wait_for_timeout(100)
            tabs=pg.locator('.tabs .tab')
            check(f'{L} {W}: tab names', c in tabs.nth(0).inner_text() and a in tabs.nth(1).inner_text() or a in tabs.nth(0).inner_text() and c in tabs.nth(1).inner_text())
            ok=pg.evaluate("[...document.querySelectorAll('.tabs .tab')].every(t=>t.scrollWidth<=t.clientWidth+1&&t.getBoundingClientRect().right<=innerWidth+0.5)")
            check(f'{L} {W}: tabs not cut', ok)
            if W==277: pg.screenshot(path=f'{OUT}/tabs_{L}.png')
            txt=pg.text_content('html')
            check(f'{L} {W}: old names gone', not any(x in pg.evaluate("JSON.stringify(U)") for x in ['Говорит человек','Говорить людина','Someone speaks','The person speaks']))
            pg.context.close()
    check('no script errors', not errors)
    b.close()
print('errors:',errors)
print(sum(r for _,r in results),'/',len(results),'passed')
