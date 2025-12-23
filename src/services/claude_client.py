"""
Claude API Client Wrapper

This module provides a simple interface for calling Claude.

Key Concepts:
- API client = A wrapper around the Anthropic SDK
- Messages API = Claude's chat interface (send messages, get responses)
- Streaming = Get responses token-by-token (not using this yet)
- JSON mode = Ask Claude to return structured data (we use this!)

Why wrap the API?
- Centralize error handling
- Add logging for debugging
- Make it easy to swap models
- Track API usage and costs
"""

from typing import Optional, Dict, Any, List
from anthropic import Anthropic
from loguru import logger

from src.config import settings


class ClaudeClient:
    """
    Wrapper for the Claude API.

    This provides a simple interface for:
    - Sending prompts to Claude
    - Getting structured JSON responses
    - Handling errors and retries

    Example usage:
        client = ClaudeClient()
        response = client.chat(
            prompt="Explain transformers in simple terms",
            model="claude-3-5-haiku-20241022"
        )
        print(response)
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Claude client.

        Args:
            api_key: Anthropic API key. If not provided, uses settings.anthropic_api_key
        """
        self.api_key = api_key or settings.anthropic_api_key
        self.client = Anthropic(api_key=self.api_key)
        logger.debug("Claude client initialized")

    def chat(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
        **kwargs,
    ) -> str:
        """
        Send a prompt to Claude and get a text response.

        Args:
            prompt: The user message to send
            model: Which Claude model to use (defaults to reader_model from config)
            system: System prompt (sets Claude's behavior/role)
            max_tokens: Maximum response length
            temperature: Randomness (0 = deterministic, 1 = creative)
            **kwargs: Additional arguments for the API

        Returns:
            Claude's response as a string

        Example:
            response = client.chat(
                prompt="What is machine learning?",
                system="You are a helpful teacher.",
                temperature=0.7
            )
        """
        model = model or settings.reader_model

        logger.debug(f"Calling Claude API with model={model}")

        try:
            # Build the messages list
            # Claude's API expects this format:
            # [{"role": "user", "content": "..."}]
            messages = [{"role": "user", "content": prompt}]

            # Make the API call
            response = self.client.messages.create(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system if system else None,
                messages=messages,
                **kwargs,
            )

            # Extract the text from the response
            # Claude returns a Message object with content blocks
            # We want the text from the first content block
            text = response.content[0].text

            logger.debug(f"Claude responded with {len(text)} characters")

            return text

        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise

    def chat_json(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Send a prompt to Claude and get a JSON response.

        This is useful when you want Claude to return structured data
        (like extracting specific fields from a paper).

        How it works:
        1. We add instructions to the prompt asking for JSON
        2. We parse Claude's response as JSON
        3. If parsing fails, we retry with clearer instructions

        Args:
            prompt: The user message (should ask for JSON output)
            model: Which Claude model to use
            system: System prompt
            max_tokens: Maximum response length
            temperature: Randomness

        Returns:
            Parsed JSON response as a Python dict

        Example:
            prompt = '''
            Extract the following from this paper:
            {
              "main_claim": "...",
              "methodology": "...",
              "key_results": ["...", "..."]
            }

            Paper:
            Title: Attention is All You Need
            Abstract: We propose a new architecture...
            '''

            result = client.chat_json(prompt)
            print(result["main_claim"])
        """
        import json

        model = model or settings.reader_model

        logger.debug(f"Calling Claude API for JSON response with model={model}")

        # Add JSON formatting instructions to the prompt
        enhanced_prompt = f"""{prompt}

IMPORTANT: Return ONLY valid JSON. Do not include any text before or after the JSON.
Do not use markdown code blocks. Just raw JSON."""

        try:
            # Get text response
            text = self.chat(
                prompt=enhanced_prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Try to parse as JSON
            try:
                # Sometimes Claude wraps JSON in markdown code blocks
                # Remove them if present
                if text.strip().startswith("```"):
                    # Extract JSON from code block
                    text = text.strip()
                    text = text.removeprefix("```json").removeprefix("```")
                    text = text.removesuffix("```").strip()

                data = json.loads(text)
                logger.debug("Successfully parsed JSON response")
                return data

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON: {e}")
                logger.error(f"Response text: {text[:500]}...")

                # Try one more time with even clearer instructions
                logger.info("Retrying with stricter JSON instructions...")

                retry_prompt = f"""{prompt}

CRITICAL: You MUST return ONLY a valid JSON object. Nothing else.
Do NOT use markdown. Do NOT add explanations.
ONLY JSON."""

                text = self.chat(
                    prompt=retry_prompt,
                    model=model,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=0,  # Make it more deterministic
                )

                # Clean and parse
                if text.strip().startswith("```"):
                    text = text.strip()
                    text = text.removeprefix("```json").removeprefix("```")
                    text = text.removesuffix("```").strip()

                data = json.loads(text)
                logger.debug("Successfully parsed JSON on retry")
                return data

        except Exception as e:
            logger.error(f"Claude JSON call failed: {e}")
            raise

    def estimate_cost(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ) -> float:
        """
        Estimate the cost of an API call.

        Claude pricing (as of Dec 2024):
        - Haiku: $0.25 / 1M input tokens, $1.25 / 1M output tokens
        - Sonnet: $3.00 / 1M input tokens, $15.00 / 1M output tokens

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: Which model was used

        Returns:
            Estimated cost in USD

        Example:
            cost = client.estimate_cost(1000, 500, "claude-3-5-haiku-20241022")
            print(f"This call cost ~${cost:.4f}")
        """
        model = model or settings.reader_model

        # Pricing per 1M tokens (USD)
        pricing = {
            "claude-3-5-haiku-20241022": {
                "input": 0.25,
                "output": 1.25,
            },
            "claude-3-5-sonnet-20241022": {
                "input": 3.00,
                "output": 15.00,
            },
        }

        if model not in pricing:
            logger.warning(f"Unknown model {model}, using Haiku pricing")
            model = "claude-3-5-haiku-20241022"

        input_cost = (input_tokens / 1_000_000) * pricing[model]["input"]
        output_cost = (output_tokens / 1_000_000) * pricing[model]["output"]

        total_cost = input_cost + output_cost

        logger.debug(
            f"Estimated cost: ${total_cost:.4f} "
            f"({input_tokens} in + {output_tokens} out tokens)"
        )

        return total_cost


# ============================================================================
# Global client instance
# ============================================================================

# Create a singleton client instance
# This avoids creating multiple API clients
_client: Optional[ClaudeClient] = None


def get_claude_client() -> ClaudeClient:
    """
    Get the global Claude client instance.

    This is a singleton pattern - we only create one client
    and reuse it throughout the app.

    Example:
        client = get_claude_client()
        response = client.chat("Hello, Claude!")
    """
    global _client
    if _client is None:
        _client = ClaudeClient()
    return _client


if __name__ == "__main__":
    # Test the client
    print("Testing Claude client...")

    client = get_claude_client()

    # Test simple chat
    print("\n1. Testing simple chat...")
    response = client.chat(
        prompt="Say 'Hello, World!' in exactly 3 words.",
        temperature=0,
    )
    print(f"Response: {response}")

    # Test JSON mode
    print("\n2. Testing JSON mode...")
    response = client.chat_json(
        prompt="""
        Return this information as JSON:
        {
          "name": "Claude",
          "version": "3.5",
          "awesome": true
        }
        """,
        temperature=0,
    )
    print(f"JSON Response: {response}")

    print("\n✅ Client tests passed!")
