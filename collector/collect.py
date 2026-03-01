import os
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

env_vars = {}
env_path = os.path.join(PROJECT_DIR, ".env")
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k] = v

CLIENT_ID = env_vars["NAVER_CLIENT_ID"]
CLIENT_SECRET = env_vars["NAVER_CLIENT_SECRET"]

def clean_html(text):
    return re.sub(r"<[^>]+>", "", text)

def search_kin(query, display=20, sort="date"):
    encoded = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/kin.json?query={encoded}&display={display}&sort={sort}"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", CLIENT_ID)
    req.add_header("X-Naver-Client-Secret", CLIENT_SECRET)
    res = urllib.request.urlopen(req)
    return json.loads(res.read().decode("utf-8"))

def collect_pain_points():
    keywords_path = os.path.join(SCRIPT_DIR, "keywords.json")
    with open(keywords_path) as f:
        kw = json.load(f)

    seen_links = set()
    results = []

    for pattern in kw["pain_patterns"]:
        try:
            data = search_kin(pattern, display=10, sort="date")
            for item in data.get("items", []):
                link = item["link"]
                if link in seen_links:
                    continue
                seen_links.add(link)
                results.append({
                    "keyword": pattern,
                    "title": clean_html(item["title"]),
                    "description": clean_html(item["description"]),
                    "link": link,
                    "collected_at": datetime.now().isoformat()
                })
        except Exception as e:
            print(f"[ERROR] '{pattern}': {e}")

    print(f"\n수집 완료: {len(results)}개 (중복 제거됨)")

    output_dir = os.path.join(PROJECT_DIR, "data")
    os.makedirs(output_dir, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    output_path = os.path.join(output_dir, f"{today}-raw.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"저장: {output_path}")
    return results

if __name__ == "__main__":
    results = collect_pain_points()
    print(f"\n--- 샘플 5개 ---")
    for r in results[:5]:
        print(f"[{r['keyword']}] {r['title']}")
        print(f"  {r['description'][:80]}...")
        print()
