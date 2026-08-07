# SovereignAI Edge — Architecture Compatibility Matrix

> **Last updated**: 2026-07-29  
> **Source**: `app/core/task_resolver.py` (task detection; legacy `model_manager/` package deleted)  
> **Transformers version**: v4.46+

This document lists every HuggingFace model architecture supported by SovereignAI's architecture detection layer. `app/core/task_resolver.py` suffix‑matches **any** `*ForCausalLM`, `*ForMaskedLM`, etc. automatically — explicit entries here are for documentation + the `model_type` fallback.

**Detection priority**: `config.json` `architectures[]` → suffix match → `model_type` fallback → default `CAUSAL_LM`.

---

## Legend

| Column | Meaning |
|--------|---------|
| ✅ Full | Works in FullRAM engine (default) |
| ✅ LS | Works in LayerStream engine (manual layer loading) |
| ⚠️ | Known limitation or requires testing |
| ❌ | Not supported |
| ✓ | Architecture class name used in `TaskResolver` fallback |
| - | Not applicable or untested |

---

## Causal LM (text generation)

All architectures auto‑detected via suffix `*ForCausalLM` / `*LMHeadModel`. FullRAM and LayerStream engines use `AutoModelForCausalLM.from_pretrained()`.

| HF Architecture Class | `model_type` | FullRAM | LayerStream | MoE | Notes |
|---|---|---|---|---|---|
| `LlamaForCausalLM` | `llama` | ✅ | ✅ | | Foundation — most tested |
| `MistralForCausalLM` | `mistral` | ✅ | ✅ | | Sliding window attention |
| `MixtralForCausalLM` | `mixtral` | ✅ | ✅ | ✅ | Top‑2 MoE |
| `Qwen2ForCausalLM` | `qwen2` | ✅ | ✅ | | High‑context, RoPE |
| `Qwen2MoeForCausalLM` | `qwen2_moe` | ✅ | ✅ | ✅ | Qwen2 MoE variant |
| `Qwen3ForCausalLM` | `qwen3` | ✅ | ✅ | | Qwen 3 series |
| `Qwen3_5ForCausalLM` | `qwen3_5` | ✅ | ✅ | | Hybrid attn (Qwen3.5) |
| `Qwen3MoeForCausalLM` | `qwen3_moe` | ✅ | ✅ | ✅ | Qwen3 MoE |
| `GemmaForCausalLM` | `gemma` | ✅ | ✅ | | Google Gemma |
| `Gemma2ForCausalLM` | `gemma2` | ✅ | ✅ | | Gemma2 — logit soft‑capping |
| `RecurrentGemmaForCausalLM` | `recurrent_gemma` | ✅ | ✅ | | State‑space + attn hybrid |
| `PhiForCausalLM` | `phi` | ✅ | ✅ | | Phi‑1 / Phi‑1.5 |
| `Phi3ForCausalLM` | `phi3` | ✅ | ✅ | | Phi‑3 mini/medium |
| `FalconForCausalLM` | `falcon` | ✅ | ⚠️ | | Uses `transformer.h.N` layer naming |
| `CohereForCausalLM` | `cohere` | ✅ | ✅ | | Cohere Command R |
| `OPTForCausalLM` | `opt` | ✅ | ✅ | | Meta OPT |
| `BloomForCausalLM` | `bloom` | ✅ | ✅ | | BigScience BLOOM |
| `StableLmForCausalLM` | `stablelm` | ✅ | ✅ | | Stability AI |
| `GPT2LMHeadModel` | `gpt2` | ✅ | ✅ | | GPT‑2 |
| `GPTNeoForCausalLM` | `gpt_neo` | ✅ | ✅ | | EleutherAI GPT‑Neo |
| `GPTNeoXForCausalLM` | `gpt_neox` | ✅ | ✅ | | EleutherAI GPT‑NeoX‑20B |
| `GPTJForCausalLM` | `gptj` | ✅ | ✅ | | EleutherAI GPT‑J |
| `Starcoder2ForCausalLM` | `starcoder2` | ✅ | ✅ | | HF StarCoder2 |
| `DeepseekV2ForCausalLM` | `deepseek_v2` | ✅ | ✅ | ✅ | DeepSeek V2 (MoE) |
| `DeepseekV3ForCausalLM` | `deepseek_v3` | ✅ | ✅ | ✅ | DeepSeek V3 (MoE) |
| `DeepseekV4ForCausalLM` | `deepseek_v4` | ✅ | ✅ | ✅ | DeepSeek V4 (MoE) |
| `DbrxForCausalLM` | `dbrx` | ✅ | ✅ | ✅ | Databricks DBRX (MoE) |
| `JambaForCausalLM` | `jamba` | ✅ | ✅ | ✅ | AI21 Jamba (MoE+SSM) |
| `OlmoForCausalLM` | `olmo` | ✅ | ✅ | | AI2 OLMo |
| `Olmo2ForCausalLM` | `olmo2` | ✅ | ✅ | | AI2 OLMo 2 |
| `Olmo3ForCausalLM` | `olmo3` | ✅ | ✅ | | AI2 OLMo 3 |
| `Exaone4ForCausalLM` | `exaone4` | ✅ | ✅ | | LG EXAONE 4 |
| `ExaoneMoeForCausalLM` | `exaone_moe` | ✅ | ✅ | ✅ | LG EXAONE MoE |
| `BitNetForCausalLM` | `bitnet` | ✅ | ⚠️ | | 1.58‑bit ternary weights |
| `MptForCausalLM` | `mpt` | ✅ | ⚠️ | | MosaicML MPT — ALiBi attn |
| `MambaForCausalLM` | `mamba` | ✅ | ⚠️ | | SSM — no attn, conv‑only |
| `Mamba2ForCausalLM` | `mamba2` | ✅ | ⚠️ | | Mamba 2 (SSM) |
| `GraniteForCausalLM` | `granite` | ✅ | ✅ | | IBM Granite |
| `GraniteMoeForCausalLM` | `granitemoe` | ✅ | ✅ | ✅ | IBM Granite MoE |
| `NemotronForCausalLM` | `nemotron` | ✅ | ✅ | | NVIDIA Nemotron |
| `PersimmonForCausalLM` | `persimmon` | ✅ | ✅ | | Adept Persimmon‑8B |
| `MinistralForCausalLM` | `ministral` | ✅ | ✅ | | Mistral Ministral |
| `SolarOpenForCausalLM` | `solar_open` | ✅ | ✅ | | Upstage SOLAR |
| `JetMoeForCausalLM` | `jetmoe` | ✅ | ✅ | ✅ | JetMoE (by my‑local‑dolphin) |
| `BambaForCausalLM` | `bamba` | ✅ | ✅ | | Bamba (SSM + attn) |
| `MiniCPM3ForCausalLM` | `minicpm3` | ✅ | ✅ | | MiniCPM‑3 |
| `GlmForCausalLM` | `glm` | ✅ | ✅ | | THUDM GLM |
| `Glm4ForCausalLM` | `glm4` | ✅ | ✅ | | THUDM GLM‑4 |
| `ZambaForCausalLM` | `zamba` | ✅ | ⚠️ | | Zyphra Zamba (SSM+attn) |
| `Zamba2ForCausalLM` | `zamba2` | ✅ | ⚠️ | | Zyphra Zamba 2 |
| `RwkvForCausalLM` | `rwkv` | ✅ | ⚠️ | | RWKV (RNN‑style) |
| `XGLMForCausalLM` | `xglm` | ✅ | ✅ | | Meta XGLM (multilingual) |
| `CodeGenForCausalLM` | `codegen` | ✅ | ✅ | | Salesforce CodeGen |
| `GPTBigCodeForCausalLM` | `gpt_bigcode` | ✅ | ✅ | | BigCode (SantaCoder, StarCoder) |
| `BioGptForCausalLM` | `biogpt` | ✅ | ✅ | | Microsoft BioGPT |
| `GitForCausalLM` | `git` | ✅ | | | GenerativeImage2Text |
| `ApertusForCausalLM` | `apertus` | ✅ | ✅ | | Apertus |
| `ArceeForCausalLM` | `arcee` | ✅ | ✅ | | Arcee |
| `HeliumForCausalLM` | `helium` | ✅ | ✅ | | Helium |
| `DiffLlamaForCausalLM` | `diffllama` | ✅ | ✅ | | Diffusion‑augmented Llama |
| `BltForCausalLM` | `blt` | ✅ | ✅ | | Byte‑Level Transformer |
| `NanoChatForCausalLM` | `nanochat` | ✅ | ✅ | | NanoChat |
| `SmolLM3ForCausalLM` | `smollm3` | ✅ | ✅ | | HuggingFace SmolLM3 |
| `InternLM2ForCausalLM` | `internlm2` | ✅ | ✅ | | InternLM 2 |

---

## Masked LM (embedding / classification)

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `BertForMaskedLM` | `bert` | ✅ | N/A | No streaming for masked LMs |
| `RobertaForMaskedLM` | `roberta` | ✅ | N/A | |
| `AlbertForMaskedLM` | `albert` | ✅ | N/A | |
| `DebertaForMaskedLM` | `deberta` | ✅ | N/A | |
| `DebertaV2ForMaskedLM` | `deberta-v2` | ✅ | N/A | |
| `ModernBertForMaskedLM` | `modernbert` | ✅ | N/A | |
| `CamembertForMaskedLM` | `camembert` | ✅ | N/A | |
| `FlaubertWithLMHeadModel` | `flaubert` | ✅ | N/A | |
| `DistilBertForMaskedLM` | `distilbert` | ✅ | N/A | |
| `XLMRobertaForMaskedLM` | `xlm-roberta` | ✅ | N/A | |
| `CanineForMaskedLM` | `canine` | ✅ | N/A | |
| `LayoutLMForMaskedLM` | `layoutlm` | ✅ | N/A | |
| `LongformerForMaskedLM` | `longformer` | ✅ | N/A | |
| `ElectraForPreTraining` | `electra` | ✅ | N/A | |
| `MobileBertForMaskedLM` | `mobilebert` | ✅ | N/A | |
| `BigBirdForMaskedLM` | `big_bird` | ✅ | N/A | |
| `FunnelForPreTraining` | `funnel` | ✅ | N/A | |
| `NystromformerForMaskedLM` | `nystromformer` | ✅ | N/A | |
| `ReformerModelWithLMHead` | `reformer` | ✅ | N/A | |
| `RoFormerForCausalLM` | `roformer` | ✅ | N/A | |

---

## Seq2Seq LM

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `T5ForConditionalGeneration` | `t5` | ✅ | N/A | Encoder‑decoder |
| `BartForConditionalGeneration` | `bart` | ✅ | N/A | |
| `MBartForConditionalGeneration` | `mbart` | ✅ | N/A | Multilingual BART |
| `PegasusForConditionalGeneration` | `pegasus` | ✅ | N/A | |
| `MarianMTModel` | `marian` | ✅ | N/A | |
| `MT5ForConditionalGeneration` | `mt5` | ✅ | N/A | Multilingual T5 |
| `FlanT5ForConditionalGeneration` | `flan-t5` | ✅ | N/A | |
| `LongT5ForConditionalGeneration` | `longt5` | ✅ | N/A | |
| `M2M100ForConditionalGeneration` | `m2m_100` | ✅ | N/A | |
| `BigBirdPegasusForConditionalGeneration` | `bigbird_pegasus` | ✅ | N/A | |
| `BlenderbotForConditionalGeneration` | `blenderbot` | ✅ | N/A | |
| `FSMTForConditionalGeneration` | `fsmt` | ✅ | N/A | |
| `LEDForConditionalGeneration` | `led` | ✅ | N/A | |
| `NllbMoeForConditionalGeneration` | `nllb-moe` | ✅ | N/A | MoE seq2seq |
| `PLBartForConditionalGeneration` | `plbart` | ✅ | N/A | |
| `SwitchTransformersForConditionalGeneration` | `switch_transformers` | ✅ | N/A | MoE seq2seq |
| `UMT5ForConditionalGeneration` | `umt5` | ✅ | N/A | |
| `SeamlessM4TForConditionalGeneration` | `seamless_m4t` | ✅ | N/A | Speech + text |
| `WhisperForConditionalGeneration` | `whisper` | ✅ | N/A | Speech‑to‑text |

---

## Speech Seq2Seq

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `WhisperForConditionalGeneration` | `whisper` | ✅ | N/A | Also in Seq2Seq |
| `Speech2TextForConditionalGeneration` | `speech_to_text` | ✅ | N/A | |
| `SpeechT5ForConditionalGeneration` | `speecht5` | ✅ | N/A | |

---

## Vision2Seq (multimodal)

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `LlavaForConditionalGeneration` | `llava` | ✅ | ⚠️ | Vision‑language |
| `LlavaNextForConditionalGeneration` | `llava_next` | ✅ | ⚠️ | |
| `Blip2ForConditionalGeneration` | `blip-2` | ✅ | N/A | Q‑former bridge |
| `VisionEncoderDecoderModel` | - | ✅ | N/A | Generic VED |
| `PaliGemmaForConditionalGeneration` | `paligemma` | ✅ | ⚠️ | |
| `FuyuForCausalLM` | `fuyu` | ✅ | ⚠️ | |

---

## Image Classification

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `ViTForImageClassification` | `vit` | ✅ | N/A | |
| `SwinForImageClassification` | `swin` | ✅ | N/A | |
| `DeiTForImageClassification` | `deit` | ✅ | N/A | |
| `BeitForImageClassification` | `beit` | ✅ | N/A | |
| `ConvNextForImageClassification` | `convnext` | ✅ | N/A | |
| `ResNetForImageClassification` | `resnet` | ✅ | N/A | |
| `EfficientNetForImageClassification` | `efficientnet` | ✅ | N/A | |
| `Dinov2ForImageClassification` | `dinov2` | ✅ | N/A | |

---

## Object Detection

| HF Architecture Class | `model_type` | FullRAM | LayerStream | Notes |
|---|---|---|---|---|
| `DetrForObjectDetection` | `detr` | ✅ | N/A | |
| `YolosForObjectDetection` | `yolos` | ✅ | N/A | |

---

## FAQ

**Q: How does detection actually work?**  
A: `app/core/task_resolver.py` reads `config.json`: (1) architecture suffix match (any `*ForCausalLM` → `CAUSAL_LM`, etc.), (2) `model_type` heuristics, (3) default `CAUSAL_LM` for raw GGUF.

**Q: My architecture isn't listed — will it work?**  
A: Probably! If its class name ends with `ForCausalLM`, `ForMaskedLM`, `ForSequenceClassification`, etc., the suffix match in `app/core/task_resolver.py` catches it automatically.

**Q: What does "LayerStream: ⚠️" mean?**  
A: The architecture is not yet tested with LayerStream's manual layer‑loading loop. Non‑standard layer internals (SSM, MoE hierachies, ALiBi, custom norms) may need minor `layer_executor.py` adjustments. These generally work but haven't been validated.

**Q: Can I add a missing entry?**  
A: Yes. (1) Extend the mapping in `app/core/task_resolver.py`. (2) Update this doc.
