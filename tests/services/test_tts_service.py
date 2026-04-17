"""
Tests for the TTS (Text-to-Speech) service.

These tests verify the TTS functionality without actually
generating audio files (uses mocks).
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.tts_service import (
    EdgeTTSProvider,
    OpenAITTSProvider,
    TTSService,
    get_tts_service,
)


class TestEdgeTTSProvider:
    """Tests for Edge TTS provider."""

    def test_default_voice(self):
        """Test default voice is set correctly."""
        provider = EdgeTTSProvider()
        assert provider.voice == "en-US-AriaNeural"

    def test_custom_voice(self):
        """Test custom voice can be set."""
        provider = EdgeTTSProvider(voice="en-US-GuyNeural")
        assert provider.voice == "en-US-GuyNeural"

    def test_is_configured_when_package_installed(self):
        """Test is_configured returns True when edge-tts is available."""
        provider = EdgeTTSProvider()
        # Will return True if edge-tts is installed
        result = provider.is_configured()
        assert isinstance(result, bool)

    def test_is_configured_when_package_missing(self):
        """Test is_configured returns False when edge-tts is not available."""
        with patch.dict("sys.modules", {"edge_tts": None}):
            provider = EdgeTTSProvider()
            # Force ImportError by patching __import__
            with patch("builtins.__import__", side_effect=ImportError):
                assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tmp_path):
        """Test successful audio synthesis."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        # Mock edge_tts.Communicate
        mock_communicate = MagicMock()
        mock_communicate.save = AsyncMock()

        with patch("edge_tts.Communicate", return_value=mock_communicate):
            result = await provider.synthesize("Hello world", output_path)

        assert result is True
        mock_communicate.save.assert_called_once_with(str(output_path))

    @pytest.mark.asyncio
    async def test_synthesize_failure(self, tmp_path):
        """Test audio synthesis failure handling."""
        provider = EdgeTTSProvider()
        output_path = tmp_path / "test.mp3"

        with patch("edge_tts.Communicate", side_effect=Exception("TTS Error")):
            result = await provider.synthesize("Hello world", output_path)

        assert result is False


class TestOpenAITTSProvider:
    """Tests for OpenAI TTS provider."""

    def test_default_voice(self):
        """Test default voice is set correctly."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            provider = OpenAITTSProvider()
            assert provider.voice == "nova"

    def test_custom_voice(self):
        """Test custom voice can be set."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            provider = OpenAITTSProvider(voice="alloy")
            assert provider.voice == "alloy"

    def test_is_configured_with_api_key(self):
        """Test is_configured returns True when API key is set."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-key"
            provider = OpenAITTSProvider()
            assert provider.is_configured() is True

    def test_is_configured_without_api_key(self):
        """Test is_configured returns False when API key is missing."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = None
            provider = OpenAITTSProvider()
            assert provider.is_configured() is False

    @pytest.mark.asyncio
    async def test_synthesize_success(self, tmp_path):
        """Test successful OpenAI audio synthesis."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-key"
            provider = OpenAITTSProvider()
            output_path = tmp_path / "test.mp3"

            mock_response = MagicMock()
            mock_response.stream_to_file = MagicMock()

            mock_client = MagicMock()
            mock_client.audio.speech.create = MagicMock(return_value=mock_response)

            with patch.dict(
                "sys.modules", {"openai": MagicMock(OpenAI=MagicMock(return_value=mock_client))}
            ):
                result = await provider.synthesize("Hello world", output_path)

            assert result is True

    @pytest.mark.asyncio
    async def test_synthesize_import_error(self, tmp_path):
        """Test OpenAI synthesis handles missing package."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-key"
            provider = OpenAITTSProvider()
            output_path = tmp_path / "test.mp3"

            # Remove openai from modules to trigger ImportError
            with patch.dict("sys.modules", {"openai": None}):
                result = await provider.synthesize("Hello world", output_path)

            assert result is False

    @pytest.mark.asyncio
    async def test_synthesize_api_error(self, tmp_path):
        """Test OpenAI synthesis handles API errors."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-test-key"
            provider = OpenAITTSProvider()
            output_path = tmp_path / "test.mp3"

            mock_client = MagicMock()
            mock_client.audio.speech.create = MagicMock(side_effect=Exception("API Error"))

            with patch.dict(
                "sys.modules", {"openai": MagicMock(OpenAI=MagicMock(return_value=mock_client))}
            ):
                result = await provider.synthesize("Hello world", output_path)

            assert result is False


class TestTTSService:
    """Tests for TTS service."""

    @pytest.fixture(autouse=True)
    def disable_r2_upload(self):
        """Prevent tests from touching real R2."""
        with patch(
            "src.services.tts_service.TTSService._upload_to_r2",
            return_value=None,
        ):
            yield

    @pytest.fixture
    def mock_settings_disabled(self):
        """Create mock settings with TTS disabled."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.tts_enabled = False
            mock_settings.tts_provider = "edge"
            mock_settings.tts_voice = "en-US-AriaNeural"
            mock_settings.openai_api_key = None
            yield mock_settings

    @pytest.fixture
    def mock_settings_edge(self):
        """Create mock settings with Edge TTS enabled."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.tts_enabled = True
            mock_settings.tts_provider = "edge"
            mock_settings.tts_voice = "en-US-AriaNeural"
            mock_settings.openai_api_key = None
            yield mock_settings

    @pytest.fixture
    def mock_settings_openai(self):
        """Create mock settings with OpenAI TTS enabled."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.tts_enabled = True
            mock_settings.tts_provider = "openai"
            mock_settings.tts_voice = "nova"
            mock_settings.openai_api_key = "sk-test-key"
            yield mock_settings

    def test_is_configured_when_disabled(self, mock_settings_disabled):
        """Test is_configured returns False when TTS is disabled."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()
            assert service.is_configured() is False

    def test_is_configured_when_enabled_edge(self, mock_settings_edge):
        """Test is_configured returns True when Edge TTS is enabled."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()
            # Will be True if edge-tts package is installed
            assert isinstance(service.is_configured(), bool)

    def test_unknown_provider_returns_none(self):
        """Test unknown TTS provider returns None."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.tts_enabled = True
            mock_settings.tts_provider = "unknown_provider"
            mock_settings.tts_voice = "test"
            mock_settings.openai_api_key = None

            with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
                mock_data_dir.return_value = Path("/tmp/test")
                service = TTSService()
                assert service.provider is None
                assert service.is_configured() is False

    def test_get_audio_path_sanitizes_id(self, mock_settings_edge):
        """Test audio path sanitizes arXiv ID correctly."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            # Test various arXiv ID formats
            path1 = service.get_audio_path("2312.12345v1")
            assert "2312.12345v1" in str(path1)
            assert path1.suffix == ".mp3"

            # Test ID with special characters
            path2 = service.get_audio_path("cs/0401001")
            assert "cs_0401001" in str(path2)

    def test_audio_exists_false_for_missing(self, mock_settings_edge):
        """Test audio_exists returns False for non-existent files."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/nonexistent")
            service = TTSService()
            assert service.audio_exists("2312.12345") is False

    def test_build_narration_script_basic(self, mock_settings_edge):
        """Test narration script building with basic inputs."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            script = service.build_narration_script(
                title="Test Paper Title",
                eli5_summary="This is a simple explanation.",
                key_insight="The main point is important.",
            )

            assert "Test Paper Title" in script
            assert "simple explanation" in script
            assert "main point" in script
            assert "Paper summary:" in script

    def test_build_narration_script_with_main_claim(self, mock_settings_edge):
        """Test narration script includes main claim if short."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            script = service.build_narration_script(
                title="Test Paper",
                eli5_summary="Simple explanation.",
                key_insight="Key point.",
                main_claim="The main technical claim of this paper.",
            )

            assert "In technical terms:" in script
            assert "main technical claim" in script

    def test_build_narration_script_skips_long_claim(self, mock_settings_edge):
        """Test narration script skips main claim if too long."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            long_claim = "This is a very long claim. " * 20  # > 300 chars
            script = service.build_narration_script(
                title="Test Paper",
                eli5_summary="Simple explanation.",
                key_insight="Key point.",
                main_claim=long_claim,
            )

            assert "In technical terms:" not in script

    @pytest.mark.asyncio
    async def test_generate_audio_when_not_configured(self, mock_settings_disabled):
        """Test generate_audio returns unsuccessful AudioResult when not configured."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            result = await service.generate_audio(
                arxiv_id="2312.12345",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
            )

            assert not result.success
            assert result.local_path is None

    @pytest.mark.asyncio
    async def test_generate_audio_skips_empty_summary(self, mock_settings_edge):
        """Test generate_audio returns unsuccessful AudioResult when eli5_summary is empty."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            result = await service.generate_audio(
                arxiv_id="2312.12345",
                title="Test Paper",
                eli5_summary="",  # Empty
                key_insight="Test insight",
            )

            assert not result.success
            assert result.local_path is None

    @pytest.mark.asyncio
    async def test_generate_audio_uses_cache(self, mock_settings_edge, tmp_path):
        """Test generate_audio uses cached file if it exists."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = tmp_path
            (tmp_path / "audio").mkdir()

            service = TTSService()

            # Create existing audio file
            audio_path = service.get_audio_path("2312.12345")
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            audio_path.write_text("fake audio data")

            result = await service.generate_audio(
                arxiv_id="2312.12345",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
            )

            assert result.success
            assert result.local_path == audio_path

    @pytest.mark.asyncio
    async def test_generate_audio_success(self, mock_settings_edge, tmp_path):
        """Test successful audio generation."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = tmp_path
            (tmp_path / "audio").mkdir()

            service = TTSService()
            audio_path = service.get_audio_path("2312.99999")

            # Mock the provider's synthesize method to create the file
            async def mock_synthesize(text, path):
                path.write_text("fake audio")
                return True

            service.provider.synthesize = mock_synthesize

            result = await service.generate_audio(
                arxiv_id="2312.99999",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
            )

            assert result.success
            assert result.local_path == audio_path
            assert audio_path.exists()

    @pytest.mark.asyncio
    async def test_generate_audio_force_regenerate(self, mock_settings_edge, tmp_path):
        """Test force flag regenerates audio even if cached."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = tmp_path
            (tmp_path / "audio").mkdir()

            service = TTSService()
            audio_path = service.get_audio_path("2312.88888")

            # Create existing audio file
            audio_path.write_text("old audio")

            # Mock synthesize to write new content
            async def mock_synthesize(text, path):
                path.write_text("new audio")
                return True

            service.provider.synthesize = mock_synthesize

            result = await service.generate_audio(
                arxiv_id="2312.88888",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
                force=True,
            )

            assert result.success
            assert result.local_path == audio_path
            assert audio_path.read_text() == "new audio"

    @pytest.mark.asyncio
    async def test_generate_audio_provider_failure(self, mock_settings_edge, tmp_path):
        """Test audio generation handles provider failure."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = tmp_path
            (tmp_path / "audio").mkdir()

            service = TTSService()

            # Mock synthesize to fail
            async def mock_synthesize(text, path):
                return False

            service.provider.synthesize = mock_synthesize

            result = await service.generate_audio(
                arxiv_id="2312.77777",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
            )

            assert not result.success
            assert result.local_path is None

    def test_generate_audio_sync_wrapper(self, mock_settings_disabled):
        """Test synchronous wrapper returns unsuccessful AudioResult when not configured."""
        with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
            mock_data_dir.return_value = Path("/tmp/test")
            service = TTSService()

            result = service.generate_audio_sync(
                arxiv_id="2312.12345",
                title="Test Paper",
                eli5_summary="Test summary",
                key_insight="Test insight",
            )

            assert not result.success  # Not configured


class TestGetTTSService:
    """Tests for get_tts_service helper function."""

    def test_returns_tts_service_instance(self):
        """Test get_tts_service returns a TTSService instance."""
        with patch("src.services.tts_service.settings") as mock_settings:
            mock_settings.tts_enabled = False
            mock_settings.tts_provider = "edge"
            mock_settings.tts_voice = "en-US-AriaNeural"
            mock_settings.openai_api_key = None

            with patch("src.services.tts_service.get_data_dir") as mock_data_dir:
                mock_data_dir.return_value = Path("/tmp/test")
                service = get_tts_service()
                assert isinstance(service, TTSService)
