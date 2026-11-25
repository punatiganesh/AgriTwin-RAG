import re

files = [
    'assistant.html', 'crop-disease.html', 'dashboard.html', 'digital-twin.html',
    'evaluation.html', 'location.html', 'prediction.html', 'recommendations.html',
    'reports.html', 'satellite.html', 'settings.html', 'soil.html',
    'weather.html', 'xai.html'
]

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    match = re.search(r'(<a\s+[^>]*id=["\']userProfile["\'][\s\S]*?</a>)', content)
    if match:
        print(f"=== {f} ===")
        print(match.group(1))
    else:
        print(f"=== {f} === NOT MATCHED")
