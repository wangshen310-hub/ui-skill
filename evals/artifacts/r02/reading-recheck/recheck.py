import functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
from pathlib import Path
import tempfile
import threading
from patchright.sync_api import sync_playwright

ROOT = Path('/opt/ui-skill-lab-20261020/round-0002-reading')
OUT = ROOT / 'parent-recheck'
OUT.mkdir(exist_ok=False)
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self, *_): pass
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(Quiet, directory=str(ROOT/'source/dist')))
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
url = f'http://127.0.0.1:{server.server_port}'
result = {'runtime':'Tencent Cloud / isolated Chrome / actual browser keyboard and touch emulation', 'checks':[]}
def state(page):
    return page.evaluate('''() => ({title:document.querySelector('#article-title').textContent,
      scroll:scrollY, maxScroll:document.documentElement.scrollHeight-innerHeight,
      headingTop:document.querySelector('#article-title').getBoundingClientRect().top,
      focusTag:document.activeElement.tagName, focusId:document.activeElement.id})''')
def record(label, data):
    result['checks'].append({'label':label,'data':data})
try:
    with tempfile.TemporaryDirectory(prefix='ui-skill-reading-r2-') as profiles, sync_playwright() as p:
        desktop = p.chromium.launch_persistent_context(str(Path(profiles)/'desktop'), executable_path='/usr/bin/google-chrome', headless=True, viewport={'width':1440,'height':1000}, args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            page=desktop.pages[0]
            page.goto(url, wait_until='networkidle')
            page.locator('.toc-item[data-index="1"]').focus()
            page.keyboard.press('Enter')
            current=state(page); record('actual-enter-selects-article', current)
            assert current['title']=='巷子尽头的早餐' and current['focusId']=='article-title'
            page.keyboard.press('Tab'); record('following-tab',state(page))
            assert page.evaluate('document.activeElement.tagName')=='BUTTON'
        finally: desktop.close()
        phone = p.chromium.launch_persistent_context(str(Path(profiles)/'phone'), executable_path='/usr/bin/google-chrome', headless=True, viewport={'width':390,'height':600}, is_mobile=True, has_touch=True, args=['--no-sandbox','--disable-dev-shm-usage'])
        try:
            page=phone.pages[0]; page.goto(url,wait_until='networkidle')
            page.evaluate('scrollTo(0,document.documentElement.scrollHeight)')
            before=state(page); record('before-next-real-positive-scroll',before)
            assert before['scroll']>0, 'scroll precondition was not exercised'
            page.screenshot(path=str(OUT/'before-next.png'))
            page.locator('#next').tap()
            after=state(page); record('after-next',after)
            assert after['title']=='巷子尽头的早餐' and after['scroll']==0
            assert 0<=after['headingTop']<600 and after['focusId']=='article-title'
            page.screenshot(path=str(OUT/'after-next.png'))
            metadata=[]
            for index in range(3):
                page.goto(url+f'/#essay-{index+1}',wait_until='networkidle')
                metadata.append(page.evaluate('''() => ({title:document.querySelector('#article-title').textContent,
                  chars:[...document.querySelectorAll('#article-body p')].map(p=>p.textContent).join('').length,
                  counter:document.querySelector('#page-number').textContent,
                  hasReadTime:/\\d+\\s*分钟/.test(document.body.innerText)})'''))
            record('content-and-metadata',metadata)
            assert [m['chars'] for m in metadata]==[115,109,97]
            assert all(not m['hasReadTime'] for m in metadata)
        finally: phone.close()
    result['passed']=True
except Exception as e:
    result['passed']=False; result['error']=repr(e)
    raise
finally:
    server.shutdown(); server.server_close(); thread.join(timeout=5)
    (OUT/'observations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
