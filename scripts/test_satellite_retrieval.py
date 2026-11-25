import os
import sys
import time
import requests

def test():
    lat = 9.571529
    lon = 77.675734
    print(f"Testing Sentinel-2 retrieval for lat={lat}, lon={lon}...")
    
    # 1. Get SAS Token
    token = None
    try:
        t_res = requests.get("https://planetarycomputer.microsoft.com/api/sas/v1/token/sentinel-2-l2a", timeout=10)
        if t_res.status_code == 200:
            token = t_res.json().get("token")
            print("Acquired PC SAS token successfully.")
    except Exception as e:
        print(f"Token acquisition failed: {e}")

    # 2. Search Planetary Computer STAC
    delta = 0.02
    bbox = [lon - delta, lat - delta, lon + delta, lat + delta]
    now = time.time()
    
    # Windows
    search_windows = [45, 90, 180, 365]
    item = None
    for days in search_windows:
        start_date = time.strftime("%Y-%m-%d", time.gmtime(now - days * 86400))
        end_date = time.strftime("%Y-%m-%d", time.gmtime(now))
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": f"{start_date}/{end_date}",
            "query": {"eo:cloud_cover": {"lt": 30.0}},
            "sortby": [{"field": "properties.datetime", "direction": "desc"}],
            "limit": 3
        }
        try:
            res = requests.post("https://planetarycomputer.microsoft.com/api/stac/v1/search", json=payload, timeout=20)
            if res.status_code == 200:
                features = res.json().get("features", [])
                if features:
                    item = features[0]
                    print(f"Found item in {days}-day window: {item['id']}")
                    break
        except Exception as e:
            print(f"Search failed for {days}-day window: {e}")

    if not item:
        print("No item found.")
        return

    item_id = item["id"]
    props = item.get("properties", {})
    cloud = props.get("eo:cloud_cover")
    dt = props.get("datetime")
    print(f"Selected Item: {item_id}, Date: {dt}, Cloud: {cloud}%")

    # 3. Sample center point
    url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/point/{lon},{lat}"
    params = {
        "collection": "sentinel-2-l2a",
        "item": item_id,
        "assets": ["B04", "B08"],
    }
    if token:
        params["token"] = token
    headers = {"User-Agent": "AgriTwin-RAG/1.0"}

    p_res = requests.get(url, params=params, headers=headers, timeout=25)
    print(f"Point sample status: {p_res.status_code}")
    if p_res.status_code == 200:
        val = p_res.json().get("values", [])
        print(f"Values: {val}")
        red_raw, nir_raw = float(val[0]), float(val[1])
        ndvi = (nir_raw - red_raw) / (nir_raw + red_raw)
        print(f"Calculated NDVI: {ndvi:.4f}")
        
    # 4. Preview image URL
    preview_url = f"https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?collection=sentinel-2-l2a&item={item_id}&assets=visual&asset_bidx=visual%7C1,2,3&nodata=0&format=png"
    if token:
        preview_url += f"&token={token}"
    print(f"Preview URL: {preview_url}")

if __name__ == "__main__":
    test()
