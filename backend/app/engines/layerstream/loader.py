import os
import torch
import gc
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from safetensors.torch import safe_open

from .quant_config import QuantConfig


class LayerWeightLoader:
    def __init__(self, weights_dir: str):
        self.weights_dir = weights_dir
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.future = None
        self.future_path = None
        self.cpu_cache: Dict[str, Dict[str, torch.Tensor]] = {}
        self.quant_config = QuantConfig.load(os.path.join(weights_dir, "quant_config.json"))

    @property
    def is_quantized(self) -> bool:
        return self.quant_config.quant_method not in ("none",)

    @property
    def quant_method(self) -> str:
        return self.quant_config.quant_method

    def _load_file(self, path: str) -> Dict[str, torch.Tensor]:
        """Loads safetensors to CPU, dequantizing int8 on the fly."""
        if not os.path.exists(path):
            return {}
        state_dict = {}
        with safe_open(path, framework="pt", device="cpu") as f:
            for k in f.keys():
                state_dict[k] = f.get_tensor(k)

        if self.quant_config.quant_method == "int8":
            scales = {}
            for k in list(state_dict.keys()):
                if k.endswith(".scale"):
                    scales[k.removesuffix(".scale")] = state_dict.pop(k)

            for k, tensor in state_dict.items():
                if tensor.dtype == torch.int8 and k in scales:
                    state_dict[k] = tensor.to(torch.float32) * scales[k]

        return state_dict

    def prefetch_async(self, path: str):
        """Asynchronously double-buffer the loading of the next tensor."""
        if path not in self.cpu_cache and self.future is None:
            self.future = self.executor.submit(self._load_file, path)
            self.future_path = path

    def get_weights(self, path: str) -> Dict[str, torch.Tensor]:
        """Provides weights and permanently caches them in CPU memory to avoid duplicate IO loops."""
        if path in self.cpu_cache:
            return self.cpu_cache[path]
            
        if self.future is not None and self.future_path == path:
            state_dict = self.future.result()
            self.cpu_cache[path] = state_dict
            self.future = None
            self.future_path = None
            return state_dict
            
        state_dict = self._load_file(path)
        self.cpu_cache[path] = state_dict
        return state_dict
        
    def clear_cache(self):
        self.cpu_cache.clear()
        gc.collect()
