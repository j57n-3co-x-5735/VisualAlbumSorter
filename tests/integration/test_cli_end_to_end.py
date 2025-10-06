"""End-to-end smoke tests for the Visual Album Sorter CLI."""

import json
from types import SimpleNamespace

import pytest

import visualalbumsorter.cli as vas_cli


@pytest.mark.integration
def test_cli_main_runs_with_custom_config(monkeypatch, tmp_path):
    config_path = tmp_path / "vas_config.json"
    config_data = {
        "task": {
            "name": "Example Album Task",
            "description": "Identify photos that match the provided prompt and rules",
            "prompt": "Describe what you see in one concise sentence.",
            "classification_rules": {
                "type": "always_yes",
                "rules": [],
                "match_all": True,
            },
        },
        "provider": {
            "type": "lm_studio",
            "settings": {
                "model": "qwen2.5-omni-3b",
                "api_url": "http://localhost:1234/v1/chat/completions",
            },
        },
        "album": {"name": "VASorter_Album", "create_if_missing": False},
        "processing": {
            "batch_size": 10,
            "album_update_frequency": 5,
            "skip_types": ["HEIC"],
            "skip_videos": True,
            "debug_mode": False,
            "debug_limit": 1,
        },
        "storage": {
            "temp_dir": str(tmp_path / "state"),
            "state_file": "state.json",
            "done_file": "done.txt",
            "log_file": "visual_album_sorter.log",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "console": False,
            "file": False,
        },
    }
    config_path.write_text(json.dumps(config_data))

    captured = {}

    def fake_args():
        return SimpleNamespace(
            config=config_path,
            provider=None,
            diagnostics=False,
            debug=True,
            debug_limit=2,
            batch_size=None,
            album_name=None,
            no_album=False,
            log_file=None,
            verbose=False,
            quiet=False,
            reset_state=False,
            list_providers=False,
            check_server=False,
            show_config=False,
            verify=False,
            status=False,
            analyze_work=None,
            rules=None,
            continue_processing=False,
        )

    stub_provider = object()

    def fake_create_provider(provider_cfg):
        captured["provider_cfg"] = provider_cfg
        return stub_provider

    class FakeClassifier:
        def __init__(self, provider, task_cfg):
            captured["classifier"] = {
                "provider": provider,
                "prompt": task_cfg["prompt"],
            }

        def classify(self, *_args, **_kwargs):
            return "yes"

    class FakeProcessor:
        def __init__(self, config, classifier, enable_diagnostics=True):
            captured["config_task_name"] = config.task.name
            captured["processor_classifier"] = classifier
            captured["enable_diagnostics"] = enable_diagnostics

        def process_library(self):
            captured["process_invoked"] = True
            return {"status": "completed", "processed_this_session": 3}

    monkeypatch.setattr(vas_cli, "parse_arguments", lambda argv=None: fake_args())
    monkeypatch.setattr(vas_cli, "setup_cli_logging", lambda verbose, quiet: None)
    monkeypatch.setattr(vas_cli, "create_provider", fake_create_provider)
    monkeypatch.setattr(vas_cli, "ImageClassifier", FakeClassifier)
    monkeypatch.setattr(vas_cli, "EnhancedPhotoProcessor", FakeProcessor)

    exit_code = vas_cli.main()

    assert exit_code == 0
    assert captured["provider_cfg"]["type"] == "lm_studio"
    assert captured["classifier"]["prompt"] == config_data["task"]["prompt"]
    assert captured["config_task_name"] == config_data["task"]["name"]
    assert captured["process_invoked"] is True
