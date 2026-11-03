"""DailyPain Threads 고통 채점/군집/힌트 (DAILYPAIN-THREADS-01 작업 4).

Llama API 연동. 엔드포인트·키는 환경변수 LLAMA_API_URL / LLAMA_API_KEY 로만
주입한다. 키 값은 파일·로그에 기록하지 않는다.
"""
import os
import json
import urllib.request

LLAMA_API_URL = os.getenv("LLAMA_API_URL", "")
LLAMA_API_KEY = os.getenv("LLAMA_API_KEY", "")

# 채점 축 가중치 (합 1.0)
WEIGHTS = {
    "intensity": 0.35,     # 고통 강도(감정 강도)
    "universality": 0.25,  # 보편성(같은 고통 반복 빈도)
    "specificity": 0.20,   # 구체성(막연한 푸념 vs 특정 대상)
    "solvability": 0.20,   # 해결 가능성
}

PROMPT = """다음 한국어 Threads 포스트를 분석해 JSON으로만 답하라.
포스트: {text}

출력 스키마:
{{
  "pain_summary": "한 줄 요약",
  "intensity": 0-100,
  "universality": 0-100,
  "specificity": 0-100,
  "solvability": 0-100,
  "category": "카테고리",
  "solution_hint": "검증되지 않은 단정(가격·효과) 없이 해결 힌트 한 줄"
}}"""


def score_post(text: str) -> dict:
    """실패 시 fail-open: 원문만 저장, 파이프라인 계속."""
    if not LLAMA_API_URL or not LLAMA_API_KEY:
        return {"pain_summary": text[:80], "pain_score": 0,
                "intensity": 0, "universality": 0, "specificity": 0,
                "solvability": 0, "category": "", "solution_hint": "",
                "llama_ok": False}
    try:
        body = json.dumps({"prompt": PROMPT.format(text=text)}).encode()
        req = urllib.request.Request(LLAMA_API_URL, data=body,
                                    headers={"Authorization": f"Bearer {LLAMA_API_KEY}",
                                             "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
        raw = data.get("text", data.get("response", "{}"))
        # 마크다운 펜스 제거
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
        ps = (parsed["intensity"] * WEIGHTS["intensity"]
              + parsed["universality"] * WEIGHTS["universality"]
              + parsed["specificity"] * WEIGHTS["specificity"]
              + parsed["solvability"] * WEIGHTS["solvability"])
        parsed["pain_score"] = int(ps)
        parsed["llama_ok"] = True
        return parsed
    except Exception:
        # fail-open
        return {"pain_summary": text[:80], "pain_score": 0,
                "intensity": 0, "universality": 0, "specificity": 0,
                "solvability": 0, "category": "", "solution_hint": "",
                "llama_ok": False}


def cluster(posts: list) -> list:
    """같은 주제 군집 대표 1건. pain_score는 구성원 중 최대값."""
    groups = {}
    for p in posts:
        key = p.get("category") or (p.get("text") or "")[:40]
        groups.setdefault(key, []).append(p)
    out = []
    for key, members in groups.items():
        rep = max(members, key=lambda m: m.get("pain_score", 0))
        rep = dict(rep)
        rep["pain_score"] = max(m.get("pain_score", 0) for m in members)
        rep["cluster_size"] = len(members)
        out.append(rep)
    return out
