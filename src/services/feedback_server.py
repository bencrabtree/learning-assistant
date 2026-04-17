"""
Minimal Feedback Server.

A simple Flask server that handles feedback links from email notifications.
Users click links in emails to rate papers as good/neutral/bad.

Also serves audio files for paper narrations.
"""

from pathlib import Path

from flask import Flask, send_file
from loguru import logger

from src.config import settings
from src.database import get_db_session
from src.models.paper import Paper
from src.services.feedback import record_feedback

app = Flask(__name__)


# Simple HTML template for response
RESPONSE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Feedback Recorded</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            text-align: center;
        }}
        .success {{ color: #28a745; }}
        .error {{ color: #dc3545; }}
        .emoji {{ font-size: 48px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="emoji">{emoji}</div>
    <h1 class="{status}">{title}</h1>
    <p>{message}</p>
    <p><a href="https://arxiv.org/abs/{arxiv_id}">View paper on arXiv</a></p>
</body>
</html>
"""


@app.route("/feedback/<arxiv_id>/<rating>")
def handle_feedback(arxiv_id: str, rating: str):
    """
    Handle feedback from email links.

    URL format: /feedback/<arxiv_id>/<rating>
    rating: "good", "neutral", or "bad"
    """
    result = record_feedback(arxiv_id, rating, source="email")

    if result["success"]:
        emoji_map = {"good": "👍", "neutral": "😐", "bad": "👎"}
        emoji = emoji_map.get(rating.lower(), "✓")
        return RESPONSE_HTML.format(
            emoji=emoji,
            status="success",
            title="Thanks for your feedback!",
            message=result["message"],
            arxiv_id=arxiv_id,
        )
    else:
        return (
            RESPONSE_HTML.format(
                emoji="❌",
                status="error",
                title="Feedback Failed",
                message=result["message"],
                arxiv_id=arxiv_id,
            ),
            400,
        )


@app.route("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


@app.route("/audio/<arxiv_id>")
def serve_audio(arxiv_id: str):
    """
    Serve audio file for a paper.

    URL format: /audio/<arxiv_id>
    Returns the MP3 file for the paper's narration.
    """
    # Look up the paper to get its audio path
    with get_db_session() as db:
        paper = db.query(Paper).filter_by(arxiv_id=arxiv_id).first()

        if not paper:
            return {"error": f"Paper not found: {arxiv_id}"}, 404

        if not paper.audio_path:
            return {"error": f"No audio available for: {arxiv_id}"}, 404

        audio_path = Path(paper.audio_path)
        if not audio_path.exists():
            return {"error": f"Audio file missing for: {arxiv_id}"}, 404

        # Serve the file with proper MIME type
        return send_file(
            audio_path,
            mimetype="audio/mpeg",
            as_attachment=False,
            download_name=f"{arxiv_id.replace('/', '_')}.mp3",
        )


def run_feedback_server(host: str = "0.0.0.0", port: int | None = None):  # nosec B104
    """
    Start the feedback server.

    Args:
        host: Host to bind to
        port: Port to listen on (defaults to settings.feedback_port)
    """
    if port is None:
        port = settings.feedback_port

    logger.info(f"Starting feedback server on {host}:{port}")
    logger.info(f"Feedback URL: http://localhost:{port}/feedback/<arxiv_id>/<rating>")
    logger.info("Press Ctrl+C to stop")

    # Disable Flask's default logging in favor of loguru
    import logging

    log = logging.getLogger("werkzeug")
    log.setLevel(logging.WARNING)

    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_feedback_server()
