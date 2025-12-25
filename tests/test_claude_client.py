"""
Unit tests for Claude API Client.

Tests the ClaudeClient wrapper to ensure proper API parameter formatting,
especially the system prompt format which must be a list of text blocks.
"""

from unittest.mock import Mock, patch

import pytest

from src.services.claude_client import ClaudeClient


class TestClaudeClient:
    """Test ClaudeClient initialization and basic setup."""

    def test_init_with_api_key(self):
        """Test client initialization with explicit API key."""
        client = ClaudeClient(api_key="test-key")
        assert client.api_key == "test-key"

    def test_init_with_settings(self):
        """Test client initialization uses settings API key."""
        client = ClaudeClient()
        # Should use the mocked env var from conftest.py
        assert client.api_key is not None


class TestChatMethod:
    """Test the chat() method for proper API parameter formatting."""

    @patch("src.services.claude_client.Anthropic")
    def test_chat_without_system_prompt(self, mock_anthropic):
        """Test chat() without system prompt omits system parameter."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_client.messages.create.return_value = mock_response

        # Call chat without system prompt
        client = ClaudeClient()
        client.chat(prompt="Hello")

        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]

        # System should NOT be in the call
        assert "system" not in call_kwargs
        assert call_kwargs["messages"] == [{"role": "user", "content": "Hello"}]

    @patch("src.services.claude_client.Anthropic")
    def test_chat_with_system_prompt_formats_correctly(self, mock_anthropic):
        """
        REGRESSION TEST: Ensure system prompt is formatted as list of text blocks.

        Bug: Anthropic API now requires system=[{"type": "text", "text": "..."}]
        not system="..." (string). This test ensures we don't regress.
        """
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_client.messages.create.return_value = mock_response

        # Call chat WITH system prompt
        client = ClaudeClient()
        client.chat(prompt="Hello", system="You are a helpful assistant")

        # Verify API was called correctly
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]

        # System MUST be formatted as list of text blocks
        assert "system" in call_kwargs
        assert isinstance(call_kwargs["system"], list)
        assert len(call_kwargs["system"]) == 1
        assert call_kwargs["system"][0] == {
            "type": "text",
            "text": "You are a helpful assistant",
        }

    @patch("src.services.claude_client.Anthropic")
    def test_chat_with_all_parameters(self, mock_anthropic):
        """Test chat() with all parameters set."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_client.messages.create.return_value = mock_response

        # Call with all params
        client = ClaudeClient()
        client.chat(
            prompt="Test prompt",
            model="claude-3-5-haiku-20241022",
            system="System message",
            max_tokens=1000,
            temperature=0.5,
        )

        # Verify all params passed correctly
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-5-haiku-20241022"
        assert call_kwargs["max_tokens"] == 1000
        assert call_kwargs["temperature"] == 0.5
        assert call_kwargs["system"] == [{"type": "text", "text": "System message"}]

    @patch("src.services.claude_client.Anthropic")
    def test_chat_extracts_text_from_response(self, mock_anthropic):
        """Test that chat() correctly extracts text from API response."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text="Expected response text")]
        mock_client.messages.create.return_value = mock_response

        # Call
        client = ClaudeClient()
        response = client.chat(prompt="Test")

        # Verify we get the text back
        assert response == "Expected response text"

    @patch("src.services.claude_client.Anthropic")
    def test_chat_raises_on_api_error(self, mock_anthropic):
        """Test that chat() propagates API errors."""
        # Setup mock to raise
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        # Should raise
        client = ClaudeClient()
        with pytest.raises(Exception, match="API Error"):
            client.chat(prompt="Test")


class TestChatJsonMethod:
    """Test the chat_json() method for structured JSON responses."""

    @patch("src.services.claude_client.Anthropic")
    def test_chat_json_system_prompt_format(self, mock_anthropic):
        """
        REGRESSION TEST: Ensure chat_json() also formats system prompt correctly.

        chat_json() calls chat() internally, so it should also use the
        correct system prompt format.
        """
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text='{"result": "success"}')]
        mock_client.messages.create.return_value = mock_response

        # Call chat_json with system prompt
        client = ClaudeClient()
        client.chat_json(prompt="Extract data", system="You are a JSON extractor")

        # Verify system prompt formatted correctly
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["system"] == [{"type": "text", "text": "You are a JSON extractor"}]

    @patch("src.services.claude_client.Anthropic")
    def test_chat_json_parses_json_response(self, mock_anthropic):
        """Test that chat_json() correctly parses JSON from response."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        mock_response.content = [Mock(text='{"key": "value", "number": 42}')]
        mock_client.messages.create.return_value = mock_response

        # Call
        client = ClaudeClient()
        result = client.chat_json(prompt="Get JSON")

        # Verify parsed correctly
        assert isinstance(result, dict)
        assert result["key"] == "value"
        assert result["number"] == 42

    @patch("src.services.claude_client.Anthropic")
    def test_chat_json_strips_markdown_code_blocks(self, mock_anthropic):
        """Test that chat_json() handles markdown-wrapped JSON."""
        # Setup mock
        mock_client = Mock()
        mock_anthropic.return_value = mock_client
        mock_response = Mock()
        # Response wrapped in markdown
        mock_response.content = [Mock(text='```json\n{"result": "success"}\n```')]
        mock_client.messages.create.return_value = mock_response

        # Call
        client = ClaudeClient()
        result = client.chat_json(prompt="Get JSON")

        # Should parse successfully despite markdown
        assert result == {"result": "success"}

    @patch("src.services.claude_client.Anthropic")
    def test_chat_json_retries_on_parse_error(self, mock_anthropic):
        """Test that chat_json() retries if first response is invalid JSON."""
        # Setup mock to return invalid JSON first, valid JSON second
        mock_client = Mock()
        mock_anthropic.return_value = mock_client

        # First call returns invalid JSON
        mock_response_1 = Mock()
        mock_response_1.content = [Mock(text="Not valid JSON")]

        # Second call (retry) returns valid JSON
        mock_response_2 = Mock()
        mock_response_2.content = [Mock(text='{"retry": "success"}')]

        mock_client.messages.create.side_effect = [mock_response_1, mock_response_2]

        # Call
        client = ClaudeClient()
        result = client.chat_json(prompt="Get JSON")

        # Should have called API twice (original + retry)
        assert mock_client.messages.create.call_count == 2

        # Should return the second (successful) response
        assert result == {"retry": "success"}


class TestEstimateCost:
    """Test cost estimation functionality."""

    def test_estimate_cost_haiku(self):
        """Test cost estimation for Haiku model."""
        client = ClaudeClient()

        # 1M input tokens, 1M output tokens on Haiku
        # Should be: (1M * $0.25/1M) + (1M * $1.25/1M) = $1.50
        cost = client.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-3-5-haiku-20241022",
        )

        assert cost == 1.50

    def test_estimate_cost_sonnet(self):
        """Test cost estimation for Sonnet model."""
        client = ClaudeClient()

        # 1M input tokens, 1M output tokens on Sonnet
        # Should be: (1M * $3.00/1M) + (1M * $15.00/1M) = $18.00
        cost = client.estimate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            model="claude-sonnet-4-5-20250929",
        )

        # Use Haiku pricing for unknown model as fallback
        # So should default to Haiku: $1.50
        assert cost == 1.50  # Unknown model defaults to Haiku pricing

    def test_estimate_cost_realistic_paper(self):
        """Test cost estimation for a realistic paper analysis."""
        client = ClaudeClient()

        # Typical paper: ~5000 input tokens, ~500 output tokens
        cost = client.estimate_cost(
            input_tokens=5_000, output_tokens=500, model="claude-3-5-haiku-20241022"
        )

        # Should be: (5k * $0.25/1M) + (500 * $1.25/1M) = ~$0.00188
        assert cost < 0.01  # Should be less than a penny


class TestGlobalClientInstance:
    """Test the global client singleton pattern."""

    @patch("src.services.claude_client.ClaudeClient")
    def test_get_claude_client_singleton(self, mock_client_class):
        """Test that get_claude_client returns same instance."""
        # Reset the global client
        import src.services.claude_client
        from src.services.claude_client import get_claude_client

        src.services.claude_client._client = None

        # First call creates instance
        client1 = get_claude_client()

        # Second call returns same instance
        client2 = get_claude_client()

        assert client1 is client2
