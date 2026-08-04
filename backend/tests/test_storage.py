"""Unit tests for the storage abstraction (M2, Task 4.1)."""

import pytest
from app.services.storage import LocalStorageService, get_storage_service


def test_save_writes_file_and_returns_scoped_key(tmp_path):
    svc = LocalStorageService(tmp_path)
    key = svc.save(b"jpeg-bytes", "image/jpeg", user_id=7)
    assert key.startswith("7/")
    assert key.endswith(".jpg")
    assert (tmp_path / key).read_bytes() == b"jpeg-bytes"


def test_save_respects_subdir_and_mime_extension(tmp_path):
    svc = LocalStorageService(tmp_path)
    key = svc.save(b"x", "image/png", 7, subdir="scans")
    parts = key.split("/")
    assert parts == ["7", "scans", parts[2]]
    assert key.endswith(".png")


def test_save_generates_unique_filenames(tmp_path):
    svc = LocalStorageService(tmp_path)
    a = svc.save(b"a", "image/jpeg", 1)
    b = svc.save(b"a", "image/jpeg", 1)
    assert a != b
    assert len(list((tmp_path / "1").iterdir())) == 2


def test_save_unknown_mime_falls_back_to_bin(tmp_path):
    svc = LocalStorageService(tmp_path)
    assert svc.save(b"x", "application/octet-stream", 1).endswith(".bin")


def test_delete_removes_file_and_missing_is_noop(tmp_path):
    svc = LocalStorageService(tmp_path)
    key = svc.save(b"x", "image/jpeg", 1)
    svc.delete(key)
    assert not (tmp_path / key).exists()
    svc.delete(key)  # must not raise


def test_url_returns_media_path(tmp_path):
    svc = LocalStorageService(tmp_path)
    assert svc.url("1/abc.jpg") == "/media/1/abc.jpg"


def test_factory_builds_local_service(tmp_path, monkeypatch):

    class _Settings:
        storage_provider = "local"
        storage_local_dir = str(tmp_path)

    monkeypatch.setattr("app.services.storage.get_settings", lambda: _Settings())
    svc = get_storage_service()
    assert isinstance(svc, LocalStorageService)
    assert svc.base_dir == tmp_path


def test_factory_rejects_unwired_s3(monkeypatch):

    class _Settings:
        storage_provider = "s3"
        storage_local_dir = "storage"

    monkeypatch.setattr("app.services.storage.get_settings", lambda: _Settings())
    with pytest.raises(NotImplementedError):
        get_storage_service()
