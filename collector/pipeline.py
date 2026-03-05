"""
DailyPain 통합 파이프라인
collect(네이버 API) → classify(AI) → upload(D1)
"""
import os
import json
import urllib.request
import urllib.parse
import re
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

# .env 로드
env_vars = {}
with open(os.path.join(PROJECT_DIR, ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k] = v

NAVER_ID = env_vars["NAVER_CLIENT_ID"]
NAVER_SECRET = env_vars["NAVER_CLIENT_SECRET"]
OPENAI_KEY = env_vars["OPENAI_API_KEY"]
D1_API_URL = env_vars.get("D1_API_URL", "")
D1_API_KEY = env_vars.get("D1_API_KEY", "")


# ========== 1단계: 수집 ==========

def clean_html(text):
    return re.sub(r"<[^>]+>", "", text)

def search_kin(query, display=20, sort="date"):
    encoded = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/kin.json?query={encoded}&display={display}&sort={sort}"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", NAVER_ID)
    req.add_header("X-Naver-Client-Secret", NAVER_SECRET)
    res = urllib.request.urlopen(req)
    return json.loads(res.read().decode("utf-8"))

def collect():
    with open(os.path.join(SCRIPT_DIR, "keywords.json")) as f:
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
            print(f"  [수집 ERROR] '{pattern}': {e}")

    print(f"[수집] {len(results)}개 (중복 제거)")
    return results


# ========== 2단계: AI 분류 ==========

def call_openai(prompt):
    url = "https://api.openai.com/v1/chat/completions"
    body = json.dumps({
        "model": "gpt-5-nano",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body)
    req.add_header("Authorization", f"Bearer {OPENAI_KEY}")
    req.add_header("Content-Type", "application/json")
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def classify_batch(items):
    prompt = """네이버 지식인에서 수집한 질문 목록이다. 각 질문을 분석해서 JSON 배열로 응답.

## 판단 기준
- "actionable": true = 소프트웨어, 앱, 웹서비스, 자동화 도구로 해결 가능한 비즈니스 문제
- "actionable": false = 개인 건강, 연애, 감정, 취미, 일반 상식, 숙제, 법률 상담 등

## 중요 규칙
- 제목과 내용이 불일치하면 내용(description) 기준으로 판단
- 판단이 애매하면 반드시 false 처리
- "~추천해주세요"가 이미 시장에 흔한 서비스면 pain_score 낮게
- 반복적으로 많은 사람이 겪을수록 pain_score 높게

## actionable=true인 경우 필드:
- "category": 분야 (쇼핑몰운영, 회계세무, HR인사, 마케팅, 제조생산, IT개발, 교육, 부동산, 요식업, 물류배달, 의료, 금융, 프리랜서, 기타)
- "pain_summary": 핵심 문제를 한 문장으로 (제목이 아닌 실제 내용 기반)
- "pain_score": 1-100 (빈도 × 심각도 × 해결가능성)
- "solution_hint": 어떤 서비스가 해결할 수 있는지 한 문장

JSON 배열만 응답. 코드블록 없이. 설명 없이.

질문 목록:
"""
    for i, item in enumerate(items):
        prompt += f"\n[{i}] 제목: {item['title']}\n    내용: {item['description'][:200]}\n"

    result = call_openai(prompt)
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1]
        result = result.rsplit("```", 1)[0]
    return json.loads(result)

def classify(raw_items):
    batch_size = 10
    actionable = []

    for i in range(0, len(raw_items), batch_size):
        batch = raw_items[i:i+batch_size]
        print(f"  [분류] {i+1}-{min(i+batch_size, len(raw_items))}...")
        try:
            classified = classify_batch(batch)
            for j, c in enumerate(classified):
                idx = i + j
                if idx < len(raw_items) and c.get("actionable"):
                    item = raw_items[idx].copy()
                    item.update(c)
                    item["classified_at"] = datetime.now().isoformat()
                    actionable.append(item)
        except Exception as e:
            print(f"  [분류 ERROR] batch {i}: {e}")

    print(f"[분류] {len(actionable)}개 actionable")
    return actionable


# ========== 3단계: D1 업로드 ==========

def upload_to_d1(items):
    if not D1_API_URL or not D1_API_KEY:
        print("[업로드] D1_API_URL 또는 D1_API_KEY 미설정 — 스킵")
        return 0

    success = 0
    for item in items:
        try:
            body = json.dumps({
                "source": "naver_kin",
                "source_url": item["link"],
                "keyword": item.get("keyword", ""),
                "title": item["title"],
                "description": item.get("description", ""),
                "category": item.get("category", ""),
                "pain_summary": item.get("pain_summary", ""),
                "pain_score": item.get("pain_score", 0),
                "solution_hint": item.get("solution_hint", ""),
                "collected_at": item.get("collected_at", ""),
                "classified_at": item.get("classified_at", "")
            }).encode("utf-8")
            req = urllib.request.Request(D1_API_URL + "/api/pain", data=body, method="POST")
            req.add_header("Authorization", f"Bearer {D1_API_KEY}")
            req.add_header("Content-Type", "application/json")
            res = urllib.request.urlopen(req)
            result = json.loads(res.read().decode("utf-8"))
            if result.get("ok"):
                success += 1
        except Exception as e:
            pass  # 중복 등 무시

    print(f"[업로드] {success}/{len(items)}개 성공")
    return success


# ========== 메인 ==========

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*50}")
    print(f"DailyPain 파이프라인 — {today}")
    print(f"{'='*50}\n")

    # 1. 수집
    raw = collect()

    # 로컬 저장
    data_dir = os.path.join(PROJECT_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    with open(os.path.join(data_dir, f"{today}-raw.json"), "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    # 2. 분류
    actionable = classify(raw)

    with open(os.path.join(data_dir, f"{today}-classified.json"), "w", encoding="utf-8") as f:
        json.dump(actionable, f, ensure_ascii=False, indent=2)

    # 3. D1 업로드
    uploaded = upload_to_d1(actionable)

    # 4. 요약
    categories = {}
    for item in actionable:
        cat = item.get("category", "기타")
        categories[cat] = categories.get(cat, 0) + 1

    print(f"\n{'='*50}")
    print(f"완료: 수집 {len(raw)} → 분류 {len(actionable)} → 업로드 {uploaded}")
    print(f"카테고리 분포:")
    for cat, cnt in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {cnt}개")

    # 상위 5개 출력
    top5 = sorted(actionable, key=lambda x: x.get("pain_score", 0), reverse=True)[:5]
    print(f"\n--- 오늘의 TOP 5 ---")
    for i, r in enumerate(top5, 1):
        print(f"{i}. [{r.get('category','')}] {r.get('pain_summary','')}")
        print(f"   점수: {r.get('pain_score',0)} | {r['link']}")

if __name__ == "__main__":
    main()
