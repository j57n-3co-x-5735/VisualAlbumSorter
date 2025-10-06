"""Unit tests for AI provider implementations."""

import base64
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

# Add parent directory to path for direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.providers.ollama import OllamaProvider
from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.providers.mlx_vlm import MLXVLMProvider
from visualalbumsorter.providers.base import VisionModelProvider


@pytest.fixture
def sample_image(tmp_path):
    path = tmp_path / "sample.jpg"
    path.write_bytes(b"fake image data")
    return path


@pytest.fixture
def wide_test_image(tmp_path):
    from PIL import Image

    path = tmp_path / "wide.jpg"
    Image.new("RGB", (150, 50), color="red").save(path, "JPEG")
    return path


class DummyProvider(VisionModelProvider):
    """Minimal provider implementation for validation tests."""

    def classify_image(self, image_path: Path, prompt: str, max_retries: int = 3) -> str:
        return ""

    def check_server(self) -> bool:
        return True


class TestVisionModelProviderValidation:
    """Validation scenarios for base provider helper."""

    def test_validate_image_dimension_limit_enforced(self, wide_test_image):
        provider = DummyProvider(
            model_name="model",
            api_url="http://localhost",
            config={"max_image_dimension_px": 100},
        )

        is_valid, error = provider.validate_image(wide_test_image)

        assert is_valid is False
        assert "Image too large" in error
        assert "100px" in error

    def test_validate_image_dimension_limit_disabled(self, wide_test_image):
        provider = DummyProvider(
            model_name="model",
            api_url="http://localhost",
            config={"max_image_dimension_px": 0},
        )

        is_valid, error = provider.validate_image(wide_test_image)

        assert is_valid is True
        assert error == ""


class TestOllamaProvider:
    """Tests for the Ollama provider."""

    @patch("requests.post")
    def test_classify_image_success(self, mock_post, sample_image):
        provider = OllamaProvider(model_name="test-model", api_url="http://localhost:11434/api/generate")

        response = Mock()
        response.json.return_value = {"response": "A yellow fox"}
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        result = provider.classify_image(sample_image, "Describe the image")

        assert result == "A yellow fox"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "test-model"
        assert payload["prompt"] == "Describe the image"
        encoded = payload["images"][0]
        base64.b64decode(encoded)

    @patch("requests.post")
    def test_classify_image_handles_timeout(self, mock_post, sample_image):
        provider = OllamaProvider(model_name="test-model")
        mock_post.side_effect = [
            requests.Timeout("timeout"),
            requests.ConnectionError("conn"),
            Mock(json=Mock(return_value={"response": "stub"}), raise_for_status=Mock(return_value=None)),
        ]

        with patch("time.sleep") as mock_sleep:
            result = provider.classify_image(sample_image, "Prompt", max_retries=3)

        assert result == "stub"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("requests.get")
    def test_check_server_reports_available(self, mock_get):
        provider = OllamaProvider()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"models": [{"name": provider.model_name}]}
        mock_get.return_value = response

        assert provider.check_server() is True
        mock_get.assert_called_once_with("http://127.0.0.1:11434/api/tags", timeout=5)

    @patch("requests.get")
    def test_check_server_handles_missing_model(self, mock_get):
        provider = OllamaProvider(model_name="missing")
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"models": [{"name": "other"}]}
        mock_get.return_value = response

        assert provider.check_server() is False


class TestLMStudioProvider:
    """Tests for the LM Studio provider."""

    @patch("requests.post")
    def test_classify_image_success(self, mock_post, sample_image):
        provider = LMStudioProvider(model_name="test-model")

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": "A yellow fox with ears"}}]
        }
        mock_post.return_value = response

        result = provider.classify_image(sample_image, "Describe the image")

        assert result == "A yellow fox with ears"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == "test-model"
        assert payload["messages"][0]["content"][0]["text"] == "Describe the image"
        assert payload["messages"][0]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")

    @patch("requests.post")
    def test_classify_image_handles_connection_error(self, mock_post, sample_image):
        provider = LMStudioProvider(model_name="test-model")
        mock_post.side_effect = [requests.ConnectionError("down"), Mock(json=Mock(return_value={"choices": [{"message": {"content": "ok"}}]}), raise_for_status=Mock(return_value=None))]

        with patch("time.sleep"):
            result = provider.classify_image(sample_image, "Prompt", max_retries=2)

        assert result == "ok"
        assert mock_post.call_count == 2

    @patch("requests.get")
    def test_check_server(self, mock_get):
        provider = LMStudioProvider()
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        response.json.return_value = {"data": [{"id": "model-a"}]}
        mock_get.return_value = response

        assert provider.check_server() is True
        mock_get.assert_called_once_with("http://localhost:1234/v1/models", timeout=5)


class TestMLXVLMProvider:
    """Tests for the MLX VLM provider."""

    @patch("requests.post")
    def test_classify_image_success(self, mock_post, sample_image):
        provider = MLXVLMProvider(model_name="mlx-model")
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"text": "A fox with yellow fur"}
        mock_post.return_value = response

        result = provider.classify_image(sample_image, "Describe")

        assert result == "A fox with yellow fur"
        payload = mock_post.call_args.kwargs["json"]
        assert payload["image"] == [str(sample_image)]

    @patch("requests.post")
    def test_classify_image_handles_timeout(self, mock_post, sample_image):
        provider = MLXVLMProvider(model_name="mlx-model")
        mock_post.side_effect = [requests.Timeout("timeout"), Mock(json=Mock(return_value={"text": "ok"}), raise_for_status=Mock(return_value=None))]

        with patch("time.sleep"):
            result = provider.classify_image(sample_image, "Prompt", max_retries=2)

        assert result == "ok"
        assert mock_post.call_count == 2

    @patch("requests.get")
    def test_check_server(self, mock_get):
        provider = MLXVLMProvider()
        response = Mock(status_code=200)
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        assert provider.check_server() is True
        mock_get.assert_called_once_with("http://127.0.0.1:8000", timeout=3)


class TestVisionModelProviderBase:
    """Tests for the shared base provider helpers."""

    def test_encode_image(self, sample_image):
        class DummyProvider(VisionModelProvider):
            def classify_image(self, image_path, prompt, max_retries=3):
                return ""

            def check_server(self):
                return True

        provider = DummyProvider("model", "http://localhost")
        encoded = provider.encode_image(sample_image)
        assert isinstance(encoded, str)
        assert base64.b64decode(encoded) == b"fake image data"

    def test_get_provider_name(self):
        class DummyProvider(VisionModelProvider):
            def classify_image(self, image_path, prompt, max_retries=3):
                return ""

            def check_server(self):
                return True

        provider = DummyProvider("model", "http://localhost")
        assert provider.get_provider_name() == "Dummy"

    def test_get_info(self):
        class DummyProvider(VisionModelProvider):
            def classify_image(self, image_path, prompt, max_retries=3):
                return ""

            def check_server(self):
                return True

        provider = DummyProvider("model", "http://localhost")
        info = provider.get_info()
        assert info == {
            "provider": "Dummy",
            "model": "model",
            "api_url": "http://localhost",
            "available": True,
        }
