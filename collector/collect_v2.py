import os, json, urllib.request, urllib.parse, time, hashlib
from datetime import datetime

# .env 로드
env_path = "/Users/twinssn/Projects/dailypain/.env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k] = v

CLIENT_ID = os.environ["NAVER_CLIENT_ID"]
CLIENT_SECRET = os.environ["NAVER_CLIENT_SECRET"]

def search_kin(query, display=20, sort="date"):
    params = urllib.parse.urlencode({
        "query": query, "display": display, "sort": sort
    })
    url = f"https://openapi.naver.com/v1/search/kin.json?{params}"
    req = urllib.request.Request(url, headers={
        "X-Naver-Client-Id": CLIENT_ID,
        "X-Naver-Client-Secret": CLIENT_SECRET,
    })
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode()).get("items", [])
    except Exception as e:
        print(f"  [오류] {query}: {e}")
        return []

# 키워드 로드
with open("/Users/twinssn/Projects/dailypain/collector/keywords.json") as f:
    keywords = json.load(f)["b2b_pain_keywords"]

print(f"키워드 {len(keywords)}개로 수집 시작...\n")

seen = set()
results = []
for i, kw in enumerate(keywords, 1):
    print(f"  [{i}/{len(keywords)}] {kw}")
    items = search_kin(kw, display=10, sort="date")
    for item in items:
        link = item.get("link", "")
        link_hash = hashlib.md5(link.encode()).hexdigest()
        if link_hash not in seen:
            seen.add(link_hash)
            # HTML 태그 제거
            title = item.get("title", "").replace("<b>", "").replace("</b>", "")
            desc = item.get("description", "").replace("<b>", "").replace("</b>", "")
            results.append({
                "keyword": kw,
                "title": title,
                "description": desc,
                "link": link,
                "collected_at": datetime.now().isoformat()
            })
    time.sleep(0.15)

today = datetime.now().strftime("%Y-%m-%d")
outpath = f"/Users/twinssn/Projects/dailypain/data/{today}-raw-v2.json"
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"\n수집 완료: {len(results)}개 (중복 제거)")
print(f"저장: {outpath}")

# 샘플 5개
print("\n--- 샘플 5개 ---")
for r in results[:5]:
    print(f"[{r['keyword']}] {r['title'][:60]}")
    print(f"  {r['description'][:80]}")
    print()
