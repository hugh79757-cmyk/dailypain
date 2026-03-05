import os, json, time
from datetime import datetime
from openai import OpenAI

env_path = "/Users/twinssn/Projects/dailypain/.env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k] = v

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
today = datetime.now().strftime("%Y-%m-%d")

with open(f"/Users/twinssn/Projects/dailypain/data/{today}-raw-v2.json", encoding="utf-8") as f:
    raw = json.load(f)

print(f"원본: {len(raw)}개\n")

SYSTEM_PROMPT = """너는 B2B SaaS 창업 기회 분석가다. 
네이버 지식인 질문을 보고, **사업자/자영업자/직장인이 업무 중 겪는 반복적 고통**만 골라내라.

반드시 제외할 것:
- 개인 건강, 연애, 가족, 법률 상담, 게임, 학교 숙제
- 단순 정보 질문 ("~이 뭔가요?", "~어떻게 하나요?")
- 일회성 문제 (계정 복구, 기기 고장)
- 제목/내용에 사업·업무·운영 맥락이 전혀 없는 질문

골라낼 것:
- 사업 운영 중 반복되는 불편 (세금, 정산, 재고, 인사, 마케팅 등)
- 소프트웨어로 자동화/개선 가능한 업무 고통
- "매달/매주/매번" 같은 반복성 신호가 있는 문제
- 기존 도구(엑셀, 수기 등)의 한계를 호소하는 질문

각 항목에 대해 JSON 배열로 응답하라:
[
  {
    "index": 원본 인덱스(0부터),
    "keep": true/false,
    "category": "세무회계|인사급여|재고물류|마케팅|고객관리|매장운영|쇼핑몰|부동산|교육|의료|건설|IT자동화|기타업무",
    "pain_summary": "사업자가 겪는 구체적 고통 한 줄 (keep=false면 빈 문자열)",
    "pain_score": 1-100 (반복성, SaaS화 가능성, 지불의향 기준. keep=false면 0),
    "solution_hint": "SaaS 솔루션 아이디어 한 줄 (keep=false면 빈 문자열)"
  }
]

keep=false 항목도 반드시 배열에 포함하라. 엄격하게 필터링하라."""

def classify_batch(items, start_idx):
    batch_text = ""
    for i, item in enumerate(items):
        idx = start_idx + i
        batch_text += f"[{idx}] 제목: {item['title'][:80]}\n내용: {item['description'][:150]}\n키워드: {item['keyword']}\n\n"

    try:
        resp = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": batch_text}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        text = resp.choices[0].message.content
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    return parsed[key]
            return []
        return parsed
    except Exception as e:
        print(f"  [분류 오류] {e}")
        return []

BATCH = 15
all_classified = []
kept = 0

for i in range(0, len(raw), BATCH):
    batch = raw[i:i+BATCH]
    print(f"  분류 중... {i+1}-{i+len(batch)}")
    results = classify_batch(batch, i)
    for r in results:
        idx = r.get("index", 0)
        if r.get("keep") and 0 <= idx < len(raw):
            item = raw[idx]
            item.update({
                "category": r.get("category", ""),
                "pain_summary": r.get("pain_summary", ""),
                "pain_score": r.get("pain_score", 0),
                "solution_hint": r.get("solution_hint", ""),
                "is_actionable": True
            })
            all_classified.append(item)
            kept += 1
    time.sleep(0.5)

# pain_score 내림차순 정렬
all_classified.sort(key=lambda x: -x.get("pain_score", 0))

outpath = f"/Users/twinssn/Projects/dailypain/data/{today}-classified-v2.json"
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(all_classified, f, ensure_ascii=False, indent=2)

print(f"\n전체: {len(raw)}개")
print(f"B2B 페인포인트: {kept}개 ({kept*100//len(raw)}% 통과)")
print(f"저장: {outpath}")

# 카테고리 분포
cats = {}
for d in all_classified:
    c = d.get("category", "?")
    cats[c] = cats.get(c, 0) + 1
print(f"\n=== 카테고리 분포 ===")
for c, n in sorted(cats.items(), key=lambda x: -x[1]):
    print(f"  {c}: {n}개")

# 상위 10개
print(f"\n=== 상위 10개 ===")
for i, d in enumerate(all_classified[:10], 1):
    print(f"\n{i}. [{d['category']}] 점수:{d['pain_score']}")
    print(f"   문제: {d['pain_summary']}")
    print(f"   힌트: {d['solution_hint']}")
    print(f"   원문: {d['link']}")
