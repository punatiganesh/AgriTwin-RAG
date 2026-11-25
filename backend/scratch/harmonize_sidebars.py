import os
import re

html_files = [
    "dashboard.html", "digital-twin.html", "weather.html", "soil.html",
    "satellite.html", "location.html", "crop-disease.html", "prediction.html",
    "xai.html", "assistant.html", "recommendations.html", "reports.html",
    "evaluation.html", "settings.html"
]

def get_sidebar_html(active_file):
    def is_active(href):
        return ' class="nav-item active"' if href == active_file else ' class="nav-item"'

    return f"""      <!-- ==================== LEFT SIDEBAR ==================== -->
      <aside class="app-sidebar" id="appSidebar">
        <!-- Brand Header -->
        <div class="sidebar-brand">
          <a href="dashboard.html" class="brand-logo-wrap">
            <div class="brand-icon">
              <i class="fas fa-leaf"></i>
            </div>
            <div class="brand-text">
              <div class="brand-title">
                AgriTwin <span class="badge-rag">RAG</span>
              </div>
              <div class="brand-subtitle">Precision Digital Twin</div>
            </div>
          </a>
          <button
            class="sidebar-collapse-btn d-none d-lg-flex"
            id="sidebarCollapseBtn"
            title="Toggle Sidebar"
          >
            <i class="fas fa-chevron-left"></i>
          </button>
        </div>

        <!-- Navigation Sections -->
        <div class="sidebar-nav-container">
          <div class="nav-section-label">OVERVIEW</div>
          <ul class="sidebar-menu">
            <li>
              <a href="dashboard.html"{is_active("dashboard.html")}>
                <i class="fas fa-th-large nav-icon"></i>
                <span class="nav-label">Dashboard</span>
              </a>
            </li>
          </ul>

          <div class="nav-section-label">FARM</div>
          <ul class="sidebar-menu">
            <li>
              <a href="digital-twin.html"{is_active("digital-twin.html")}>
                <i class="fas fa-cube nav-icon"></i>
                <span class="nav-label">Digital Twin</span>
              </a>
            </li>
            <li>
              <a href="weather.html"{is_active("weather.html")}>
                <i class="fas fa-cloud-sun nav-icon"></i>
                <span class="nav-label">Weather</span>
              </a>
            </li>
            <li>
              <a href="soil.html"{is_active("soil.html")}>
                <i class="fas fa-seedling nav-icon"></i>
                <span class="nav-label">Soil Intelligence</span>
              </a>
            </li>
            <li>
              <a href="satellite.html"{is_active("satellite.html")}>
                <i class="fas fa-satellite nav-icon"></i>
                <span class="nav-label">Satellite & NDVI</span>
              </a>
            </li>
            <li>
              <a href="location.html"{is_active("location.html")}>
                <i class="fas fa-map-marker-alt nav-icon"></i>
                <span class="nav-label">Farm Location</span>
              </a>
            </li>
          </ul>

          <div class="nav-section-label">AI</div>
          <ul class="sidebar-menu">
            <li>
              <a href="crop-disease.html"{is_active("crop-disease.html")}>
                <i class="fas fa-virus nav-icon"></i>
                <span class="nav-label">Crop Disease</span>
              </a>
            </li>
            <li>
              <a href="prediction.html"{is_active("prediction.html")}>
                <i class="fas fa-shield-alt nav-icon"></i>
                <span class="nav-label">Farm Risk</span>
              </a>
            </li>
            <li>
              <a href="assistant.html"{is_active("assistant.html")}>
                <i class="fas fa-robot nav-icon"></i>
                <span class="nav-label">RAG Assistant</span>
              </a>
            </li>
            <li>
              <a href="recommendations.html"{is_active("recommendations.html")}>
                <i class="fas fa-clipboard-list nav-icon"></i>
                <span class="nav-label">Recommendations</span>
              </a>
            </li>
          </ul>

          <div class="nav-section-label">REPORTS</div>
          <ul class="sidebar-menu">
            <li>
              <a href="reports.html"{is_active("reports.html")}>
                <i class="fas fa-file-alt nav-icon"></i>
                <span class="nav-label">Farm Report</span>
              </a>
            </li>
          </ul>

          <div class="nav-section-label">RESEARCH / TECHNICAL</div>
          <ul class="sidebar-menu">
            <li>
              <a href="evaluation.html"{is_active("evaluation.html")}>
                <i class="fas fa-chart-line nav-icon"></i>
                <span class="nav-label">Model Evaluation</span>
              </a>
            </li>
            <li>
              <a href="xai.html"{is_active("xai.html")}>
                <i class="fas fa-lightbulb nav-icon"></i>
                <span class="nav-label">Explainable AI (XAI)</span>
              </a>
            </li>
            <li>
              <a href="settings.html"{is_active("settings.html")}>
                <i class="fas fa-cog nav-icon"></i>
                <span class="nav-label">Settings & Provenance</span>
              </a>
            </li>
          </ul>
        </div>

        <!-- Sidebar User Footer -->
        <div class="sidebar-footer">
          <div class="user-profile-widget">
            <div class="user-avatar-circle" id="userAvatar">F</div>
            <div class="user-info">
              <div class="user-name" id="userName">Farmer Profile</div>
              <div class="user-meta" id="userMeta">AgriTwin User</div>
            </div>
            <a
              href="settings.html"
              class="user-action-btn"
              title="Settings & Provenance"
            >
              <i class="fas fa-cog"></i>
            </a>
          </div>
        </div>
      </aside>"""

for hf in html_files:
    if not os.path.exists(hf):
        continue
    with open(hf, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace sidebar
    new_sidebar = get_sidebar_html(hf)
    pattern = r'<!-- ==================== LEFT SIDEBAR ==================== -->.*?<!-- ==================== MAIN CONTENT'
    match = re.search(pattern, content, re.DOTALL)
    if not match:
        # try without comment
        pattern = r'<aside class="app-sidebar".*?</aside>'
        match = re.search(pattern, content, re.DOTALL)
        if match:
            content = content[:match.start()] + new_sidebar + content[match.end():]
            print(f"Updated sidebar via aside tag in {hf}")
    else:
        # replace between comments
        content = content[:match.start()] + new_sidebar + "\n\n      <!-- ==================== MAIN CONTENT" + content[match.end():]
        print(f"Updated sidebar via comments in {hf}")

    with open(hf, "w", encoding="utf-8") as f:
        f.write(content)

print("Sidebar harmonization complete.")
