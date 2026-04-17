"""Tests for the Cloudflare R2 storage service."""

from unittest.mock import MagicMock, patch

import pytest

from src.services.r2_storage import R2Storage, get_r2_storage


@pytest.fixture
def mock_settings_configured():
    """Fully configured R2 settings."""
    with patch("src.services.r2_storage.settings") as mock_settings:
        mock_settings.r2_account_id = "acct-123"
        mock_settings.r2_access_key_id = "key-id"
        mock_settings.r2_secret_access_key = "secret"
        mock_settings.r2_bucket_name = "arxiv-audio"
        mock_settings.r2_public_url = "https://pub-xxx.r2.dev"
        yield mock_settings


@pytest.fixture
def mock_settings_unconfigured():
    """R2 settings with missing credentials."""
    with patch("src.services.r2_storage.settings") as mock_settings:
        mock_settings.r2_account_id = None
        mock_settings.r2_access_key_id = None
        mock_settings.r2_secret_access_key = None
        mock_settings.r2_bucket_name = "arxiv-audio"
        mock_settings.r2_public_url = None
        yield mock_settings


class TestIsConfigured:
    def test_is_configured_true_when_all_set(self, mock_settings_configured):
        storage = R2Storage()
        assert storage.is_configured() is True

    def test_is_configured_false_when_missing(self, mock_settings_unconfigured):
        storage = R2Storage()
        assert storage.is_configured() is False

    def test_is_configured_false_when_public_url_missing(self, mock_settings_configured):
        mock_settings_configured.r2_public_url = None
        storage = R2Storage()
        assert storage.is_configured() is False


class TestClientLazyInit:
    def test_client_raises_when_not_configured(self, mock_settings_unconfigured):
        storage = R2Storage()
        with pytest.raises(ValueError, match="R2 is not configured"):
            _ = storage.client

    def test_client_builds_boto3_with_r2_endpoint(self, mock_settings_configured):
        storage = R2Storage()
        with patch("src.services.r2_storage.boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            _ = storage.client
            args, kwargs = mock_boto.call_args
            assert args[0] == "s3"
            assert kwargs["endpoint_url"] == "https://acct-123.r2.cloudflarestorage.com"
            assert kwargs["aws_access_key_id"] == "key-id"

    def test_client_caches_instance(self, mock_settings_configured):
        storage = R2Storage()
        with patch("src.services.r2_storage.boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            first = storage.client
            second = storage.client
            assert first is second
            assert mock_boto.call_count == 1


class TestUploadFile:
    def test_upload_not_configured_returns_none(self, mock_settings_unconfigured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "a.mp3"
        local.write_bytes(b"fake")
        assert storage.upload_file(local) is None

    def test_upload_missing_file_returns_none(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        missing = tmp_path / "nope.mp3"
        assert storage.upload_file(missing) is None

    def test_upload_success_returns_public_url(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "2312_12345.mp3"
        local.write_bytes(b"fake mp3")

        mock_client = MagicMock()
        storage._client = mock_client

        url = storage.upload_file(local)
        assert url == "https://pub-xxx.r2.dev/2312_12345.mp3"
        mock_client.upload_file.assert_called_once()
        call_kwargs = mock_client.upload_file.call_args.kwargs
        assert call_kwargs["ExtraArgs"]["ContentType"] == "audio/mpeg"

    def test_upload_with_custom_key(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "a.mp3"
        local.write_bytes(b"x")

        mock_client = MagicMock()
        storage._client = mock_client

        url = storage.upload_file(local, key="digests/2026-04-17.mp3")
        assert url == "https://pub-xxx.r2.dev/digests/2026-04-17.mp3"

    def test_upload_non_mp3_sets_octet_stream(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "a.txt"
        local.write_text("hi")

        mock_client = MagicMock()
        storage._client = mock_client

        storage.upload_file(local)
        call_kwargs = mock_client.upload_file.call_args.kwargs
        assert call_kwargs["ExtraArgs"]["ContentType"] == "application/octet-stream"

    def test_upload_strips_trailing_slash_from_public_url(self, mock_settings_configured, tmp_path):
        mock_settings_configured.r2_public_url = "https://pub-xxx.r2.dev/"
        storage = R2Storage()
        local = tmp_path / "a.mp3"
        local.write_bytes(b"x")
        storage._client = MagicMock()
        assert storage.upload_file(local) == "https://pub-xxx.r2.dev/a.mp3"

    def test_upload_handles_client_error(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "a.mp3"
        local.write_bytes(b"x")

        mock_client = MagicMock()
        mock_client.upload_file.side_effect = Exception("network down")
        storage._client = mock_client

        assert storage.upload_file(local) is None

    def test_upload_accepts_string_path(self, mock_settings_configured, tmp_path):
        storage = R2Storage()
        local = tmp_path / "a.mp3"
        local.write_bytes(b"x")
        storage._client = MagicMock()

        url = storage.upload_file(str(local))
        assert url is not None


class TestDeleteFile:
    def test_delete_not_configured_returns_false(self, mock_settings_unconfigured):
        storage = R2Storage()
        assert storage.delete_file("a.mp3") is False

    def test_delete_success(self, mock_settings_configured):
        storage = R2Storage()
        mock_client = MagicMock()
        storage._client = mock_client
        assert storage.delete_file("a.mp3") is True
        mock_client.delete_object.assert_called_once_with(Bucket="arxiv-audio", Key="a.mp3")

    def test_delete_handles_error(self, mock_settings_configured):
        storage = R2Storage()
        mock_client = MagicMock()
        mock_client.delete_object.side_effect = Exception("no such key")
        storage._client = mock_client
        assert storage.delete_file("a.mp3") is False


class TestFileExists:
    def test_exists_not_configured_returns_false(self, mock_settings_unconfigured):
        storage = R2Storage()
        assert storage.file_exists("a.mp3") is False

    def test_exists_true_when_head_succeeds(self, mock_settings_configured):
        storage = R2Storage()
        mock_client = MagicMock()
        storage._client = mock_client
        assert storage.file_exists("a.mp3") is True

    def test_exists_false_when_head_raises(self, mock_settings_configured):
        storage = R2Storage()
        mock_client = MagicMock()
        mock_client.head_object.side_effect = Exception("404")
        storage._client = mock_client
        assert storage.file_exists("a.mp3") is False


class TestGetR2Storage:
    def test_returns_singleton(self, mock_settings_configured):
        import src.services.r2_storage as r2_mod

        r2_mod._r2_storage = None
        first = get_r2_storage()
        second = get_r2_storage()
        assert first is second
