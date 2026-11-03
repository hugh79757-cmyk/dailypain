"""Threads 수집기 (B안: 브라우저 자동화). 공개 페이지만, 운영 계정 로그인 금지.
"""
import json, time


def filter_korean(posts):
    out = []
    for p in posts:
        t = p.get("text", "")
        # 간단 한국어 판별: 한글 비율
        kr = sum(1 for c in t if "\uac00" <= c <= "\ud7a3")
        if len(t) == 0:
            continue
        if kr / max(len(t), 1) < 0.3:
            continue
        out.append(p)
    return out


import hashlib


def _dedup_key(p):
    if p.get("post_id"):
        return ("id", p["post_id"])
    if p.get("permalink"):
        return ("url", p["permalink"])
    t = (p.get("text") or "").strip()
    if t:
        return ("hash", hashlib.sha256(t.encode()).hexdigest())
    return None


def dedup(posts):
    seen = set()
    out = []
    for p in posts:
        key = _dedup_key(p)
        if key is None:
            # 대체 키도 없으면 dedup 대상에서 제외(보존)
            out.append(p)
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


# 홍보성 문구 패턴(부분문자열 "광고"만으로는 불만 글까지 잘리므로 좁힘)
PROMO_PATTERNS = ["구매 링크", "할인 코드", "업체 홍보", "프로모션 코드", "affiliate"]


def exclude_policy(posts):
    out = []
    for p in posts:
        t = p.get("text", "")
        if any(k in t for k in ["스팸"]):
            continue
        # 정치/흉악범죄·잔인
        if any(k in t for k in ["정치", "살인", "잔인"]):
            continue
        # 홍보성 문구 패턴만 제외 (광고 불만 글은 유지)
        if any(pat in t for pat in PROMO_PATTERNS):
            continue
        out.append(p)
    return out
