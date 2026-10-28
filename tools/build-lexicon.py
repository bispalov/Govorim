#!/usr/bin/env python3
"""
Скачивает частотные списки слов FrequencyWords (hermitdave) и кладёт их в ./lex/,
чтобы они поставлялись вместе с приложением и работали офлайн без кнопки «Загрузить словари».

Запуск (нужен интернет, из корня репозитория):
    python tools/build-lexicon.py

Результат: lex/ru.txt, lex/uk.txt, lex/en.txt (по одному слову в строке, по убыванию частоты).
Приложение само отфильтрует их при загрузке (только буквы нужного алфавита, без дублей и грубых слов).

Источник: https://github.com/hermitdave/FrequencyWords  (на основе OpenSubtitles)
Лицензия данных: CC BY-SA 4.0. Сохраняйте указание источника и эту лицензию при публикации списков.
"""
import os
import re
import sys
import urllib.error
import urllib.request

BASE = "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/"
# Сколько слов нужно приложению; берём с запасом, т. к. часть строк отсеется фильтром
WANT = {"ru": 20000, "uk": 20000, "en": 10000}
RESERVE = 1.6


def fetch_head(url, max_lines):
    """Читает только первые max_lines строк большого файла."""
    lines = []
    with urllib.request.urlopen(url, timeout=60) as resp:
        for raw in resp:
            lines.append(raw.decode("utf-8", "replace").rstrip("\n"))
            if len(lines) >= max_lines:
                break
    return lines


def first_tokens(lines):
    out = []
    for ln in lines:
        parts = ln.strip().split()
        if parts:
            out.append(parts[0].lower().replace("ё", "е"))
    return out


def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lex")
    os.makedirs(out_dir, exist_ok=True)
    for lang, n in WANT.items():
        words = None
        for name in (f"{lang}_50k.txt", f"{lang}_full.txt"):
            url = f"{BASE}{lang}/{name}"
            try:
                words = first_tokens(fetch_head(url, int(n * RESERVE)))
                print(f"{lang}: {len(words)} строк из {name}")
                break
            except urllib.error.URLError as e:
                print(f"{lang}: {name} недоступен ({e})", file=sys.stderr)
        if not words:
            print(f"{lang}: пропущен", file=sys.stderr)
            continue
        with open(os.path.join(out_dir, f"{lang}.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(words) + "\n")
    with open(os.path.join(out_dir, "LICENSE.txt"), "w", encoding="utf-8") as f:
        f.write(
            "Word lists derived from FrequencyWords by hermitdave "
            "(https://github.com/hermitdave/FrequencyWords), based on OpenSubtitles.\n"
            "Licensed under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/).\n"
        )
    print("Готово: lex/ru.txt, lex/uk.txt, lex/en.txt")


if __name__ == "__main__":
    main()
