# Прогон всех тестов Govorim по очереди: python3 Govorim/tests/run_all.py [--url=http://…/Govorim/]
# Каждый тест печатает «N / M passed»; здесь — сводка и строки FAIL упавших тестов.
import glob, os, re, subprocess, sys
T = os.path.dirname(os.path.abspath(__file__))
total = ok = 0; bad = []
for f in sorted(glob.glob(os.path.join(T, 'test_v*.py')), key=lambda p: int(re.search(r'v(\d+)', p).group(1))):
    r = subprocess.run([sys.executable, f] + sys.argv[1:], capture_output=True, text=True)
    m = re.findall(r'(\d+) / (\d+) passed', r.stdout)
    p, n = map(int, m[-1]) if m else (0, 0)
    good = n > 0 and p == n and 'Traceback' not in r.stderr
    name = os.path.basename(f); total += n; ok += p
    print(f'{name:14} {p:4} / {n:<4} {"OK" if good else "FAIL"}')
    if not good:
        bad.append(name)
        print('\n'.join(l for l in r.stdout.splitlines() if l.startswith('FAIL'))[:3000])
        if r.stderr.strip(): print(r.stderr.strip()[-2000:])
print(f'\nВсего: {ok} / {total}' + ('' if not bad else '   ошибки: ' + ', '.join(bad)))
sys.exit(1 if bad else 0)
