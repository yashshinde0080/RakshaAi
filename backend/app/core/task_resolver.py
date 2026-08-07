"""Task Resolver - Determines model task type dynamically"""
from typing import Dict, Any, List
from transformers import AutoConfig

class TaskResolver:
    """Resolves task capabilities from HuggingFace config"""
    
    @staticmethod
    def resolve(model_path: str) -> Dict[str, Any]:
        """Inspect model config and determine task descriptors"""
        try:
            config = AutoConfig.from_pretrained(model_path, trust_remote_code=True, local_files_only=True)
        except Exception:
            try:
                config = AutoConfig.from_pretrained(model_path, trust_remote_code=True)
            except Exception as e:
                # Provide a safe default for raw GGUF / unconfigured models
                return {
                    "model_path": model_path,
                    "architectures": ["CausalLM"],
                    "model_type": "unknown",
                    "task_type": "causal_lm",
                    "input_modality": "text",
                    "is_generative": True
                }
                
        architectures: List[str] = getattr(config, "architectures", [])
        model_type: str = getattr(config, "model_type", "").lower()
        is_encoder_decoder: bool = getattr(config, "is_encoder_decoder", False)
        
        # Default assumptions
        task_category = "unknown"
        input_modality = "text"
        is_generative = False
        
        # Mapping common architecture suffixes
        if not architectures:
             # Fallback if architectures is empty
             if "gpt" in model_type or "llama" in model_type or "qwen" in model_type:
                 task_category = "causal_lm"
                 is_generative = True
             elif "bert" in model_type:
                 task_category = "masked_lm"
        else:
            arch = architectures[0].lower()
            
            # Generative language modeling
            if "causallm" in arch:
                task_category = "causal_lm"
                is_generative = True
            elif "seq2seqlm" in arch or "conditionalgeneration" in arch:
                task_category = "seq2seq_lm"
                is_generative = True
            elif "maskedlm" in arch:
                task_category = "masked_lm"
            
            # Classification
            elif "sequenceclassification" in arch:
                task_category = "sequence_classification"
            elif "tokenclassification" in arch:
                task_category = "token_classification"
            elif "multiplechoice" in arch:
                task_category = "multiple_choice"
            elif "nextsentenceprediction" in arch:
                task_category = "next_sentence"
            elif "videoclassification" in arch:
                task_category = "video_classification"
            elif "audioframeclassification" in arch:
                task_category = "audio_frame_classification"
            elif "audioxvector" in arch:
                task_category = "audio_xvector"
                
            # Question Answering
            elif "questionanswering" in arch:
                task_category = "question_answering"
            elif "tablequestionanswering" in arch:
                task_category = "table_qa"
            elif "documentquestionanswering" in arch:
                task_category = "document_qa"
            elif "visualquestionanswering" in arch:
                task_category = "visual_qa"
                input_modality = "multimodal"
                
            # Vision tasks
            elif "imageclassification" in arch:
                task_category = "image_classification"
                input_modality = "image"
            elif "objectdetection" in arch:
                task_category = "object_detection"
                input_modality = "image"
            elif "zeroshotobjectdetection" in arch:
                task_category = "zero_shot_object_detection"
                input_modality = "image"
            elif "imagesegmentation" in arch:
                task_category = "image_segmentation"
                input_modality = "image"
            elif "semanticsegmentation" in arch:
                task_category = "semantic_segmentation"
                input_modality = "image"
            elif "instancesegmentation" in arch:
                task_category = "instance_segmentation"
                input_modality = "image"
            elif "depthestimation" in arch:
                task_category = "depth_estimation"
                input_modality = "image"
            elif "maskedimagemodeling" in arch:
                task_category = "masked_image_modeling"
                input_modality = "image"
            elif "imagetoimage" in arch:
                task_category = "image_to_image"
                input_modality = "image"
            elif "vision2seq" in arch or "llava" in model_type or "qwen" in model_type:
                task_category = "vision2seq"
                input_modality = "multimodal"
                is_generative = True
                
            # Audio tasks
            elif "audioclassification" in arch:
                task_category = "audio_classification"
                input_modality = "audio"
            elif "ctc" in arch:
                task_category = "ctc"
                input_modality = "audio"
            elif "speechseq2seq" in arch or "whisper" in model_type:
                task_category = "speech_seq2seq"
                input_modality = "audio"
                is_generative = True
            elif "texttospectrogram" in arch:
                task_category = "text_to_spectrogram"
            elif "texttowaveform" in arch:
                task_category = "text_to_waveform"
            
            # Embeddings and Encodings
            elif "pretraining" in arch:
                task_category = "pretraining"
            elif "model" in arch and not is_generative and task_category == "unknown":
                 # generic bare models (Backbone-only)
                 task_category = "text_encoding"
                 
        # Additional heuristics: check for multimodal configs
        if hasattr(config, "vision_config") or hasattr(config, "visual_config"):
            task_category = "vision2seq"
            input_modality = "multimodal"
            is_generative = True
            
        # Additional heuristics
        elif is_encoder_decoder and task_category == "unknown":
            task_category = "seq2seq_lm"
            is_generative = True
            
        return {
            "model_path": model_path,
            "architectures": architectures,
            "model_type": model_type,
            "task_type": task_category,
            "input_modality": input_modality,
            "is_generative": is_generative
        }
