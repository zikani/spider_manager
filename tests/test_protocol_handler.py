import pytest

from core.protocol_handler import UnsupportedProtocolError, normalize_url


def test_normalize_adds_https():
    assert normalize_url("example.com/file").startswith("https://")


def test_normalize_keeps_scheme():
    u = normalize_url("https://Example.COM/path")
    assert u.startswith("https://example.com/")


def test_rejects_ftp():
    with pytest.raises(UnsupportedProtocolError):
        normalize_url("ftp://host/file")


def test_rejects_empty():
    with pytest.raises(ValueError):
        normalize_url("")
