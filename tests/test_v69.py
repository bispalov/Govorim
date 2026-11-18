# v69: варианты по звучанию, «у … есть …», слова о людях
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
with sync_playwright() as p:
    b=p.chromium.launch()
    for L,cases in [('ru',[(['у','оксаны','есть','прогуны'],3,'подруги'),(['я','шучу','гулять'],1,'хочу'),(['хочу','пить','фоду'],2,'воду'),(['позвони','бабуске'],1,'бабушка'),(['я','хочу','есть','супп'],3,'суп')]),
                    ('uk',[(['у','оксани','є','прогуни'],3,'подруги'),(['подзвони','бабусі','і','сустці'],3,'сестрі'),(['хочу','пити','фоду'],2,'воду')]),
                    ('en',[(['call','my','sistor'],2,'sister'),(['i','want','some','wotter'],3,'water')])]:
      for lex in (0,1):                       # v75: без словаря и с настоящим lex/<язык>.txt (20–30 тыс. слов)
        pg=page(b,{'aac.lang':L,'aac.tour.seen':allseen,'aac.settings':json.dumps({'level':'L3'})},412,860)
        if lex:
            pg.evaluate(f"loadBundledLex('{L}')");pg.wait_for_timeout(300)
            check(f'{L}: bundled lexicon loaded', pg.evaluate(f"(LEXB['{L}']||[]).length")>=5000)
        else: pg.evaluate(f"LEXB['{L}']=null;LEXTRY['{L}']=true;delete LEXC['{L}']")
        tag=' [lex]' if lex else ''
        pg.evaluate("hearTab='sug';settings.hearTab='sug';openHear()")
        for H,i,want in cases:
            pg.evaluate(f"hearBuild={json.dumps(H,ensure_ascii=False)};hearOpen=true;hearSlot={i};refreshHear()");pg.wait_for_timeout(80)
            c=pg.evaluate(f"slotCands({i})")
            check(f'{L} {" ".join(H)}: «{want}» among options{tag}', want in c)
            if want in c: check(f'{L} {" ".join(H)}: shown in the panel{tag}', pg.locator('#main button', has_text=want).count()>0)
            if H[:4]==['у','оксаны','есть','прогуны']:
                check('ru «у … есть …»: no food options'+tag, not any(x in c for x in ['хлеб','мясо','суп','фрукты']))
            if H==['я','хочу','есть','супп']:
                check('ru «хочу есть …» still offers food'+tag, any(x in c for x in ['суп','хлеб']))
        check(f'{L}: people words in ABC/type dictionary{tag}', pg.evaluate("typeDict().includes(%s)"%json.dumps({'ru':'подруги','uk':'подруги','en':'friends'}[L])))
        pg.context.close()
    # с большим словарём (20 тыс. слов) — время подбора
    pg=page(b,{'aac.lang':'ru','aac.tour.seen':allseen},412,860)
    t=pg.evaluate("(()=>{const a=['подруги','прогулы'];for(let i=0;i<20000;i++)a.push('слово'+i.toString(36));localStorage.setItem('aac.lex.ru',a.join('\\n'));delete LEXC.ru;const t0=performance.now();soundCands('прогуны',6);return performance.now()-t0})()")
    check(f'20k-word list: options in {round(t)} ms (<400)', t<400)
    check('no script errors', not errors)
    b.close()
print('errors:',errors)
print(sum(r for _,r in results),'/',len(results),'passed')
