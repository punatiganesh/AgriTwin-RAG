import glob
import re

html_files = [
    "dashboard.html",
    "location.html",
    "weather.html",
    "digital-twin.html",
    "soil.html",
    "satellite.html",
    "prediction.html",
    "crop-disease.html",
    "xai.html",
    "assistant.html",
    "recommendations.html",
    "reports.html",
    "settings.html",
    "evaluation.html"
]

logout_btn_html = '''            <button class="user-action-btn btn-logout" id="logoutBtn" title="Sign Out / Logout" style="background:none;border:none;color:#ef4444;cursor:pointer;padding:6px;margin-left:4px;">
              <i class="fas fa-sign-out-alt"></i>
            </button>'''

for filename in html_files:
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Inject js/auth.js if not already present
        if "js/auth.js" not in content:
            # Insert before js/farmState.js or js/app.js or before </body>
            if '<script src="js/farmState.js"' in content:
                content = content.replace('<script src="js/farmState.js"', '<script src="js/auth.js"></script>\n    <script src="js/farmState.js"')
            elif '<script src="js/api.js"' in content:
                content = content.replace('<script src="js/api.js"', '<script src="js/auth.js"></script>\n    <script src="js/api.js"')
            elif '</body>' in content:
                content = content.replace('</body>', '    <script src="js/auth.js"></script>\n  </body>')

        # 2. Add logout button in user-profile-widget if not present
        if 'btn-logout' not in content and 'class="user-profile-widget"' in content:
            pattern = r'(<div class="user-profile-widget">.*?<a\s+href="settings\.html"[^>]*>.*?</a>)(.*?)(\s*</div>\s*</div>\s*</aside>)'
            # Search for the closing of the user-profile-widget
            def replacer(match):
                prefix = match.group(1)
                suffix = match.group(3)
                return f"{prefix}\n{logout_btn_html}{suffix}"
            
            content = re.sub(r'(<a\s+href="settings\.html"\s+class="user-action-btn"[^>]*>\s*<i class="fas fa-cog"></i>\s*</a>)', r'\1\n' + logout_btn_html, content)

        # 3. Add a logout option to topbar if appropriate or ensure btn-logout is clickable
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated {filename}")
    except Exception as e:
        print(f"Error updating {filename}: {e}")
