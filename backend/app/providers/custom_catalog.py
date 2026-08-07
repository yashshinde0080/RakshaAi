"""Custom Model YAML Catalog for llmfit Integration

Enterprise and USB providers can expose custom/private models via YAML
files that llmfit auto-discovers and scores alongside its built-in catalog.

Usage:
    catalog = CustomModelCatalog()
    catalog.load_directory(Path("workspace/plugins/user/models"))
    catalog.register_with_llmfit()  # makes scores available via llmfit
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import json


class CustomModelCatalog:
    """Manages custom model definitions from YAML/JSON files.

    Models declared here are merged into llmfit's catalog so they
    appear in /v1/models/recommend results alongside public models.
    """

    def __init__(self, catalog_dir: Optional[Path] = None):
        self.models: List[Dict[str, Any]] = []
        self.catalog_dir = catalog_dir

    def load_directory(self, directory: Path) -> int:
        """Load all model definition files from a directory.

        Supports .json and .yaml/.yml files.
        Returns count of models loaded.
        """
        directory = Path(directory)
        if not directory.exists():
            return 0

        count = 0
        for ext in ("*.json", "*.yaml", "*.yml"):
            for path in sorted(directory.glob(ext)):
                loaded = self._load_file(path)
                count += loaded

        if self.models:
            self._try_register_with_llmfit()

        return count

    def add_model(self, model_def: Dict[str, Any]):
        """Add a single custom model definition."""
        self.models.append(model_def)
        self._try_register_with_llmfit()

    def _load_file(self, path: Path) -> int:
        """Load a single catalog file. Returns model count."""
        try:
            if path.suffix == ".json":
                with open(path) as f:
                    data = json.load(f)
            else:
                # Try YAML via json-compatible dict
                data = self._load_yaml_fallback(path)

            models_list = data if isinstance(data, list) else data.get("models", [data])
            self.models.extend(models_list)
            return len(models_list)
        except Exception as e:
            print(f"Failed to load catalog {path}: {e}")
            return 0

    def _load_yaml_fallback(self, path: Path) -> Dict:
        """Load YAML file, falling back to json if yaml not available."""
        try:
            import yaml
            with open(path) as f:
                return yaml.safe_load(f) or {}
        except ImportError:
            # No PyYAML -- try .json only
            raise RuntimeError(
                "PyYAML required for .yaml files. "
                "Install: pip install pyyaml"
            )

    def _try_register_with_llmfit(self):
        """Register custom models with llmfit if available."""
        try:
            from llmfit.catalog import register_custom_models
            register_custom_models(self.models)
        except ImportError:
            pass  # llmfit not installed -- skip
        except Exception as e:
            print(f"llmfit custom registration failed: {e}")

    def list_models(self) -> List[Dict[str, Any]]:
        """Return all loaded custom models."""
        return list(self.models)

    def to_json(self) -> str:
        """Serialize catalog to JSON."""
        return json.dumps({"models": self.models}, indent=2)
