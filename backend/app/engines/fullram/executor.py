"""FullRAM Execution Engine"""
import asyncio
import time
import os
from typing import Dict, Any, AsyncGenerator, Optional
import numpy as np

import torch
from transformers import AutoProcessor, AutoTokenizer, TextIteratorStreamer, AutoImageProcessor
from threading import Thread
import psutil

from app.engines.base import BaseEngine
from app.core.task_resolver import TaskResolver
from app.core.task_router import TaskRouter


class _IkModelWrapper:
    """Thin wrapper: IkLlama -> llama_cpp.Llama API subset used by FullRAMEngine."""
    def __init__(self, inner):
        self._inner = inner

    def create_chat_completion(self, messages, **kwargs):
        kwargs.pop("stream", None)  # ik_llama.cpp doesn't support stream
        return self._inner.create_chat_completion(messages=messages, **kwargs)

    def __call__(self, prompt, **kwargs):
        max_tokens = kwargs.pop("max_tokens", 512)
        tokens = self._inner.tokenize(prompt)
        out = self._inner.generate(tokens, max_tokens=max_tokens)
        text = self._inner.detokenize(out)
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        return {"choices": [{"text": text}], "usage": {"completion_tokens": len(out)}}

class FullRAMEngine(BaseEngine):
    """Full RAM inference engine - loads entire model into memory dynamically"""
    
    def __init__(self, model_path: str, hardware: Dict[str, Any], memory_manager: Any):
        super().__init__(model_path, hardware, memory_manager)
        self.mode = "fullram"
        self.processor = None
        self.tokenizer = None
        self.model = None
        self.task_metadata = {}
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
    
    async def load(self):
        """Load model into RAM dynamically based on task"""
        start_time = time.time()
        
        try:
            # 1. Resolve task
            self.task_metadata = TaskResolver.resolve(self.model_path)
            task_type = self.task_metadata["task_type"]
            input_modality = self.task_metadata["input_modality"]
            is_generative = self.task_metadata["is_generative"]
            
            # 2. Get Appropriate Class
            model_class = TaskRouter.TASK_CLASS_MAP.get(task_type)
            if not model_class:
                raise ValueError(f"Unsupported task type: {task_type}")
                
            model_kwargs = {
                "trust_remote_code": True,
                "low_cpu_mem_usage": True,
                "ignore_mismatched_sizes": True

            }
            
            if self.device == "cuda":
                model_kwargs["device_map"] = "auto"
                model_kwargs["dtype"] = torch.float16
            else:
                model_kwargs["device_map"] = "cpu"
                model_kwargs["dtype"] = torch.float32
                
            if self.model_path.endswith(".gguf") or self.model_path.endswith(".gguf.enc"):
                model_dir = os.path.dirname(self.model_path)
                model_kwargs["gguf_file"] = os.path.basename(self.model_path)
                # GGUF loading relies heavily on AutoConfig dynamic bridging locally
                self.model = model_class.from_pretrained(model_dir, **model_kwargs)
            else:
                # torch < 2.6 refuses .bin checkpoints (CVE-2025-32434); convert to safetensors first
                from app.engines.shared.safetensors import ensure_safetensors
                ensure_safetensors(self.model_path)
                self.model = model_class.from_pretrained(
                    self.model_path,
                    **model_kwargs
                )
            
            # 3. Load Processors
            if input_modality == "text" or is_generative:
                try:
                     tok_kwargs = {
                         "trust_remote_code": True,
                     }
                     if self.model_path.endswith(".gguf") or self.model_path.endswith(".gguf.enc"):
                         tok_kwargs["gguf_file"] = os.path.basename(self.model_path)
                         tok_dir = os.path.dirname(self.model_path)
                     else:
                         tok_dir = self.model_path
                     
                     self.tokenizer = AutoTokenizer.from_pretrained(tok_dir, **tok_kwargs)
                     if not self.tokenizer.pad_token:
                         self.tokenizer.pad_token = self.tokenizer.eos_token
                except Exception as e:
                     print(f"Failed loading tokenizer from repo natively: {e}")
                     pass
                     
            if input_modality in ["image", "multimodal"]:
                try:
                    self.processor = AutoProcessor.from_pretrained(
                        self.model_path, trust_remote_code=True
                    )
                except Exception:
                    try:
                        self.processor = AutoImageProcessor.from_pretrained(
                            self.model_path, trust_remote_code=True
                        )
                    except:
                        raise RuntimeError(f"Missing required processor for vision task")
            
            if input_modality == "audio":
                try:
                    self.processor = AutoProcessor.from_pretrained(
                        self.model_path, trust_remote_code=True
                    )
                except:
                    raise RuntimeError("Missing processor for audio task")
                
            self.loaded = True
            self.stats["load_time"] = time.time() - start_time
            print(f"Loaded {self.model_path} [{task_type}] in {self.mode} on {self.device}")
            
        except Exception as e:
            self.loaded = False
            msg = str(e)
            # Transformers rejects architectures it can't parse with exactly
            # these phrases (see /v1/models/load, which maps them to 422).
            # Any such failure means transformers can't run this model, so try
            # llama.cpp before giving up — never silently drop the fallback.
            if "not supported" in msg or "architecture" in msg:
                # Check if this is an ik_llama.cpp-only model (IQ2_BN, etc.)
                basename = os.path.basename(self.model_path).lower()
                is_ik_only = any(tag in basename for tag in ("iq2_bn", "iq2_bnr4", "iq2_bn_r4"))
                
                # Try ik_llama.cpp first (handles BitNet / IQ2_BN models)
                try:
                    from ik_llama_cpp import IkLlama
                    print(f"ik_llama.cpp: loading {self.model_path}")
                    self.model = _IkModelWrapper(IkLlama(model_path=self.model_path, n_ctx=2048, verbose=False))
                    self.is_llama_cpp = True
                    self.is_ik_backend = True
                    self.loaded = True
                    self.task_metadata = {"task_type": "causal_lm", "is_generative": True, "input_modality": "text"}
                    self.stats["load_time"] = time.time() - start_time
                    print(f"Loaded {self.model_path} [ik_llama.cpp] in {self.mode}")
                    return
                except ImportError:
                    print("ik_llama.cpp not installed, trying llama_cpp fallback")
                except Exception as ik_err:
                    print(f"ik_llama.cpp fallback failed: {ik_err}")

                # Fall back to standard llama_cpp
                try:
                    from llama_cpp import Llama
                    print(f"llama_cpp fallback: loading {self.model_path}")
                    self.model = Llama(model_path=self.model_path, n_ctx=2048, verbose=False)
                    self.is_llama_cpp = True
                    self.loaded = True
                    self.task_metadata = {"task_type": "causal_lm", "is_generative": True, "input_modality": "text"}
                    self.stats["load_time"] = time.time() - start_time
                    print(f"Loaded {self.model_path} [llama_cpp fallback] in {self.mode}")
                    return
                except Exception as llama_err:
                    print(f"llama_cpp fallback failed: {llama_err}")

                # Both backends failed — give a targeted error
                if is_ik_only:
                    raise RuntimeError(
                        f"This model uses IQ2_BN quantization which requires ik_llama.cpp (a fork), "
                        f"not standard llama.cpp or Transformers. Use a standard GGUF quantization "
                        f"(Q4_K_M, Q5_K_M, Q8_0) or a supported architecture."
                    )
                raise RuntimeError(
                    f"Model architecture not supported by PyTorch/Transformers or llama-cpp-python. "
                    f"Use a GGUF model quantized from a standard architecture (Llama, Mistral, "
                    f"Qwen2, Gemma, Phi-3, Falcon, DeepSeek, etc.). Check the error above for "
                    f"the specific architecture name that failed."
                )
            raise RuntimeError(f"Failed to load model dynamically: {e}")
    
    async def unload(self):
        """Unload model from RAM"""
        if self.model:
            del self.model
            self.model = None
        
        if self.tokenizer:
            del self.tokenizer
            self.tokenizer = None
            
        if self.processor:
            del self.processor
            self.processor = None
            
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self.loaded = False
    
    async def generate(self, input_data: Any, **kwargs) -> Dict[str, Any]:
        """Unified Execute Endpoint"""
        if not self.loaded:
            raise RuntimeError("Model not loaded")
            
        task_type = self.task_metadata["task_type"]
        is_generative = self.task_metadata["is_generative"]
        modality = self.task_metadata["input_modality"]
        
        start_time = time.perf_counter()
        
        if getattr(self, "is_llama_cpp", False):
            import asyncio
            if isinstance(input_data, list) or (isinstance(input_data, dict) and "messages" in input_data):
                msgs = input_data if isinstance(input_data, list) else input_data["messages"]
                res = await asyncio.to_thread(self.model.create_chat_completion, messages=msgs, max_tokens=kwargs.get("max_tokens", 512))
                output_res = res["choices"][0]["message"]["content"]
                tokens = res["usage"]["completion_tokens"]
            else:
                prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
                res = await asyncio.to_thread(self.model, prompt, max_tokens=kwargs.get("max_tokens", 512))
                output_res = res["choices"][0]["text"]
                tokens = res["usage"]["completion_tokens"]
                
            return {
                "model_name": os.path.basename(self.model_path),
                "task_type": task_type,
                "mode": self.mode,
                "input": "provided inputs", 
                "output": output_res,
                "confidence": "1.0000",
                "metadata": {
                    "ram_usage": f"{self.get_memory_usage()['ram_used_gb']:.2f}GB",
                    "latency": f"{time.perf_counter() - start_time:.3f}s",
                    "tokens_generated": str(tokens)
                }
            }

        # 1. Process inputs dynamically
        processed_inputs = {}
        prompt_tokens = 0
        
        # Determine modality-based input processing
        if task_type == "question_answering":
             prompt = input_data.get("question", "")
             context = input_data.get("context", "")
             processed_inputs = self.tokenizer(prompt, context, return_tensors="pt")
             prompt_tokens = processed_inputs.input_ids.shape[1]
             
        elif modality == "image":
             image = input_data.get("image")
             processed_inputs = self.processor(images=image, return_tensors="pt")
             
        elif modality == "audio":
             audio = input_data.get("audio")
             processed_inputs = self.processor(audio=audio, return_tensors="pt")
             
        elif modality == "multimodal":
             if isinstance(input_data, str):
                 prompt = input_data
                 image = None
             elif isinstance(input_data, list):
                 if self.tokenizer:
                     prompt = self.tokenizer.apply_chat_template(input_data, tokenize=False, add_generation_prompt=True)
                 else:
                     prompt = str(input_data)
                 image = None
             else:
                 image = input_data.get("image")
                 if "messages" in input_data and self.tokenizer:
                     prompt = self.tokenizer.apply_chat_template(input_data["messages"], tokenize=False, add_generation_prompt=True)
                 else:
                     prompt = input_data.get("prompt", "")
             
             if image is not None and self.processor:
                 processed_inputs = self.processor(text=prompt, images=image, return_tensors="pt")
             elif self.tokenizer:
                 processed_inputs = self.tokenizer(prompt, return_tensors="pt")
             else:
                 raise RuntimeError("No tokenizer or processor found for text input in multimodal mode.")
             
             prompt_tokens = processed_inputs.input_ids.shape[1] if hasattr(processed_inputs, "input_ids") else 0
             
        else: # Default: Text
             if not self.tokenizer:
                 raise RuntimeError("Model requires a tokenizer but none was loaded.")
             
             if isinstance(input_data, list):
                 # Assume chat messages
                 prompt = self.tokenizer.apply_chat_template(input_data, tokenize=False, add_generation_prompt=True)
             elif isinstance(input_data, dict) and "messages" in input_data:
                 prompt = self.tokenizer.apply_chat_template(input_data["messages"], tokenize=False, add_generation_prompt=True)
             else:
                 prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
                 
             processed_inputs = self.tokenizer(prompt, return_tensors="pt")
             prompt_tokens = processed_inputs.input_ids.shape[1]
             
        if is_generative:
             max_tokens = kwargs.get("max_tokens", 512)
             temperature = kwargs.get("temperature", 0.7)
             top_p = kwargs.get("top_p", 0.9)
             
             gen_kwargs = {
                 "max_new_tokens": max_tokens,
                 "temperature": temperature if temperature > 0 else 1.0,
                 "do_sample": temperature > 0,
                 "top_p": top_p
             }
             if self.tokenizer and self.tokenizer.eos_token_id is not None:
                  gen_kwargs["pad_token_id"] = self.tokenizer.eos_token_id
             processed_inputs["generation_kwargs"] = gen_kwargs

        # 2. Route Execution via TaskRouter for unified logic
        result = await TaskRouter.execute(
            model=self.model,
            task_metadata=self.task_metadata,
            inputs=processed_inputs,
            device=self.device
        )
        
        # 3. Process outputs dynamically for user reporting
        output_res = result.get("output")
        confidence = result.get("confidence", 1.0)
        completion_tokens = 0
        predictions = []  # structured top-k candidates (masked_lm)
        message = None  # plain-text note for non-generative tasks (masked_lm)
        finish_reason = "stop"
        
        if is_generative:
            output_ids = output_res[0]  # TaskRouter returns output_ids for generative
            # Strip the prompt for all generative modalities (text, multimodal/vision2seq);
            # prompt_tokens == 0 is a no-op. Previously only text was sliced, so vision2seq
            # (e.g. Qwen3.5) echoed the whole rendered prompt in the response.
            if prompt_tokens > 0 and len(output_ids) >= prompt_tokens:
                output_ids = output_ids[prompt_tokens:]
            
            output_res = self.tokenizer.decode(output_ids, skip_special_tokens=True)
            completion_tokens = len(output_ids)
            # Honest truncation signal: hitting max_new_tokens means "length".
            # (Previously always reported "stop", which hid thinking-mode
            # truncation — reasoning eats the whole budget and content comes
            # out empty.)
            if completion_tokens >= max_tokens:
                finish_reason = "length"
            
        elif task_type == "question_answering":
            # Extract text from QA logits
            start_logits = result["start_logits"]
            end_logits = result["end_logits"]
            answer_start = torch.argmax(start_logits)
            answer_end = torch.argmax(end_logits) + 1
            answer_tokens = processed_inputs["input_ids"][0][answer_start:answer_end]
            output_res = self.tokenizer.decode(answer_tokens)
            completion_tokens = len(answer_tokens)
            
        elif task_type == "masked_lm":
            # BERT-style [MASK] prediction — structured top-k candidates per mask position.
            # Plain-text cases go to the dedicated 'message' field; 'output' stays empty.
            output_res = ""
            mask_token_id = getattr(self.tokenizer, "mask_token_id", None)
            input_ids = processed_inputs["input_ids"][0]
            if mask_token_id is None:
                message = "Tokenizer has no mask_token_id; cannot predict [MASK]."
            else:
                mask_positions = (input_ids == mask_token_id).nonzero(as_tuple=True)[0]
                if len(mask_positions) == 0:
                    message = "No [MASK] tokens found in input."
                else:
                    logits = result["logits"][0]  # [seq_len, vocab]
                    probs = logits.softmax(dim=-1)
                    for pos in mask_positions:
                        topk_vals, topk_ids = probs[pos].topk(5)
                        tokens = self.tokenizer.convert_ids_to_tokens(topk_ids.tolist())
                        candidates = [
                            {"token": t, "probability": round(float(p), 4)}
                            for t, p in zip(tokens, topk_vals.tolist())
                        ]
                        predictions.append({"position": int(pos.item()), "candidates": candidates})

        elapsed = time.perf_counter() - start_time
        
        return {
            "model_name": self.model_path.split("/")[-1] if "/" in self.model_path else self.model_path.split("\\")[-1],
            "task_type": task_type,
            "mode": self.mode,
            "input": "provided inputs", 
            "output": output_res,
            "finish_reason": finish_reason,
            "confidence": f"{confidence:.4f}",
            "predictions": predictions,
            "message": message,
            "metadata": {
                "ram_usage": f"{self.get_memory_usage()['ram_used_gb']:.2f}GB",
                "latency": f"{elapsed:.3f}s",
                "tokens_generated": str(completion_tokens) if is_generative else "N/A"
            }
        }
    
    async def generate_stream(self, input_data: Any, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Streaming endpoint for generative models"""
        if not self.task_metadata.get("is_generative"):
            raise RuntimeError("Selected model does not support streaming generation.")
            
        if not self.loaded:
            raise RuntimeError("Model not loaded")

        task_type = self.task_metadata["task_type"]
        modality = self.task_metadata["input_modality"]
        
        if getattr(self, "is_llama_cpp", False):
            if isinstance(input_data, list) or (isinstance(input_data, dict) and "messages" in input_data):
                msgs = input_data if isinstance(input_data, list) else input_data["messages"]

                if getattr(self, "is_ik_backend", False):
                    # ik_llama.cpp doesn't support streaming — yield full output
                    res = self.model.create_chat_completion(
                        messages=msgs, max_tokens=kwargs.get("max_tokens", 512)
                    )
                    yield {"token": res["choices"][0]["message"]["content"], "finish_reason": None}
                else:
                    for chunk in self.model.create_chat_completion(
                        messages=msgs, max_tokens=kwargs.get("max_tokens", 512), stream=True
                    ):
                        delta = chunk["choices"][0].get("delta", {})
                        if "content" in delta:
                            yield {"token": delta["content"], "finish_reason": None}
            else:
                prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
                if getattr(self, "is_ik_backend", False):
                    res = self.model(prompt, max_tokens=kwargs.get("max_tokens", 512))
                    yield {"token": res["choices"][0]["text"], "finish_reason": None}
                else:
                    for chunk in self.model(prompt, max_tokens=kwargs.get("max_tokens", 512), stream=True):
                        text = chunk["choices"][0].get("text", "")
                        if text:
                            yield {"token": text, "finish_reason": None}
            yield {"token": "", "finish_reason": "stop"}
            return

        # 1. Process inputs
        if not self.tokenizer:
            raise RuntimeError("Model requires a tokenizer but none was loaded.")
            
        if isinstance(input_data, list):
            # Assume chat messages
            prompt = self.tokenizer.apply_chat_template(input_data, tokenize=False, add_generation_prompt=True)
        elif isinstance(input_data, dict) and "messages" in input_data:
            prompt = self.tokenizer.apply_chat_template(input_data["messages"], tokenize=False, add_generation_prompt=True)
        else:
            prompt = input_data if isinstance(input_data, str) else input_data.get("prompt", "")
            
        inputs = self.tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        # 2. Setup streamer
        streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
        
        max_tokens = kwargs.get("max_tokens", 512)
        temperature = kwargs.get("temperature", 0.7)
        top_p = kwargs.get("top_p", 0.9)
        
        gen_kwargs = {
            **inputs,
            "streamer": streamer,
            "max_new_tokens": max_tokens,
            "temperature": temperature if temperature > 0 else 1.0,
            "do_sample": temperature > 0,
            "top_p": top_p
        }

        
        if self.tokenizer and self.tokenizer.eos_token_id is not None:
             gen_kwargs["pad_token_id"] = self.tokenizer.eos_token_id

        # 3. Run generation in thread
        thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
        thread.start()

        # 4. Yield tokens
        for new_text in streamer:
            yield {"token": new_text, "finish_reason": None}
            
        yield {"token": "", "finish_reason": "stop"}

    def get_memory_usage(self) -> Dict[str, Any]:
        process = psutil.Process()
        return {
            "ram_used_gb": process.memory_info().rss / (1024**3),
            "peak_ram_gb": process.memory_info().peak_wset / (1024**3) if hasattr(process.memory_info(), 'peak_wset') else 0,
            "kv_cache_mb": 0
        }
