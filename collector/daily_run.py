import os, json, time, hashlib, subprocess, urllib.request, urllib.parse
from datetime import datetime
from openai import OpenAI

# .env 로드
env_path = "/Users/twinssn/Projects/dailypain/.env"
with open(env_path) as f:
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k] = v

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
today = datetime.now().strftime("%Y-%m-%d")
data_dir = "/Users/twinssn/Projects/dailypain/data"
log_path = os.path.join(data_dir, "dailypain.log")
os.makedirs(data_dir, exist_ok=True)

def log(msg):
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ── 1단계: 키워드 수집 ──
keywords = [
    "사업자 세금 신고 어려워","부가세 신고 복잡","종합소득세 힘들어",
    "전자세금계산서 발행 실수","사업자 장부 정리","매출 정산 자동화",
    "직원 급여 계산 어려워","4대보험 처리 복잡","퇴직금 계산 방법",
    "온라인 쇼핑몰 관리 힘들어","스마트스토어 주문 관리","쇼핑몰 재고 관리 어려워",
    "매장 포스 시스템 불편","배달앱 정산 복잡","식당 재료 관리",
    "거래처 관리 엑셀 한계","고객 관리 프로그램","CRM 추천",
    "사업자 마케팅 어려워","블로그 마케팅 자동화","SNS 마케팅 비용",
    "소상공인 지원금 신청 복잡","정책자금 서류 많아","창업 지원 프로그램",
    "엑셀 재고 관리 한계","물류 배송 추적","발주 자동화",
    "건설 현장 관리 어려워","공사 일보 작성","건설 인력 관리",
    "병원 예약 관리 불편","의료 차트 전산화","환자 관리 프로그램",
    "학원 관리 프로그램","수강생 관리 어려워","교육 출결 관리",
    "반복 업무 자동화 방법","업무 효율 프로그램 추천","사무 자동화 도구",
    "프리랜서 세금 신고","1인 사업자 경비 처리","간이과세자 부가세"
]

log(f"=== DailyPain 수집 시작 ({today}) ===")
log(f"키워드: {len(keywords)}개")

naver_id = os.environ["NAVER_CLIENT_ID"]
naver_secret = os.environ["NAVER_CLIENT_SECRET"]
seen = set()
raw = []

for kw in keywords:
    params = urllib.parse.urlencode({"query": kw, "display": 10, "sort": "date"})
    url = f"https://openapi.naver.com/v1/search/kin.json?{params}"
    req = urllib.request.Request(url, headers={"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret})
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for item in data.get("items", []):
                uid = hashlib.md5(item["link"].encode()).hexdigest()
                if uid not in seen:
                    seen.add(uid)
                    raw.append({"keyword": kw, "title": item["title"].replace("<b>","").replace("</b>",""),
                                "description": item["description"].replace("<b>","").replace("</b>",""),
                                "link": item["link"], "collected_at": datetime.now().isoformat()})
    except Exception as e:
        log(f"  [수집 오류] {kw}: {e}")
    time.sleep(0.15)

raw_path = f"{data_dir}/{today}-raw.json"
with open(raw_path, "w", encoding="utf-8") as f:
    json.dump(raw, f, ensure_ascii=False, indent=2)
log(f"수집 완료: {len(raw)}개")

# ── 2단계: AI 분류 ──
SYSTEM_PROMPT = """너는 B2B SaaS 창업 기회 분석가다. 네이버 지식인 질문을 보고, **사업자/자영업자/직장인이 업무 중 겪는 반복적 고통**만 골라내라.

반드시 제외: 개인 건강, 연애, 가족, 법률 상담, 게임, 학교 숙제, 단순 정보 질문, 일회성 문제, 사업·업무 맥락 없는 질문.

골라낼 것: 사업 운영 중 반복되는 불편, 소프트웨어로 자동화/개선 가능한 업무 고통, 반복성 신호, 기존 도구의 한계를 호소하는 질문.

JSON 배열로 응답:
[{"index":0,"keep":true/false,"category":"세무회계|인사급여|재고물류|마케팅|고객관리|매장운영|쇼핑몰|부동산|교육|의료|건설|IT자동화|기타업무","pain_summary":"구체적 고통 한 줄","pain_score":1-100,"solution_hint":"SaaS 아이디어 한 줄"}]
keep=false 항목도 포함. 엄격하게 필터링."""

def classify_batch(items, start_idx):
    batch_text = ""
    for i, item in enumerate(items):
        idx = start_idx + i
        batch_text += f"[{idx}] 제목: {item['title'][:80]}\n내용: {item['description'][:150]}\n키워드: {item['keyword']}\n\n"
    try:
        resp = client.chat.completions.create(
            model="gpt-5-nano", reasoning_effort="minimal",
            messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":batch_text}],
            response_format={"type":"json_object"})
        parsed = json.loads(resp.choices[0].message.content)
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list): return parsed[key]
            return []
        return parsed
    except Exception as e:
        log(f"  [분류 오류] {e}")
        return []

classified = []
for i in range(0, len(raw), 15):
    batch = raw[i:i+15]
    log(f"  분류 중... {i+1}-{i+len(batch)}/{len(raw)}")
    results = classify_batch(batch, i)
    for r in results:
        idx = r.get("index", 0)
        if r.get("keep") and 0 <= idx < len(raw):
            item = raw[idx].copy()
            item.update({"category": r.get("category",""), "pain_summary": r.get("pain_summary",""),
                         "pain_score": r.get("pain_score",0), "solution_hint": r.get("solution_hint","")})
            classified.append(item)
    time.sleep(0.5)

classified.sort(key=lambda x: -x.get("pain_score", 0))
cls_path = f"{data_dir}/{today}-classified.json"
with open(cls_path, "w", encoding="utf-8") as f:
    json.dump(classified, f, ensure_ascii=False, indent=2)
log(f"B2B 페인포인트: {len(classified)}개 ({len(classified)*100//max(len(raw),1)}% 통과)")

# ── 3단계: SQL 파일 생성 + wrangler로 D1 업로드 ──
def esc(s):
    return str(s).replace("'", "''")[:200] if s else ""

lines = []
for item in classified[:50]:
    sql = (
        f"INSERT OR IGNORE INTO pain_points (date, source, source_url, keyword, title, description, "
        f"category, pain_summary, pain_score, solution_hint, is_actionable, collected_at, classified_at) "
        f"VALUES ('{today}', 'naver_kin', '{esc(item.get('link',''))}', '{esc(item.get('keyword',''))}', "
        f"'{esc(item.get('title',''))}', '{esc(item.get('description',''))}', "
        f"'{esc(item.get('category',''))}', '{esc(item.get('pain_summary',''))}', "
        f"{item.get('pain_score', 0)}, '{esc(item.get('solution_hint',''))}', "
        f"1, '{item.get('collected_at','')}', '{datetime.now().isoformat()}');"
    )
    lines.append(sql)

sql_path = f"{data_dir}/{today}-upload.sql"
with open(sql_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
log(f"SQL 파일 생성: {len(lines)}개 INSERT문")

# wrangler로 업로드
env = os.environ.copy()
env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH","")
result = subprocess.run(
    ["npx", "wrangler", "d1", "execute", "dailypain-db", "--remote", f"--file={sql_path}"],
    cwd="/Users/twinssn/Projects/dailypain/workers",
    capture_output=True, text=True, env=env, timeout=120
)

if result.returncode == 0:
    log(f"D1 업로드 완료: {len(lines)}개")
else:
    log(f"D1 업로드 실패: {result.stderr[:200]}")

log(f"=== 완료 ===\n")
