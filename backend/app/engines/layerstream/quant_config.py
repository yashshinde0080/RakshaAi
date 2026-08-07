from dataclasses import dataclass, asdict
import json
from typing import Optional


@dataclass
class QuantConfig:
    quant_method: str = "none"  # none | int8 | awq | gptq | gguf
    bits: int = 16
    group_size: int = 128
    zero_point: bool = True
    version: str = "gemm"

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "QuantConfig":
        try:
            with open(path) as f:
                return cls(**json.load(f))
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()
