# v74: набранное в редакторе плиток не теряется при выборе фото, смене плитки/раздела, новой плитке, закрытии
import json
import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
exec(open(os.path.join(TESTS, 'test_v68.py'), encoding='utf-8').read().split("with sync_playwright() as p:")[0])
allseen=json.dumps({'home':1,'tiles':1,'hear':1,'show':1,'abc':1})
tree=lambda pg:pg.evaluate("JSON.stringify(tree)")
node=lambda pg,id:pg.evaluate("(id=>{const f=find(id);return f&&{l:f.n.l,s:f.n.s,e:f.n.e,img:!!f.n.img}})",id)
stored=lambda pg,id:pg.evaluate("(id=>{const w=l=>{for(const n of l){if(n.id===id)return n;if(n.c){const r=w(n.c);if(r)return r}}};const n=w(JSON.parse(localStorage.getItem(tk())||'[]'));return n&&{l:n.l,s:n.s,e:n.e,img:!!n.img}})",id)
inputs=lambda pg:pg.locator('#ed input[type=text]')
def fillAll(pg,vals):
    for i,v in enumerate(vals): inputs(pg).nth(i).fill(v)
import struct, zlib
_w=_h=40;_raw=b''.join(b'\x00'+bytes([200,60,60])*_w for _ in range(_h))
_c=lambda t,d:struct.pack('>I',len(d))+t+d+struct.pack('>I',zlib.crc32(t+d)&0xffffffff)
open(OUT+'/p.png','wb').write(b'\x89PNG\r\n\x1a\n'+_c(b'IHDR',struct.pack('>IIBBBBB',_w,_h,8,2,0,0,0))+_c(b'IDAT',zlib.compress(_raw))+_c(b'IEND',b''))
with sync_playwright() as p:
    b=p.chromium.launch()
    for lng,W,H,lv in [('ru',360,640,''),('uk',277,492,''),('en',360,640,''),('ru',313,556,'L3'),('uk',360,640,'L3')]:
        ls={'aac.lang':lng,'aac.tour.seen':allseen}
        if lv: ls['aac.settings']=json.dumps({'level':lv})
        pg=page(b,ls,W,H)
        pg.click('#gear');pg.wait_for_timeout(100)
        n=inputs(pg).count()
        # 1. Точный сценарий: новая плитка → набрать → фото → «Сохранить»
        pg.locator('#ed .row button').filter(has_text=pg.evaluate("uh('e_add')")).click();pg.wait_for_timeout(80)
        id1=pg.evaluate("sel");k=inputs(pg).count()-1     # имена+фразы, последнее — значок
        names=['Оксана','Оксана','Oksana'][:k//2] if k//2>1 else ['Оксана']
        vals=[('Имя%d'%i) for i in range(k//2)]+[('Фраза%d'%i) for i in range(k//2)]+['👩']
        fillAll(pg,vals)
        pg.locator('#ed input[type=file]').set_input_files(OUT+'/p.png');pg.wait_for_timeout(500)
        check(f'{lng}/{W}{lv}: photo set',node(pg,id1)['img'])
        check(f'{lng}/{W}{lv}: typed fields kept on screen after photo',[inputs(pg).nth(i).input_value() for i in range(k+1)]==vals)
        exp_l='|'.join(vals[:k//2]);exp_s='|'.join(vals[k//2:k])
        check(f'{lng}/{W}{lv}: name/phrase/icon already in tile and stored',node(pg,id1)['l']==exp_l and stored(pg,id1)=={'l':exp_l,'s':exp_s,'e':'👩','img':True})
        pg.locator('#ed .row button').filter(has_text=pg.evaluate("uh('e_save')")).click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: after Save still correct',stored(pg,id1)=={'l':exp_l,'s':exp_s,'e':'👩','img':True})
        # 2. Убрать фото — набранное сохраняется
        inputs(pg).nth(0).fill('Мама')
        pg.locator('#ed .edpic button.d').click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: remove photo keeps typed name',stored(pg,id1)['l'].split('|')[0]=='Мама' and not stored(pg,id1)['img'] and inputs(pg).nth(0).input_value()=='Мама')
        # 3. Новая плитка, пока набрано в текущей
        inputs(pg).nth(0).fill('Папа')
        pg.locator('#ed .row button').filter(has_text=pg.evaluate("uh('e_add')")).click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: adding another tile keeps typed text of previous',stored(pg,id1)['l'].split('|')[0]=='Папа')
        id2=pg.evaluate("sel");check(f'{lng}/{W}{lv}: new tile selected',id2!=id1)
        # 4. Смена плитки в списке
        inputs(pg).nth(0).fill('Чай')
        pg.locator('#ed select').nth(1).select_option(id1);pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: switching tile keeps typed text',stored(pg,id2)['l'].split('|')[0]=='Чай' and inputs(pg).nth(0).input_value()=='Папа')
        # 5. Смена раздела
        inputs(pg).nth(0).fill('Брат')
        opts=pg.locator('#ed select').nth(0).locator('option').evaluate_all("o=>o.map(x=>x.value)")
        pg.locator('#ed select').nth(0).select_option(opts[1]);pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: switching section keeps typed text',stored(pg,id1)['l'].split('|')[0]=='Брат')
        pg.locator('#ed select').nth(0).select_option('');pg.wait_for_timeout(80)
        # 6. Закрытие без «Сохранить» — кнопкой и «Назад»
        pg.locator('#ed select').nth(1).select_option(id1);inputs(pg).nth(0).fill('Сестра')
        pg.locator('#ed .helphead button').click();pg.wait_for_timeout(120)
        print('   langs:',pg.evaluate("edLangs()"),'shown:',pg.evaluate("(id=>t(find(id).n.l))",id1))
        check(f'{lng}/{W}{lv}: Close saves typed text',stored(pg,id1)['l'].split('|')[0]=='Сестра' and pg.evaluate("ed.style.display")=='none')
        check(f'{lng}/{W}{lv}: tile on main screen shows new name',pg.locator('#main .tile').filter(has_text=pg.evaluate("(id=>t(find(id).n.l))",id1)).count()==1 and 'Сестра' in pg.evaluate("find(%r).n.l"%id1))
        pg.click('#gear');pg.locator('#ed select').nth(1).select_option(id2);inputs(pg).nth(0).fill('Кофе')
        pg.evaluate("appBack()");pg.wait_for_timeout(120)
        check(f'{lng}/{W}{lv}: Back saves typed text',stored(pg,id2)['l'].split('|')[0]=='Кофе' and pg.evaluate("ed.style.display")=='none')
        # 7. Перезагрузка — всё на месте; без изменений — ничего не пишется
        pg.reload();pg.wait_for_timeout(300)
        check(f'{lng}/{W}{lv}: after reload names kept',stored(pg,id1)['l'].split('|')[0]=='Сестра' and stored(pg,id2)['l'].split('|')[0]=='Кофе')
        pg.click('#gear');pg.locator('#ed select').nth(1).select_option(id1);pg.wait_for_timeout(50)
        pg.evaluate("localStorage.setItem(tk(),JSON.stringify(JSON.parse(localStorage.getItem(tk())),null,1))")
        pg.locator('#ed .helphead button').click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: closing without changes does not save','\n' in pg.evaluate("localStorage.getItem(tk())"))
        # 8. Удаление и сброс работают как раньше
        pg.click('#gear');pg.locator('#ed select').nth(1).select_option(id2)
        pg.on('dialog',lambda d:d.accept())
        pg.locator('#ed .row button.d').filter(has_text=pg.evaluate("uh('e_del')")).click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: delete still works',stored(pg,id2) is None and pg.evaluate("sel")=='')
        pg.locator('#ed .helphead button').click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: deleted tile not re-saved on close',stored(pg,id2) is None)
        pg.click('#gear');pg.locator('#ed .row button.d').filter(has_text=pg.evaluate("uh('e_reset')")).click();pg.wait_for_timeout(80)
        pg.locator('#ed .helphead button').click();pg.wait_for_timeout(80)
        check(f'{lng}/{W}{lv}: reset still works',stored(pg,id1) is None)
        pg.context.close()
    b.close()
check('no page errors',not errors)
src=SRC
for t in ['Набранное сохраняется само','Набране зберігається саме','What you type is kept by itself']: check('help: '+t,src.count(t)==1)
for l,r in results:
    if not r: print('FAIL',l)
print(errors[:3]);print(sum(r for _, r in results), '/', len(results), 'passed')
