import os
import re

html_files = [f for f in os.listdir(".") if f.endswith(".html")]
js_files = [f"js/{f}" for f in os.listdir("js") if f.endswith(".js")]

terms_to_search = [
    "Rajesh Kumar", "Lead Agriculturist", "Sync Telemetry", "telemetry",
    "100% Verified", "95% Calibrated", "92% Cloud-Free",
    "B04", "B08", "ChromaDB", "embedding dimension",
    "mockData", "dummy", "fake", "Accuracy:"
]

print("=== SEARCHING HTML & JS FILES ===")
for path in html_files + js_files:
    if not os.path.exists(path):
        continue
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    
    matches = {}
    for term in terms_to_search:
        count = len(re.findall(re.escape(term), content, re.IGNORECASE))
        if count > 0:
            matches[term] = count
    
    if matches:
        print(f"\n[{path}]:")
        for k, v in matches.items():
            print(f"  - {k}: {v} matches")
