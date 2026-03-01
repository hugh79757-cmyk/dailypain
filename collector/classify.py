import os
import json
import urllib.request
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

env_vars = {}
with open(os.path.join(PROJECT_DIR, ".env")) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env_vars[k] = v

OPENAI_KEY = env_vars.get("OPENAI_API_KEY", "")

def call_openai(prompt, model="gpt-4o-mini"):
    url = "https://api.openai.com/v1/chat/completions"
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }).encode("utf-8")
    req = urllib.request.Request(url, data=body)
    req.add_header("Authorization", f"Bearer {OPENAI_KEY}")
    req.add_header("Content-Type", "application/json")
    res = urllib.request.urlopen(req)
    data = json.loads(res.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]

def classify_batch(items):
    prompt = """아래는 네이버 지식인에서 수집한 질문 목록이다.
각 질문을 분석해서 JSON 배열로 응답해라.

판단 기준:
- "actionable": true = 소프트웨어/서비스/자동화로 해결 가능한 비즈니스 페인포인트
- "actionable": false = 개인 고민, 건강, 연애, 일상 질문 등 서비스화 불가능

actionable이 true인 경우만 아래 필드를 채워라:
- "category": 업종/분야 (예: 쇼핑몰, 회계, HR, 마케팅, 제조, IT, 교육 등)
- "pain_summary": 핵심 페인포인트를 한 문장으로 요약
- "solution_hint": 어떤 종류의 서비스가 해결할 수 있는지 한 문장

JSON 배열만 응답. 설명 없이.

질문 목록:
"""
    for i, item in enumerate(items):
        prompt += f"\n[{i}] 제목: {item['title']}\n    내용: {item['description'][:150]}\n"

    result = call_openai(prompt)
    result = result.strip()
    if result.startswith("```"):
        result = result.split("\n", 1)[1]
        result = result.rsplit("```", 1)[0]
    return json.loads(result)

def main():
    today = datetime.now().strftime("%Y-%m-%d")
    raw_path = os.path.join(PROJECT_DIR, "data", f"{today}-raw.json")

    with open(raw_path, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"원본: {len(raw)}개")

    # 10개씩 배치 처리
    batch_size = 10
    all_classified = []

    for i in range(0, len(raw), batch_size):
        batch = raw[i:i+batch_size]
        print(f"분류 중... {i+1}-{min(i+batch_size, len(raw))}")
        try:
            classified = classify_batch(batch)
            for j, c in enumerate(classified):
                idx = i + j
                if idx < len(raw):
                    raw[idx].update(c)
                    all_classified.append(raw[idx])
        except Exception as e:
            print(f"  [ERROR] batch {i}: {e}")

    actionable = [x for x in all_classified if x.get("actionable")]
    print(f"\n전체: {len(all_classified)}개")
    print(f"비즈니스 페인포인트: {len(actionable)}개")

    output_path = os.path.join(PROJECT_DIR, "data", f"{today}-classified.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(actionable, f, ensure_ascii=False, indent=2)
    print(f"저장: {output_path}")

    print(f"\n--- 상위 5개 ---")
    for r in actionable[:5]:
        print(f"[{r.get('category','')}] {r['title']}")
        print(f"  페인포인트: {r.get('pain_summary','')}")
        print(f"  솔루션 힌트: {r.get('solution_hint','')}")
        print(f"  원문: {r['link']}")
        print()

if __name__ == "__main__":
    main()
