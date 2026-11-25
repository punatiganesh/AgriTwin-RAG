import re

files = [
    'assistant.html', 'crop-disease.html', 'dashboard.html', 'digital-twin.html',
    'evaluation.html', 'location.html', 'prediction.html', 'recommendations.html',
    'reports.html', 'satellite.html', 'settings.html', 'soil.html',
    'weather.html', 'xai.html'
]

NEW_TOPBAR_SNIPPET = """<div class="topbar-user-dropdown-wrap" id="userMenuWrapper">
              <button
                class="topbar-user-btn"
                id="userMenuBtn"
                type="button"
                aria-expanded="false"
                aria-label="Farmer profile menu"
              >
                <div class="user-avatar-sm" id="topbarAvatar">F</div>
                <div class="user-details d-none d-md-block text-start">
                  <div class="user-fullname" id="topbarName">Farmer</div>
                  <div class="user-role" id="topbarRole">AgriTwin Live</div>
                </div>
                <i class="fas fa-chevron-down dropdown-caret"></i>
              </button>
              <div class="user-dropdown-menu" id="userDropdownMenu">
                <div class="dropdown-user-header">
                  <div class="user-avatar-sm" id="dropdownAvatar">F</div>
                  <div class="dropdown-user-info">
                    <div class="dropdown-name" id="dropdownName">Farmer</div>
                    <div class="dropdown-sub" id="dropdownSub">Authenticated Farmer</div>
                  </div>
                </div>
                <div class="dropdown-divider"></div>
                <a href="settings.html" class="dropdown-item">
                  <i class="fas fa-user-cog"></i>
                  <span>My Account & Settings</span>
                </a>
                <a href="location.html" class="dropdown-item">
                  <i class="fas fa-map-marker-alt"></i>
                  <span>Farm Coordinates</span>
                </a>
                <div class="dropdown-divider"></div>
                <button type="button" class="dropdown-item text-danger btn-logout" id="topbarLogoutBtn">
                  <i class="fas fa-sign-out-alt"></i>
                  <span>Sign Out / Logout</span>
                </button>
              </div>
            </div>"""

for filename in files:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()

    # Replace userProfile block
    pattern = r'<a\s+[^>]*id=["\']userProfile["\'][\s\S]*?</a>'
    if re.search(pattern, content):
        new_content = re.sub(pattern, NEW_TOPBAR_SNIPPET, content, count=1)
    else:
        print(f"Warning: pattern not matched in {filename}")
        new_content = content

    # Ensure auth.js is included
    if 'js/auth.js' not in new_content:
        # insert before </body>
        new_content = new_content.replace('</body>', '  <script src="js/auth.js"></script>\n</body>')
        print(f"Added js/auth.js to {filename}")

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Successfully upgraded topbar dropdown in {filename}")
