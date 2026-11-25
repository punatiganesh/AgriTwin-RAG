import re

html_files = [
    "dashboard.html", "digital-twin.html", "weather.html", "soil.html",
    "satellite.html", "location.html", "crop-disease.html", "prediction.html",
    "xai.html", "assistant.html", "recommendations.html", "reports.html",
    "evaluation.html", "settings.html"
]

for hf in html_files:
    with open(hf, "r", encoding="utf-8") as f:
        content = f.read()

    orig = content
    # Replace Rajesh Kumar with Farmer / Farm User
    content = re.sub(r'Rajesh Kumar', 'Farmer', content)
    content = re.sub(r'Lead Agriculturist', 'Farm User', content)
    
    # Replace topbar avatar R with F
    content = re.sub(r'<div class="user-avatar-sm">R</div>', '<div class="user-avatar-sm">F</div>', content)
    content = re.sub(r'<div class="user-avatar-circle">R</div>', '<div class="user-avatar-circle">F</div>', content)
    
    # Replace "Sync Telemetry" with "Refresh Farm Data"
    content = re.sub(r'Sync Telemetry', 'Refresh Farm Data', content)

    if content != orig:
        with open(hf, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated user profile & sync button in {hf}")
