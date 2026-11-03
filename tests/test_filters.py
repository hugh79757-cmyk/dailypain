import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "collector"))
from threads_collector import dedup, exclude_policy, filter_korean

def test_none_post_id_not_collapsed():
    posts = [
        {"post_id": None, "author": "a", "text": "첫번째 글", "permalink": "u1"},
        {"post_id": None, "author": "b", "text": "두번째 글", "permalink": "u2"},
    ]
    assert len(dedup(posts)) == 2

def test_ad_complaint_not_excluded():
    posts = [{"text": "광고가 너무 많아서 짜증나"}]
    assert len(exclude_policy(posts)) == 1

def test_promo_excluded():
    posts = [{"text": "구매 링크 여기 할인 코드"}]
    assert len(exclude_policy(posts)) == 0