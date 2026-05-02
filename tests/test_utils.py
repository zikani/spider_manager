"""Unit tests for utils.* modules."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from utils import file_utils, mime_detector, network_utils, url_parser


# ---------------------------------------------------------------- file_utils


class TestSanitizeFilename:
    def test_empty_returns_default(self):
        assert file_utils.sanitize_filename("") == "download"

    def test_strips_illegal_chars(self):
        assert file_utils.sanitize_filename('a<b>c:d"e/f\\g|h?i*j.txt') == "a_b_c_d_e_f_g_h_i_j.txt"

    def test_strips_control_chars(self):
        assert file_utils.sanitize_filename("a\x00b\x1fc.bin") == "a_b_c.bin"

    def test_trims_trailing_dots_and_spaces(self):
        assert file_utils.sanitize_filename("file.txt.  ") == "file.txt"

    def test_reserved_basename_prefixed(self):
        assert file_utils.sanitize_filename("CON.txt").startswith("_")
        assert file_utils.sanitize_filename("nul").startswith("_")
        assert file_utils.sanitize_filename("LPT1").startswith("_")

    def test_truncates_to_max_length_keeping_ext(self):
        long_stem = "a" * 300
        out = file_utils.sanitize_filename(f"{long_stem}.zip", max_length=50)
        assert len(out) <= 50
        assert out.endswith(".zip")

    def test_only_dots_and_spaces_falls_back(self):
        assert file_utils.sanitize_filename("   ...   ") == "download"

    def test_only_illegal_chars_replaces_them(self):
        out = file_utils.sanitize_filename("////")
        assert "/" not in out and "\\" not in out
        assert out


class TestUniquePath:
    def test_returns_same_when_no_collision(self, tmp_path: Path):
        assert file_utils.unique_path(tmp_path, "x.txt") == str(tmp_path / "x.txt")

    def test_appends_counter_on_collision(self, tmp_path: Path):
        (tmp_path / "x.txt").write_text("a")
        result = file_utils.unique_path(tmp_path, "x.txt")
        assert result == str(tmp_path / "x (1).txt")

    def test_increments_until_free(self, tmp_path: Path):
        (tmp_path / "x.txt").write_text("a")
        (tmp_path / "x (1).txt").write_text("a")
        (tmp_path / "x (2).txt").write_text("a")
        result = file_utils.unique_path(tmp_path, "x.txt")
        assert result == str(tmp_path / "x (3).txt")


class TestDiskHelpers:
    def test_get_free_space_returns_positive(self, tmp_path: Path):
        assert file_utils.get_free_space(tmp_path) > 0

    def test_get_free_space_walks_to_existing_ancestor(self, tmp_path: Path):
        nonexistent = tmp_path / "does" / "not" / "exist"
        assert file_utils.get_free_space(nonexistent) > 0

    def test_ensure_directory_creates(self, tmp_path: Path):
        target = tmp_path / "a" / "b" / "c"
        file_utils.ensure_directory(target)
        assert target.is_dir()
        file_utils.ensure_directory(target)

    def test_format_size(self):
        assert file_utils.format_size(0) == "0 Bytes"
        assert "KiB" in file_utils.format_size(2048) or "B" in file_utils.format_size(2048)


# -------------------------------------------------------------- mime_detector


class TestMimeDetector:
    @pytest.mark.parametrize(
        "ct,expected",
        [
            ("video/mp4", "Video"),
            ("audio/mpeg", "Audio"),
            ("image/png", "Image"),
            ("application/pdf", "Document"),
            ("application/zip", "Archive"),
            ("application/x-msdownload", "Program"),
            ("text/plain", "Document"),
            ("application/octet-stream", None),
            ("", None),
            ("garbage", None),
        ],
    )
    def test_category_for_mime(self, ct, expected):
        assert mime_detector.category_for_mime(ct) == expected

    def test_category_handles_charset_param(self):
        assert mime_detector.category_for_mime("text/plain; charset=utf-8") == "Document"

    def test_metadata_filename_wins_over_unknown_mime(self):
        assert mime_detector.category_from_metadata("song.mp3", "application/octet-stream") == "Audio"

    def test_metadata_falls_back_to_mime_when_extension_unknown(self):
        assert mime_detector.category_from_metadata("noext", "video/webm") == "Video"

    def test_metadata_returns_other_when_nothing_matches(self):
        assert mime_detector.category_from_metadata("noext", None) == "Other"
        assert mime_detector.category_from_metadata("noext", "garbage/garbage") == "Other"

    def test_extension_from_mime(self):
        assert mime_detector.extension_from_mime("video/mp4") == ".mp4"
        assert mime_detector.extension_from_mime("application/pdf") == ".pdf"
        assert mime_detector.extension_from_mime("garbage/garbage") == ""
        assert mime_detector.extension_from_mime("") == ""


# ---------------------------------------------------------------- url_parser


class TestUrlParser:
    def test_is_valid_url_accepts_http_https(self):
        assert url_parser.is_valid_url("http://example.com/x")
        assert url_parser.is_valid_url("https://example.com/x")
        assert url_parser.is_valid_url("example.com/x")  # auto-prefixed

    def test_is_valid_url_rejects_unsupported_or_empty(self):
        assert not url_parser.is_valid_url("ftp://example.com/x")
        assert not url_parser.is_valid_url("")
        assert not url_parser.is_valid_url("https://")

    def test_extract_filename_from_url_path(self):
        assert url_parser.extract_filename("https://example.com/path/file.zip") == "file.zip"

    def test_extract_filename_strips_query(self):
        assert url_parser.extract_filename("https://example.com/x/file.zip?token=abc") == "file.zip"

    def test_extract_filename_percent_decoded(self):
        assert url_parser.extract_filename("https://example.com/my%20file.zip") == "my file.zip"

    def test_extract_filename_from_content_disposition_quoted(self):
        headers = {"Content-Disposition": 'attachment; filename="cool.zip"'}
        assert url_parser.extract_filename("https://example.com/", headers) == "cool.zip"

    def test_extract_filename_from_content_disposition_bare(self):
        headers = {"Content-Disposition": "attachment; filename=cool.zip"}
        assert url_parser.extract_filename("https://example.com/", headers) == "cool.zip"

    def test_extract_filename_rfc5987(self):
        headers = {"Content-Disposition": "attachment; filename*=UTF-8''r%C3%A9sum%C3%A9.pdf"}
        result = url_parser.extract_filename("https://example.com/", headers)
        assert result == "résumé.pdf"

    def test_extract_filename_falls_back_to_default(self):
        assert url_parser.extract_filename("https://example.com/") == "download"

    def test_safe_filename_sanitizes(self):
        headers = {"Content-Disposition": 'attachment; filename="bad<name>.zip"'}
        result = url_parser.safe_filename_from_url("https://example.com/", headers)
        assert "<" not in result and ">" not in result
        assert result.endswith(".zip")


# ------------------------------------------------------------ network_utils


class TestNetworkUtils:
    def test_build_proxy_url_basic(self):
        assert network_utils.build_proxy_url("p.example.com", 8080) == "http://p.example.com:8080"

    def test_build_proxy_url_with_auth(self):
        url = network_utils.build_proxy_url("p.example.com", 8080, "alice", "s3cret")
        assert url == "http://alice:s3cret@p.example.com:8080"

    def test_build_proxy_url_user_only(self):
        url = network_utils.build_proxy_url("p.example.com", 8080, "alice")
        assert url == "http://alice@p.example.com:8080"

    def test_build_proxy_url_quotes_special_chars(self):
        url = network_utils.build_proxy_url("p.example.com", 8080, "user@x", "p:w")
        assert "user%40x" in url
        assert "p%3Aw" in url

    def test_build_proxy_url_empty_host(self):
        assert network_utils.build_proxy_url("", 8080) is None

    def test_build_proxy_url_no_port(self):
        assert network_utils.build_proxy_url("p.example.com", 0) == "http://p.example.com"

    def test_system_proxy_reads_env(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
        monkeypatch.delenv("https_proxy", raising=False)
        monkeypatch.delenv("HTTP_PROXY", raising=False)
        monkeypatch.delenv("http_proxy", raising=False)
        assert network_utils.system_proxy() is None
        monkeypatch.setenv("HTTPS_PROXY", "http://env.proxy:3128")
        assert network_utils.system_proxy() == "http://env.proxy:3128"

    def test_resolve_ip_invalid_host(self):
        assert network_utils.resolve_ip("definitely-not-a-real-host.invalid") is None
        assert network_utils.resolve_ip("") is None

    def test_is_reachable_invalid_host(self):
        assert network_utils.is_reachable("definitely-not-a-real-host.invalid", 443, timeout=0.5) is False
        assert network_utils.is_reachable("", 443) is False


# -------------------------------------------------------------------- logger


class TestLogger:
    def test_setup_logging_creates_log_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))

        root = logging.getLogger()
        original_handlers = list(root.handlers)
        for h in original_handlers:
            root.removeHandler(h)

        try:
            from utils import logger as logger_mod

            logger_mod.setup_logging(level=logging.DEBUG)
            log = logger_mod.get_logger("spider.test")
            log.info("hello world")

            for h in root.handlers:
                h.flush()

            log_file = tmp_path / ".spider_manager" / "logs" / "spider.log"
            assert log_file.is_file()
            content = log_file.read_text(encoding="utf-8")
            assert "hello world" in content

            initial_count = len(root.handlers)
            logger_mod.setup_logging(level=logging.INFO)
            assert len(root.handlers) == initial_count
        finally:
            for h in list(root.handlers):
                try:
                    h.close()
                except Exception:
                    pass
                root.removeHandler(h)
            for h in original_handlers:
                root.addHandler(h)

    def test_get_logger_returns_named_logger(self):
        from utils.logger import get_logger

        assert get_logger("spider.x").name == "spider.x"
