from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

from app.core.config import Settings


class ModelBundleRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def resolve_model_path(self) -> Path:
        return Path(self.settings.mineria_model_file)

    def load_bundle(self, model_path: Path) -> dict[str, Any] | None:
        try:
            with model_path.open('rb') as handle:
                bundle = pickle.load(handle)
        except FileNotFoundError:
            return None
        except Exception:
            return None

        return bundle if isinstance(bundle, dict) else None
