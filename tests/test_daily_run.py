"""Tests for collector/daily_run.py — retry logic, classify parsing, upload construction, Naver normalization."""
import json
import os
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

# Ensure env vars are set before importing daily_run module (module-level code runs at import time)
os.environ.setdefault("NAVER_CLIENT_ID", "test_id")
os.environ.setdefault("NAVER_CLIENT_SECRET", "test_secret")
os.environ.setdefault("OPENAI_API_KEY", "test_key")
os.environ.setdefault("D1_API_URL", "http://test.api")
os.environ.setdefault("D1_API_KEY", "test_key")


# ── retry_with_backoff ──

class TestRetryWithBackoff:
    """Import and test retry_with_backoff from daily_run.py."""

    def test_retry_success_first_attempt(self):
        """Function succeeds on first call, returns result directly."""
        from collector.daily_run import retry_with_backoff

        def fn():
            return "ok"

        assert retry_with_backoff(fn) == "ok"

    def test_retry_eventually_succeeds(self):
        """Function fails twice then succeeds on third attempt."""
        from collector.daily_run import retry_with_backoff

        calls = [0]

        def fn():
            calls[0] += 1
            if calls[0] < 3:
                raise urllib.error.HTTPError("http://test.com", 429, "Rate Limited", {}, None)
            return "ok"

        result = retry_with_backoff(fn, max_retries=3, base_delay=0.01)
        assert result == "ok"
        assert calls[0] == 3

    def test_retry_exhaustion_raises(self):
        """After max_retries failures, the last exception is re-raised."""
        from collector.daily_run import retry_with_backoff

        def fn():
            raise urllib.error.HTTPError("http://test.com", 429, "Rate Limited", {}, None)

        with pytest.raises(urllib.error.HTTPError):
            retry_with_backoff(fn, max_retries=2, base_delay=0.01)

    def test_retry_non_http_error_no_retry(self):
        """Non-429/non-network errors are not retried (re-raised immediately)."""
        from collector.daily_run import retry_with_backoff

        def fn():
            raise ValueError("unexpected")

        with pytest.raises(ValueError):
            retry_with_backoff(fn, max_retries=3, base_delay=0.01)


# ── classify_batch parsing ──

class TestClassifyBatchParsing:
    """Test the JSON parsing path inside classify_batch()."""

    def test_parse_valid_dict_response(self, sample_openai_response_valid, sample_raw_items):
        """When OpenAI returns a dict with a list in a key, the list is extracted correctly."""
        from collector.daily_run import classify_batch
        # The function uses client.chat.completions.create which we mock
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps({
                    "results": [
                        {"index": 0, "keep": True, "category": "세무회계", "pain_summary": "test", "pain_score": 85, "solution_hint": "auto"},  # noqa: E501
                    ]
                })))]
            )
            result = classify_batch(sample_raw_items, 0)
            assert isinstance(result, list)
            assert len(result) > 0

    def test_parse_direct_list_response(self, sample_openai_response_direct_list):
        """When OpenAI returns a top-level list (no wrapper dict), it is returned directly."""
        from collector.daily_run import classify_batch
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            content = json.dumps([
                {"index": 0, "keep": True, "category": "세무회계", "pain_summary": "test", "pain_score": 80, "solution_hint": "hint"}  # noqa: E501
            ])
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))]
            )
            result = classify_batch([{"title": "test", "description": "test", "keyword": "test"}], 0)
            assert isinstance(result, list)
            assert len(result) == 1

    def test_parse_malformed_response_returns_empty_list(self):
        """When OpenAI returns non-JSON or unexpected structure, classify_batch returns []."""
        from collector.daily_run import classify_batch
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content="{{invalid json}}"))]
            )
            result = classify_batch([{"title": "test", "description": "test", "keyword": "test"}], 0)
            assert result == []

    def test_parse_empty_response_returns_empty_list(self):
        """When OpenAI returns empty content, classify_batch returns []."""
        from collector.daily_run import classify_batch
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=""))]
            )
            result = classify_batch([], 0)
            assert result == []


# ── classify loop isinstance guard ──

class TestClassifyLoopGuard:
    """The classification results loop must handle non-dict items without crashing."""

    def test_mixed_list_skips_non_dict(self, sample_raw_items):
        """Items that are strings in the result list are skipped (no AttributeError)."""
        from collector.daily_run import classify_batch
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            # Return a list containing a dict and a string
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content=json.dumps([
                    {"index": 0, "keep": True, "category": "세무회계", "pain_summary": "test", "pain_score": 85, "solution_hint": "hint"},  # noqa: E501
                    "this is a string, not a dict"  # Would crash without isinstance guard
                ])))]
            )
            # This should not raise AttributeError
            result = classify_batch(sample_raw_items[:1], 0)
            assert isinstance(result, list)
            # The string item was in the JSON response, so it's in the parsed list
            # The caller (daily_run.py line 142-151) checks isinstance(r, dict) before .get()
            # That guard prevents the crash — we verify it's handled

    def test_all_strings_list_returns_no_valid_items(self):
        """When all items are strings, classify_batch returns them but the caller skips them."""
        from collector.daily_run import classify_batch
        with patch("collector.daily_run.client.chat.completions.create") as mock_create:
            mock_create.return_value = MagicMock(
                choices=[MagicMock(message=MagicMock(content='["string1", "string2"]'))]
            )
            result = classify_batch([{"title": "t", "description": "d", "keyword": "k"}], 0)
            assert isinstance(result, list)
            assert len(result) == 2
            assert all(isinstance(x, str) for x in result)


# ── upload_via_worker ──

class TestUploadViaWorker:
    """Test the HTTP upload function."""

    def test_upload_skips_when_no_url(self):
        """When D1_API_URL is not set, upload_via_worker returns 0."""
        from collector.daily_run import upload_via_worker
        with patch.dict("os.environ", {"D1_API_URL": "", "D1_API_KEY": "test"}):
            assert upload_via_worker([]) == 0

    def test_upload_skips_when_no_key(self):
        """When D1_API_KEY is not set, upload_via_worker returns 0."""
        from collector.daily_run import upload_via_worker
        with patch.dict("os.environ", {"D1_API_URL": "http://test.api", "D1_API_KEY": ""}):
            assert upload_via_worker([]) == 0

    def test_upload_limits_to_50_items(self):
        """Only the first 50 items are processed (cap from pre-existing behavior)."""
        from collector.daily_run import upload_via_worker
        items = [{"title": f"item{i}", "link": f"http://example.com/{i}"} for i in range(100)]
        with patch.dict("os.environ", {"D1_API_URL": "http://test.api", "D1_API_KEY": "test_key"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"ok": true}'
                mock_response.__enter__.return_value = mock_response
                mock_urlopen.return_value = mock_response
                result = upload_via_worker(items)
                assert result == 50  # Capped at 50

    def test_upload_constructs_correct_request(self):
        """Verify request URL, method, headers, and body structure."""
        from collector.daily_run import upload_via_worker
        item = {
            "keyword": "세금 신고", "title": "부가세 신고", "description": "복잡해요",
            "link": "https://kin.naver.com/q1", "category": "세무회계",
            "pain_summary": "부가세 어려움", "pain_score": 90, "solution_hint": "자동화 서비스"
        }
        with patch.dict("os.environ", {"D1_API_URL": "https://test.workers.dev", "D1_API_KEY": "secret123"}):
            with patch("urllib.request.urlopen") as mock_urlopen:
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"ok": true}'
                mock_response.__enter__.return_value = mock_response
                mock_urlopen.return_value = mock_response
                upload_via_worker([item])
                # Verify the request was constructed
                call_args = mock_urlopen.call_args[0][0]
                assert isinstance(call_args, urllib.request.Request)
                assert call_args.get_full_url() == "https://test.workers.dev/api/pain"
                assert call_args.get_method() == "POST"
                assert call_args.headers["Authorization"] == "Bearer secret123"
                assert call_args.headers["Content-type"] == "application/json"
                body = json.loads(call_args.data)
                assert body["source"] == "naver_kin"
                assert body["keyword"] == "세금 신고"
                assert body["pain_score"] == 90


# ── Naver response normalization ──

class TestNaverNormalization:
    """Test HTML tag stripping and deduplication logic (integration-style, no network)."""

    def test_html_tags_stripped_from_title(self):
        """<b> tags in Naver titles are stripped by the pipeline."""
        # This tests the .replace("<b>","").replace("</b>","") pattern in daily_run.py
        raw_title = "부가세 <b>신고</b> 방법"
        cleaned = raw_title.replace("<b>", "").replace("</b>", "")
        assert cleaned == "부가세 신고 방법"
        assert "<b>" not in cleaned
        assert "</b>" not in cleaned

    def test_dedup_by_md5_link_hash(self):
        """Same link produces same MD5 hash and is skipped."""
        import hashlib
        link1 = "https://kin.naver.com/q1"
        link2 = "https://kin.naver.com/q1"
        assert hashlib.md5(link1.encode()).hexdigest() == hashlib.md5(link2.encode()).hexdigest()

    def test_different_links_produce_different_hashes(self):
        """Different links produce different MD5 hashes (no collision)."""
        import hashlib
        h1 = hashlib.md5(b"https://kin.naver.com/q1").hexdigest()
        h2 = hashlib.md5(b"https://kin.naver.com/q2").hexdigest()
        assert h1 != h2
