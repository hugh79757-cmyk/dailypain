import pytest


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Set required env vars for all tests to avoid KeyError."""
    monkeypatch.setenv("NAVER_CLIENT_ID", "test_id")
    monkeypatch.setenv("NAVER_CLIENT_SECRET", "test_secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key")
    monkeypatch.setenv("D1_API_URL", "http://test.api")
    monkeypatch.setenv("D1_API_KEY", "test_key")


@pytest.fixture
def sample_raw_items():
    """3 sample Naver KIN items (as collected by daily_run.py)."""
    return [
        {"keyword": "세금 신고", "title": "부가세 신고 방법", "description": "사업자 부가세 신고가 너무 복잡해요", "link": "https://kin.naver.com/q1", "collected_at": "2026-01-01T00:00:00"},  # noqa: E501
        {"keyword": "재고 관리", "title": "재고 정리 팁", "description": "쇼핑몰 재고 관리가 너무 어려워요", "link": "https://kin.naver.com/q2", "collected_at": "2026-01-01T00:00:00"},  # noqa: E501
        {"keyword": "개인 건강", "title": "두통 없애는 법", "description": "두통이 심해요", "link": "https://kin.naver.com/q3", "collected_at": "2026-01-01T00:00:00"},  # noqa: E501
    ]


@pytest.fixture
def sample_openai_response_valid():
    """Simulates a valid OpenAI response (dict with list in a key)."""
    return {
        "choices": [
            {
                "message": {
                    "content": '[{"index":0,"keep":true,"category":"세무회계","pain_summary":"부가세 신고 복잡","pain_score":85,"solution_hint":"자동 신고 서비스"},{"index":1,"keep":true,"category":"쇼핑몰","pain_summary":"재고 관리 어려움","pain_score":70,"solution_hint":"재고 관리 SaaS"},{"index":2,"keep":false,"category":"기타","pain_summary":"","pain_score":0,"solution_hint":""}]'  # noqa: E501
                }
            }
        ]
    }


@pytest.fixture
def sample_openai_response_direct_list():
    """OpenAI returns a top-level list instead of dict-wrapped."""
    return {
        "choices": [
            {
                "message": {
                    "content": '[{"index":0,"keep":true,"category":"세무회계","pain_summary":"","pain_score":80,"solution_hint":""}]'  # noqa: E501
                }
            }
        ]
    }


@pytest.fixture
def sample_openai_response_string_list():
    """OpenAI returns list of strings instead of list of dicts (the crash scenario)."""
    return {
        "choices": [
            {
                "message": {
                    "content": '["문자열 응답", "또 다른 문자열"]'
                }
            }
        ]
    }
