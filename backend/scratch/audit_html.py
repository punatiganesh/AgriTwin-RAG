import re

html_files = [
    "dashboard.html", "digital-twin.html", "weather.html", "soil.html",
    "satellite.html", "location.html", "crop-disease.html", "prediction.html",
    "xai.html", "assistant.html", "recommendations.html", "reports.html",
    "evaluation.html", "settings.html"
]

print("=== HTML FILES AUDIT ===")
for hf in html_files:
    with open(hf, "r", encoding="utf-8") as f:
        content = f.read()
    
    rajesh = len(re.findall(r"Rajesh Kumar", content, re.I))
    telemetry = len(re.findall(r"telemetry", content, re.I))
    sync_tel = len(re.findall(r"Sync Telemetry", content, re.I))
    b04 = len(re.findall(r"B04|B08", content))
    fake_perc = len(re.findall(r"100% Verified|95% Calibrated|92% Cloud-Free", content))
    
    print(f"{hf:22} | Rajesh: {rajesh} | Telemetry: {telemetry} | SyncTel: {sync_tel} | B04/B08: {b04} | FakePerc: {fake_perc}")
