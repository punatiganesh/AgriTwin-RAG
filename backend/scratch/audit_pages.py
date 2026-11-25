import glob
import re
import os

html_files = sorted(glob.glob('../frontend/*.html'))
if not html_files:
    html_files = sorted(glob.glob('../*.html'))

for html in html_files:
    with open(html, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    scripts = re.findall(r'<script[^>]*src=[\'"]([^\'"]+)[\'"]', content)
    inline_fetch = re.findall(r'fetch\([\'"`]([^\'"`]+)[\'"`]', content)
    calls = re.findall(r'(FarmState\.[a-zA-Z0-9_]+|loadFarmContext|loadWeather|getWeather|getSoil)', content)
    print(f"{html}:")
    print(f"  Scripts: {scripts}")
    print(f"  Inline fetch: {list(set(inline_fetch))[:5]}")
    print(f"  Key calls: {list(set(calls))[:5]}")
