# Общая часть тестов Govorim: где лежит приложение, по какому адресу его открывать, заглушки сети.
#
# Приложение — папка над tests/ (корень репозитория). Адрес выбирается так:
#   1) аргумент --url=http://…/  или переменная окружения GOVORIM_URL;
#   2) иначе http://localhost:8765/Govorim/ — если там уже запущен сервер и он отдаёт ЭТОТ index.html
#      (например: cd <папка над Govorim>; python3 -m http.server 8765);
#   3) иначе тест сам поднимает временный сервер (свободный порт), где /Govorim/ — эта папка.
# Снимки экрана пишутся во временную папку OUT (или GOVORIM_OUT).
import os, sys, re, json, socket, tempfile, threading, functools, http.server, urllib.request

TESTS = os.path.dirname(os.path.abspath(__file__))
APP = os.path.dirname(TESTS)
APP_INDEX = os.path.join(APP, 'index.html')
SRC = open(APP_INDEX, encoding='utf-8').read()
VER = int(re.search(r'const APP_VERSION\s*=\s*(\d+)', SRC).group(1))
OUT = os.environ.get('GOVORIM_OUT') or tempfile.mkdtemp(prefix='govorim-shots-')
os.makedirs(OUT, exist_ok=True)


class Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def send_head(self):
        # Без ответа 304 по If-Modified-Since: он сравнивает время файла с точностью до секунды, и файл,
        # заменённый в ту же секунду (тест обновления service worker), сервер считал неизменённым —
        # браузер так и не видел новый sw.js. GitHub Pages сравнивает по содержимому (ETag).
        if 'If-Modified-Since' in self.headers: del self.headers['If-Modified-Since']
        return super().send_head()
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache'); super().end_headers()


def serve(root, port=0):
    """Статический сервер папки root на 127.0.0.1; возвращает (сервер, порт)."""
    s = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Q, directory=root))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s, s.server_address[1]


def _arg_url():
    a = sys.argv[1:]
    for i, x in enumerate(a):
        if x.startswith('--url='): return x[6:]
        if x == '--url' and i + 1 < len(a): return a[i + 1]
    return os.environ.get('GOVORIM_URL')


def _same_app(base):
    try:
        return urllib.request.urlopen(base + 'index.html', timeout=2).read().decode('utf-8') == SRC
    except Exception:
        return False


class _NoServer:
    def shutdown(self): pass


BASE = _arg_url()
srv = _NoServer()
if BASE:
    if not BASE.endswith('/'): BASE += '/'
elif _same_app('http://localhost:8765/Govorim/'):
    BASE = 'http://localhost:8765/Govorim/'
else:
    _root = tempfile.mkdtemp(prefix='govorim-site-')
    os.symlink(APP, os.path.join(_root, 'Govorim'))
    srv, _port = serve(_root)
    BASE = f'http://127.0.0.1:{_port}/Govorim/'
URL = BASE + 'index.html'
ORIGIN = re.match(r'^[a-z]+://[^/]+', BASE).group(0)
print(f'Govorim v{VER}: {URL}')


def local_only(ctx):
    """Интернет закрыт: пропускаются только запросы к самому приложению."""
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(ORIGIN) else r.abort())
