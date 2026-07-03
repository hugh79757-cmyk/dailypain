import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_DIR = _SCRIPT_DIR.parent

# .env 로드
load_dotenv(_PROJECT_DIR / ".env")

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
today = datetime.now().strftime("%Y-%m-%d")
data_dir = str(_PROJECT_DIR / "data")
log_path = os.path.join(data_dir, "dailypain.log")
os.makedirs(data_dir, exist_ok=True)
_log_handler = RotatingFileHandler(log_path, maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
_log_handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
_logger = logging.getLogger("dailypain")
_logger.setLevel(logging.INFO)
_logger.addHandler(_log_handler)
_logger.addHandler(logging.StreamHandler())

def log(msg):
    _logger.info(msg)

# ── 재시도 헬퍼 ──
def retry_with_backoff(fn, max_retries=3, base_delay=1):
    """Call fn() with exponential backoff. Re-raises last exception after max_retries."""
    for attempt in range(max_retries):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log(f"  [재시도 {attempt+1}/{max_retries}] 429 rate limited, waiting {delay}s...")
                time.sleep(delay)
                continue
            raise
        except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log(f"  [재시도 {attempt+1}/{max_retries}] network error: {e}, waiting {delay}s...")
                time.sleep(delay)
                continue
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                log(f"  [재시도 {attempt+1}/{max_retries}] {e}, waiting {delay}s...")
                time.sleep(delay)
                continue
            raise

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
    try:
        def fetch_naver():
            req = urllib.request.Request(url, headers={
                "X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret})
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode())
        data = retry_with_backoff(fetch_naver)
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
SYSTEM_PROMPT = (
    "너는 B2B SaaS 창업 기회 분석가다. 네이버 지식인 질문을 보고, "
    "**사업자/자영업자/직장인이 업무 중 겪는 반복적 고통**만 골라내라.\n\n"
    "반드시 제외: 개인 건강, 연애, 가족, 법률 상담, 게임, 학교 숙제, "
    "단순 정보 질문, 일회성 문제, 사업·업무 맥락 없는 질문.\n\n"
    "골라낼 것: 사업 운영 중 반복되는 불편, 소프트웨어로 자동화/개선 가능한 업무 고통, "
    "반복성 신호, 기존 도구의 한계를 호소하는 질문.\n\n"
    "JSON 배열로 응답:\n"
    '[{"index":0,"keep":true/false,'
    '"category":"세무회계|인사급여|재고물류|마케팅|고객관리|매장운영|쇼핑몰|부동산|교육|의료|건설|IT자동화|기타업무",'
    '"pain_summary":"구체적 고통 한 줄","pain_score":1-100,"solution_hint":"SaaS 아이디어 한 줄"}]\n'
    "keep=false 항목도 포함. 엄격하게 필터링."
)

def classify_batch(items, start_idx):
    batch_text = ""
    for i, item in enumerate(items):
        idx = start_idx + i
        batch_text += (
            f"[{idx}] 제목: {item['title'][:80]}\n"
            f"내용: {item['description'][:150]}\n"
            f"키워드: {item['keyword']}\n\n"
        )
    try:
        resp = retry_with_backoff(
            lambda: client.chat.completions.create(
                model="gpt-5-nano", reasoning_effort="minimal",
                messages=[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":batch_text}],
                response_format={"type":"json_object"},
                timeout=30))
        parsed = json.loads(resp.choices[0].message.content)
        if isinstance(parsed, dict):
            for key in parsed:
                if isinstance(parsed[key], list):
                    return parsed[key]
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
        if not isinstance(r, dict):
            log(f"  [분류 경고] 응답이 dict가 아님 (type={type(r).__name__}), 건너뜀")
            continue
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

# ── 3단계: HTTP 업로드 (Worker API) ──
def upload_via_worker(items):
    """POST each item to Worker /api/pain with Bearer auth."""
    api_url = os.environ.get("D1_API_URL", "").rstrip("/")
    api_key = os.environ.get("D1_API_KEY", "")
    if not api_url or not api_key:
        log("D1_API_URL 또는 D1_API_KEY 미설정 — 업로드 스킵")
        return 0

    success = 0
    for item in items[:50]:      # Same cap as before
        body = json.dumps({
            "date": today,
            "source": "naver_kin",
            "source_url": item.get("link", ""),
            "keyword": item.get("keyword", ""),
            "title": item.get("title", ""),
            "description": item.get("description", ""),
            "category": item.get("category", ""),
            "pain_summary": item.get("pain_summary", ""),
            "pain_score": item.get("pain_score", 0),
            "solution_hint": item.get("solution_hint", ""),
            "classified_at": datetime.now().isoformat()
        }).encode("utf-8")
        req = urllib.request.Request(f"{api_url}/api/pain", data=body, method="POST")
        req.add_header("Authorization", f"Bearer {api_key}")
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                if result.get("ok"):
                    success += 1
        except urllib.error.HTTPError as e:
            body_err = e.read().decode("utf-8", errors="replace")[:100]
            log(f"  [업로드 HTTP 오류] {e.code}: {body_err}")
        except Exception as e:
            log(f"  [업로드 오류] {e}")
    return success

uploaded = upload_via_worker(classified)
log(f"D1 업로드 완료: {uploaded}/{min(len(classified),50)}개")

log("=== 완료 ===\n")
