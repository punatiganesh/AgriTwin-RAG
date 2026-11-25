import glob
import re

files = [
    'assistant.html', 'crop-disease.html', 'dashboard.html', 'digital-twin.html',
    'evaluation.html', 'location.html', 'prediction.html', 'recommendations.html',
    'reports.html', 'satellite.html', 'settings.html', 'soil.html',
    'weather.html', 'xai.html'
]

print(f"{'Filename':22} | {'auth.js':7} | {'wrap':5} | {'userProfile':12}")
print("-" * 55)

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    has_auth_js = 'js/auth.js' in content
    has_dropdown_wrap = 'topbar-user-dropdown-wrap' in content
    has_user_profile = 'userProfile' in content or 'userMenuBtn' in content
    print(f"{f:22} | {str(has_auth_js):7} | {str(has_dropdown_wrap):5} | {str(has_user_profile):12}")
