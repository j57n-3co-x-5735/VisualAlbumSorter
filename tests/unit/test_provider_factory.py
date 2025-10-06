"""Unit tests for provider factory."""

import pytest
from pathlib import Path
from unittest.mock import Mock

# Add parent directory to path for direct imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from visualalbumsorter.utils.provider_factory import create_provider, list_available_providers
from visualalbumsorter.providers.ollama import OllamaProvider
from visualalbumsorter.providers.lm_studio import LMStudioProvider
from visualalbumsorter.providers.mlx_vlm import MLXVLMProvider


@pytest.fixture(autouse=True)
def mock_provider_availability(monkeypatch):
    """Avoid real network calls when providers check server status."""
    monkeypatch.setattr(OllamaProvider, "check_server", Mock(return_value=True))
    monkeypatch.setattr(LMStudioProvider, "check_server", Mock(return_value=True))
    monkeypatch.setattr(MLXVLMProvider, "check_server", Mock(return_value=True))


@pytest.mark.parametrize(
    "provider_type,expected_cls,settings",
    [
        (
            "ollama",
            OllamaProvider,
            {"model": "qwen2.5vl:3b", "api_url": "http://localhost:11434/api/generate"},
        ),
        (
            "lm_studio",
            LMStudioProvider,
            {"model": "custom-model", "api_url": "http://localhost:1234/v1/chat/completions"},
        ),
        (
            "mlx_vlm",
            MLXVLMProvider,
            {"model": "mlx-community/Phi-3-vision-128k-instruct-4bit", "api_url": "http://localhost:8000/generate"},
        ),
    ],
)
def test_create_provider_with_explicit_settings(provider_type, expected_cls, settings):
    provider = create_provider({"type": provider_type, "settings": settings})
    assert isinstance(provider, expected_cls)
    assert provider.model_name == settings["model"]
    assert provider.api_url == settings["api_url"]


def test_create_provider_passes_through_extra_settings():
    provider = create_provider(
        {
            "type": "lm_studio",
            "settings": {
                "model": "qwen2.5-omni-3b",
                "api_url": "http://localhost:1234/v1/chat/completions",
                "temperature": 0.3,
                "top_p": 0.8,
            },
        }
    )
    assert isinstance(provider, LMStudioProvider)
    assert provider.config == {"temperature": 0.3, "top_p": 0.8}


@pytest.mark.parametrize("provider_type", ["Ollama", "LM_STUDIO", "mLX_vLm"])
def test_create_provider_case_insensitive(provider_type):
    settings = {
        "model": "stub-model",
        "api_url": "http://localhost:9999/stub",
    }
    provider = create_provider({"type": provider_type, "settings": settings})
    assert provider.model_name == "stub-model"
    assert provider.api_url == "http://localhost:9999/stub"


def test_create_provider_unicode_model_name():
    settings = {
        "model": "模型名称",
        "api_url": "http://localhost:11434/api/generate",
    }
    provider = create_provider({"type": "ollama", "settings": settings})
    assert provider.model_name == "模型名称"


def test_create_provider_raises_when_server_unavailable(monkeypatch):
    monkeypatch.setattr(OllamaProvider, "check_server", Mock(return_value=False))
    with pytest.raises(RuntimeError):
        create_provider({
            "type": "ollama",
            "settings": {
                "model": "qwen2.5vl:3b",
                "api_url": "http://localhost:11434/api/generate",
            },
        })


def test_create_provider_unknown_type():
    with pytest.raises(ValueError):
        create_provider({"type": "unknown", "settings": {}})


def test_list_available_providers_contains_expected_options():
    options = list_available_providers()
    assert options["ollama"].startswith("Ollama")
    assert "LM Studio" in options["lm_studio"]
    assert "MLX" in options["mlx_vlm"]
