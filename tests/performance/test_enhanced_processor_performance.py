"""Performance-oriented tests for EnhancedPhotoProcessor."""

import math
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from visualalbumsorter.core.config import (
    AlbumConfig,
    Config,
    LoggingConfig,
    ProcessingConfig,
    ProviderConfig,
    StorageConfig,
    TaskConfig,
)
from visualalbumsorter.core.photo_processor_enhanced import EnhancedPhotoProcessor


def _build_config(tmp_path: Path) -> Config:
    return Config(
        task=TaskConfig(
            name="Performance Test",
            description="Synthetic workload for Visual Album Sorter",
            prompt="Describe the contents of this image in a single sentence.",
            classification_rules={"type": "always_no", "rules": [], "match_all": True},
        ),
        provider=ProviderConfig(
            type="lm_studio",
            settings={
                "model": "qwen2.5-omni-3b",
                "api_url": "http://localhost:1234/v1/chat/completions",
            },
        ),
        album=AlbumConfig(name="PerfAlbum", create_if_missing=False),
        processing=ProcessingConfig(batch_size=100, album_update_frequency=25, debug_mode=False),
        storage=StorageConfig(temp_dir=tmp_path / "state"),
        logging_config=LoggingConfig(level="WARNING", console=False, file=False),
    )


class _StubClassifier:
    def __init__(self) -> None:
        self.calls = 0

    def classify(self, _path, _max_retries: int = 3) -> str:
        self.calls += 1
        return "no"


class _StubPhoto:
    def __init__(self, uuid: str) -> None:
        self.uuid = uuid
        self.original_filename = f"{uuid}.jpg"
        self.ismovie = False
        self.path = f"/fake/{uuid}.jpg"


@pytest.mark.performance
def test_processes_large_batch_without_regression(monkeypatch, tmp_path):
    photo_count = 500
    photos = [_StubPhoto(f"uuid-{i}") for i in range(photo_count)]
    photos_to_process = list(enumerate(photos))

    config = _build_config(tmp_path)
    classifier = _StubClassifier()

    with monkeypatch.context() as m:
        m.setattr(EnhancedPhotoProcessor, "_init_photo_libraries", lambda self: None)
        m.setattr("visualalbumsorter.core.photo_processor_enhanced.time.sleep", lambda _x: None)
        processor = EnhancedPhotoProcessor(config, classifier, enable_diagnostics=False)
        processor.osxphotos = SimpleNamespace(PhotosDB=lambda: SimpleNamespace(photos=lambda: photos))
        processor.PhotosLibrary = lambda: SimpleNamespace(
            albums=[],
            create_album=lambda name: SimpleNamespace(name=name, add_photos=lambda _: None),
        )
        processor.album = SimpleNamespace(add_photos=lambda _: None)
        processor.photos_lib = processor.PhotosLibrary()
        processor._get_skip_reason = lambda _photo: None
        processor._classify_photo = lambda _photo: classifier.classify(Path("/tmp/fake.jpg"))
        processor._save_state = lambda: None
        processor._add_to_album = lambda *_args, **_kwargs: None

        start = time.perf_counter()
        summary = processor._process_photos(photos_to_process, photos)
        duration = time.perf_counter() - start

    assert summary["processed_this_session"] == photo_count
    assert summary["matches_this_session"] == 0
    expected_batches = math.ceil(photo_count / config.processing.batch_size)
    assert summary["batches_processed"] == expected_batches
    assert classifier.calls == photo_count
    assert duration < 0.5, f"batch processing took too long: {duration:.3f}s"
