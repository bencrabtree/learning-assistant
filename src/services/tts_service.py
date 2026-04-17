"""
Text-to-Speech Service for Research Radar.

Generates audio narration for paper summaries.
Supports multiple TTS providers with a unified interface.

Usage:
    from src.services.tts_service import TTSService

    tts = TTSService()
    if tts.is_configured():
        result = tts.generate_audio_sync(
            arxiv_id="2312.12345",
            title="Paper Title",
            eli5_summary="Simple explanation...",
            key_insight="The key point is...",
        )
        # result.local_path = local file path
        # result.public_url = R2 URL (if configured)
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.config import get_data_dir, settings
from src.models.paper import Paper


@dataclass
class AudioResult:
    """Result of audio generation."""

    local_path: Path | None = None
    public_url: str | None = None

    @property
    def success(self) -> bool:
        """Check if audio was generated successfully."""
        return self.local_path is not None


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    async def synthesize(self, text: str, output_path: Path) -> bool:
        """
        Generate audio from text.

        Args:
            text: The text to synthesize
            output_path: Where to save the audio file

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if provider is properly configured."""
        pass


class EdgeTTSProvider(TTSProvider):
    """
    Microsoft Edge TTS provider.

    Uses Microsoft's neural TTS via the edge-tts package.
    Free, no API key required, excellent quality.

    Recommended voices:
    - en-US-AriaNeural (default) - Natural, friendly female
    - en-US-JennyNeural - Professional female
    - en-US-GuyNeural - Natural male
    - en-US-DavisNeural - Deep male voice
    """

    def __init__(self, voice: str = "en-US-AriaNeural"):
        self.voice = voice

    def is_configured(self) -> bool:
        """Edge TTS requires no configuration, just the package installed."""
        try:
            import edge_tts  # noqa: F401

            return True
        except ImportError:
            logger.warning("edge-tts package not installed. Run: pip install edge-tts")
            return False

    async def synthesize(self, text: str, output_path: Path) -> bool:
        """Generate audio using Edge TTS."""
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(str(output_path))

            logger.debug(f"Generated audio: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Edge TTS synthesis failed: {e}")
            return False


class OpenAITTSProvider(TTSProvider):
    """
    OpenAI TTS provider.

    Uses OpenAI's tts-1 model for high-quality speech synthesis.
    Paid service, requires OPENAI_API_KEY.

    Recommended voices:
    - nova (default) - Warm, engaging
    - alloy - Neutral, clear
    - echo - Deeper, authoritative
    - fable - British accent
    - onyx - Deep male voice
    - shimmer - Soft female voice
    """

    def __init__(self, voice: str = "nova"):
        self.voice = voice
        self.api_key = settings.openai_api_key

    def is_configured(self) -> bool:
        """Check if OpenAI API key is configured."""
        return bool(self.api_key)

    async def synthesize(self, text: str, output_path: Path) -> bool:
        """Generate audio using OpenAI TTS."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key)

            # OpenAI TTS is synchronous, run in thread pool
            response = await asyncio.to_thread(
                client.audio.speech.create,
                model="tts-1",
                voice=self.voice,
                input=text,
            )

            # Stream to file
            await asyncio.to_thread(response.stream_to_file, str(output_path))

            logger.debug(f"Generated audio: {output_path}")
            return True
        except ImportError:
            logger.error("openai package not installed. Run: pip install openai")
            return False
        except Exception as e:
            logger.error(f"OpenAI TTS synthesis failed: {e}")
            return False


class TTSService:
    """
    Text-to-Speech service for generating paper narrations.

    Follows the same pattern as EmailNotifier:
    - Class-based with is_configured() validation
    - Graceful fallback if not configured
    - Configurable via .env

    Example:
        tts = TTSService()
        if tts.is_configured():
            path = tts.generate_audio_sync(...)
    """

    def __init__(self) -> None:
        """Initialize the TTS service with configured provider."""
        self.provider = self._get_provider()
        self.audio_dir = get_data_dir() / "audio"
        self.audio_dir.mkdir(parents=True, exist_ok=True)

    def _get_provider(self) -> TTSProvider | None:
        """Get the configured TTS provider based on settings."""
        provider_name = settings.tts_provider.lower()

        if provider_name == "edge":
            return EdgeTTSProvider(voice=settings.tts_voice)
        elif provider_name == "openai":
            return OpenAITTSProvider(voice=settings.tts_voice)
        else:
            logger.warning(f"Unknown TTS provider: {provider_name}")
            return None

    def is_configured(self) -> bool:
        """Check if TTS is properly configured and enabled."""
        if not settings.tts_enabled:
            return False
        if not self.provider:
            return False
        return self.provider.is_configured()

    def get_audio_path(self, arxiv_id: str) -> Path:
        """
        Get the path where audio file should be stored.

        Args:
            arxiv_id: The paper's arXiv ID

        Returns:
            Path to the audio file (may not exist yet)
        """
        # Sanitize arxiv_id for filename (replace special chars)
        safe_id = arxiv_id.replace("/", "_").replace(":", "_")
        return self.audio_dir / f"{safe_id}.mp3"

    def audio_exists(self, arxiv_id: str) -> bool:
        """Check if audio already exists for a paper."""
        return self.get_audio_path(arxiv_id).exists()

    def build_narration_script(
        self,
        title: str,
        eli5_summary: str,
        key_insight: str,
        main_claim: str | None = None,
    ) -> str:
        """
        Build the narration script from paper data.

        Creates a natural-sounding script optimized for TTS:
        - Title announcement
        - ELI5 summary (main content)
        - Key insight
        - Optional: main claim if short enough

        Args:
            title: Paper title
            eli5_summary: ELI5 explanation
            key_insight: Key insight to remember
            main_claim: Optional technical claim

        Returns:
            Text optimized for TTS narration
        """
        parts = []

        # Title with natural pacing
        parts.append(f"Paper summary: {title}.")
        parts.append("")  # Creates a pause

        # ELI5 Summary - the main content
        if eli5_summary:
            parts.append(eli5_summary)
            parts.append("")

        # Key Insight - the takeaway
        if key_insight:
            parts.append(f"The key insight is: {key_insight}")

        # Main claim (only if short - avoid very technical jargon)
        if main_claim and len(main_claim) < 300:
            parts.append("")
            parts.append(f"In technical terms: {main_claim}")

        return "\n".join(parts)

    async def generate_audio(
        self,
        arxiv_id: str,
        title: str,
        eli5_summary: str,
        key_insight: str,
        main_claim: str | None = None,
        force: bool = False,
    ) -> AudioResult:
        """
        Generate audio narration for a paper and optionally upload to R2.

        Args:
            arxiv_id: Paper's arXiv ID
            title: Paper title
            eli5_summary: ELI5 explanation
            key_insight: Key insight
            main_claim: Optional technical claim
            force: Regenerate even if audio exists

        Returns:
            AudioResult with local_path and public_url (if R2 configured)
        """
        if not self.is_configured():
            logger.warning("TTS not configured - skipping audio generation")
            return AudioResult()

        if not eli5_summary:
            logger.warning(f"No eli5_summary for {arxiv_id} - skipping audio")
            return AudioResult()

        output_path = self.get_audio_path(arxiv_id)

        # Skip if already exists (caching)
        if not force and output_path.exists():
            logger.debug(f"Audio already exists: {output_path}")
            # Still try to get/upload R2 URL
            public_url = self._upload_to_r2(output_path, arxiv_id)
            return AudioResult(local_path=output_path, public_url=public_url)

        # Build script
        script = self.build_narration_script(
            title=title,
            eli5_summary=eli5_summary,
            key_insight=key_insight or "",
            main_claim=main_claim,
        )

        logger.info(f"Generating audio for {arxiv_id}...")

        # Generate audio - provider must not be None at this point
        assert self.provider is not None
        success = await self.provider.synthesize(script, output_path)

        if success and output_path.exists():
            file_size_kb = output_path.stat().st_size / 1024
            logger.info(f"Generated audio: {output_path} ({file_size_kb:.1f} KB)")

            # Upload to R2 for public access
            public_url = self._upload_to_r2(output_path, arxiv_id)

            return AudioResult(local_path=output_path, public_url=public_url)
        else:
            logger.error(f"Failed to generate audio for {arxiv_id}")
            return AudioResult()

    def _upload_to_r2(self, local_path: Path, arxiv_id: str) -> str | None:
        """
        Upload audio to R2 and return public URL.

        Args:
            local_path: Path to local audio file
            arxiv_id: Paper ID for constructing the key

        Returns:
            Public URL or None if R2 not configured
        """
        try:
            from src.services.r2_storage import get_r2_storage

            r2 = get_r2_storage()
            if not r2.is_configured():
                logger.debug("R2 not configured - skipping upload")
                return None

            # Use arxiv_id as key (sanitized)
            key = local_path.name  # e.g., "2312_12345.mp3"
            return r2.upload_file(local_path, key)
        except Exception as e:
            logger.error(f"Failed to upload to R2: {e}")
            return None

    def generate_audio_sync(
        self,
        arxiv_id: str,
        title: str,
        eli5_summary: str,
        key_insight: str,
        main_claim: str | None = None,
        force: bool = False,
    ) -> AudioResult:
        """
        Synchronous wrapper for generate_audio.

        Use this when calling from synchronous code (e.g., LangGraph nodes).
        """
        return asyncio.run(
            self.generate_audio(
                arxiv_id=arxiv_id,
                title=title,
                eli5_summary=eli5_summary,
                key_insight=key_insight,
                main_claim=main_claim,
                force=force,
            )
        )

    def get_digest_path(self, date_str: str) -> Path:
        """Path where the daily digest MP3 is stored locally."""
        digest_dir = self.audio_dir / "digests"
        digest_dir.mkdir(parents=True, exist_ok=True)
        return digest_dir / f"{date_str}.mp3"

    def build_digest_script(self, papers: list[Paper], date_str: str) -> str:
        """Build a single narration script covering multiple papers."""
        parts = [
            f"Good morning. Here is your arXiv digest for {date_str}.",
            f"Today we have {len(papers)} papers.",
            "",
        ]

        for i, paper in enumerate(papers, start=1):
            parts.append(f"Paper {i}: {paper.title}.")
            parts.append("")
            if paper.eli5_summary:
                parts.append(paper.eli5_summary)
                parts.append("")
            if paper.key_insight:
                parts.append(f"The key insight is: {paper.key_insight}")
            if paper.main_claim and len(paper.main_claim) < 300:
                parts.append(f"In technical terms: {paper.main_claim}")
            parts.append("")

        parts.append("That's it for today. Happy reading.")
        return "\n".join(parts)

    async def generate_digest_audio(
        self,
        papers: list[Paper],
        date_str: str,
        force: bool = False,
    ) -> AudioResult:
        """Generate one MP3 covering all papers in the digest and upload to R2."""
        if not self.is_configured():
            logger.warning("TTS not configured - skipping digest audio")
            return AudioResult()

        if not papers:
            logger.warning("No papers supplied for digest audio")
            return AudioResult()

        output_path = self.get_digest_path(date_str)
        key = f"digests/{date_str}.mp3"

        if not force and output_path.exists():
            logger.debug(f"Digest audio already exists: {output_path}")
            public_url = self._upload_digest_to_r2(output_path, key)
            return AudioResult(local_path=output_path, public_url=public_url)

        script = self.build_digest_script(papers, date_str)
        logger.info(f"Generating digest audio for {len(papers)} papers → {output_path}")

        success = await self.provider.synthesize(script, output_path)

        if success and output_path.exists():
            file_size_kb = output_path.stat().st_size / 1024
            logger.info(f"Generated digest audio: {output_path} ({file_size_kb:.1f} KB)")
            public_url = self._upload_digest_to_r2(output_path, key)
            return AudioResult(local_path=output_path, public_url=public_url)

        logger.error(f"Failed to generate digest audio for {date_str}")
        return AudioResult()

    def generate_digest_audio_sync(
        self,
        papers: list[Paper],
        date_str: str,
        force: bool = False,
    ) -> AudioResult:
        """Synchronous wrapper for generate_digest_audio."""
        return asyncio.run(self.generate_digest_audio(papers, date_str, force=force))

    def _upload_digest_to_r2(self, local_path: Path, key: str) -> str | None:
        """Upload a digest file to R2 under a stable digests/ key."""
        try:
            from src.services.r2_storage import get_r2_storage

            r2 = get_r2_storage()
            if not r2.is_configured():
                logger.debug("R2 not configured - skipping digest upload")
                return None
            return r2.upload_file(local_path, key)
        except Exception as e:
            logger.error(f"Failed to upload digest to R2: {e}")
            return None


def get_tts_service() -> TTSService:
    """Get a TTS service instance."""
    return TTSService()
