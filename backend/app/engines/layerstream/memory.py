import os
from typing import Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

import torch
import torch.nn as nn
from transformers.cache_utils import DynamicCache
from safetensors.torch import load_file

class MemoryManager:
    def __init__(self, device: str = "cuda"):
        self.device = torch.device(device)
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.prefetch_future = None

    def load_state_dict_async(self, path: str):
        """Asynchronous disk IO to overlap with compute."""
        if not os.path.exists(path):
            return
        self.prefetch_future = self.executor.submit(load_file, path, str(self.device))

    def get_prefetched_state_dict(self, fallback_path: str = None) -> Dict[str, torch.Tensor]:
        """Wait for and return the prefetched tensor dict."""
        if self.prefetch_future:
            result = self.prefetch_future.result()
            self.prefetch_future = None
            return result
        elif fallback_path and os.path.exists(fallback_path):
            return load_file(fallback_path, str(self.device))
        return None

    def assign_module_weights(self, module: nn.Module, state_dict: Dict[str, torch.Tensor]):
        """Zero-copy assignment of parameters to empty meta module."""
        if state_dict is None:
            return
        # assign=True requires PyTorch 2.1+ and Replaces parameters with tensors
        module.load_state_dict(state_dict, strict=False, assign=True)
        # Ensure buffers (like causal masks, rotary embeddings) are correctly instantiated on device
        for name, buf in module.named_buffers():
            if buf is not None and buf.device.type == 'meta':
                # Recreate meta buffers directly on target device with zero
                if buf.dtype in [torch.int, torch.long, torch.bool]:
                    module._buffers[name] = torch.zeros_like(buf, device=self.device)
                else:
                    module._buffers[name] = torch.zeros_like(buf, device=self.device, dtype=torch.float16)

    def offload_module(self, module: nn.Module):
        """Free GPU memory by replacing dense parameters with empty CPU tensors."""
        for name, param in module.named_parameters():
             module._parameters[name] = nn.Parameter(torch.empty(0, device="cpu", dtype=param.dtype))
        for name, buf in module.named_buffers():
             if buf is not None:
                 module._buffers[name] = torch.empty(0, device="cpu", dtype=buf.dtype)
        # Free CUDA memory allocator blocks
        torch.cuda.empty_cache()


class CPUOffloadedCache(DynamicCache):
    """
    Seamlessly integrates with HuggingFace layers to keep KV pairs on CPU.
    Tensors move to GPU only during layer execution.
    """
    def __init__(self):
        super().__init__()
        # PyTorch lists tracking CPU tensors internally
        self.key_cache = []
        self.value_cache = []

    def update(
        self,
        key_states: torch.Tensor,
        value_states: torch.Tensor,
        layer_idx: int,
        cache_kwargs: Optional[Dict[str, Any]] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Receives new keys/values on GPU from self-attention block,
        concatenates them to CPU history, and returns full history on GPU.
        """
        if len(self.key_cache) <= layer_idx:
            # First token
            self.key_cache.append(key_states.detach().cpu())
            self.value_cache.append(value_states.detach().cpu())
        else:
            # Subsequent tokens: cat on CPU
            self.key_cache[layer_idx] = torch.cat(
                [self.key_cache[layer_idx], key_states.detach().cpu()], dim=-2
            )
            self.value_cache[layer_idx] = torch.cat(
                [self.value_cache[layer_idx], value_states.detach().cpu()], dim=-2
            )
            
        # Return concatenated cache on GPU for the layer to perform attention
        return (
            self.key_cache[layer_idx].to(key_states.device),
            self.value_cache[layer_idx].to(value_states.device)
        )

    def get_seq_length(self, layer_idx: int = 0) -> int:
        if len(self.key_cache) <= layer_idx:
            return 0
        return self.key_cache[layer_idx].shape[-2]
        
    def get_max_length(self) -> Optional[int]:
        return None
