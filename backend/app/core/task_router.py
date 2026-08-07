"""Task Router for Unified Execution"""
from typing import Dict, Any, Type, Optional
try:
    from transformers import AutoModelForVision2Seq
except ImportError:
    # Older name, might be replaced in newer versions by AutoModelForMultimodalLM
    AutoModelForVision2Seq = None

try:
    from transformers import AutoModelForMultimodalLM
except ImportError:
    AutoModelForMultimodalLM = None

try:
    from transformers import AutoModelForImageTextToText
except ImportError:
    AutoModelForImageTextToText = None

from transformers import (
    AutoModelForCausalLM, AutoModelForSequenceClassification,
    AutoModelForQuestionAnswering, AutoModelForImageClassification,
    AutoModelForMaskedLM, AutoModelForSeq2SeqLM, AutoModelForTokenClassification,
    AutoModelForAudioClassification,
    AutoModelForSpeechSeq2Seq, AutoModelForTextEncoding,
    # Newly expanded classes
    AutoModelForMultipleChoice, AutoModelForNextSentencePrediction,
    AutoModelForVideoClassification, AutoModelForTableQuestionAnswering,
    AutoModelForDocumentQuestionAnswering, AutoModelForVisualQuestionAnswering,
    AutoModelForTextToSpectrogram, AutoModelForTextToWaveform,
    AutoModelForCTC, AutoModelForObjectDetection,
    AutoModelForZeroShotObjectDetection, AutoModelForImageSegmentation,
    AutoModelForSemanticSegmentation, AutoModelForInstanceSegmentation,
    AutoModelForDepthEstimation, AutoModelForMaskedImageModeling,
    AutoModelForAudioFrameClassification, AutoModelForAudioXVector,
    AutoModelForPreTraining, AutoModelForImageToImage,
    AutoModel, default_data_collator
)
import torch

class TaskRouter:
    """Routes execution based on detected task category"""
    
    TASK_CLASS_MAP = {
        # Generative
        "causal_lm": AutoModelForCausalLM,
        "seq2seq_lm": AutoModelForSeq2SeqLM,
        "vision2seq": AutoModelForVision2Seq or AutoModelForMultimodalLM or AutoModelForImageTextToText or AutoModel,
        "speech_seq2seq": AutoModelForSpeechSeq2Seq,
        
        # Classification
        "masked_lm": AutoModelForMaskedLM,
        "sequence_classification": AutoModelForSequenceClassification,
        "token_classification": AutoModelForTokenClassification,
        "multiple_choice": AutoModelForMultipleChoice,
        "next_sentence": AutoModelForNextSentencePrediction,
        "image_classification": AutoModelForImageClassification,
        "audio_classification": AutoModelForAudioClassification,
        "video_classification": AutoModelForVideoClassification,
        "audio_frame_classification": AutoModelForAudioFrameClassification,
        "audio_xvector": AutoModelForAudioXVector,
        
        # QA
        "question_answering": AutoModelForQuestionAnswering,
        "table_qa": AutoModelForTableQuestionAnswering,
        "document_qa": AutoModelForDocumentQuestionAnswering,
        "visual_qa": AutoModelForVisualQuestionAnswering,
        
        # Vision
        "object_detection": AutoModelForObjectDetection,
        "zero_shot_object_detection": AutoModelForZeroShotObjectDetection,
        "image_segmentation": AutoModelForImageSegmentation,
        "semantic_segmentation": AutoModelForSemanticSegmentation,
        "instance_segmentation": AutoModelForInstanceSegmentation,
        "depth_estimation": AutoModelForDepthEstimation,
        "masked_image_modeling": AutoModelForMaskedImageModeling,
        "image_to_image": AutoModelForImageToImage,
        
        # Speech/Audio
        "ctc": AutoModelForCTC,
        
        # Audio / Variants
        "text_to_spectrogram": AutoModelForTextToSpectrogram,
        "text_to_waveform": AutoModelForTextToWaveform,
        
        # Utility
        "text_encoding": AutoModelForTextEncoding,
        "pretraining": AutoModelForPreTraining,
        "unknown": AutoModel 
    }
    
    @classmethod
    def get_model_class(cls, task_type: str) -> Type:
        """Get appropriate AutoModel* class for the task"""
        return cls.TASK_CLASS_MAP.get(task_type, AutoModel)
        
    @staticmethod
    def _to_device(inputs, device):
        return {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}
        
    @classmethod
    async def execute(cls, model: Any, task_metadata: Dict[str, Any], inputs: Dict[str, Any], device: str) -> Dict[str, Any]:
        """Routes execution correctly. Receives processed inputs."""
        import asyncio
        task_type = task_metadata.get("task_type", "unknown")
        is_generative = task_metadata.get("is_generative", False)
        
        def _run():
            # Determine behavior based on generation capability or task
            if is_generative:
                # Pop generation kwargs if passed (max_tokens, temperature, etc)
                gen_kwargs = inputs.pop("generation_kwargs", {})
                device_inputs = cls._to_device(inputs, device)
                
                with torch.no_grad():
                    output_ids = model.generate(**device_inputs, **gen_kwargs)
                return {"output": output_ids}
                
            elif task_type in ["sequence_classification", "image_classification", "audio_classification"]:
                device_inputs = cls._to_device(inputs, device)
                with torch.no_grad():
                    outputs = model(**device_inputs)
                
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)[0].cpu().tolist()
                predicted_class = logits.argmax(-1).item()
                confidence = probs[predicted_class]
                
                # Map index to label if config provides
                label = model.config.id2label.get(predicted_class, str(predicted_class)) if hasattr(model.config, "id2label") and model.config.id2label else str(predicted_class)
                
                return {
                    "output": label,
                    "confidence": confidence,
                    "probabilities": probs
                }
                
            elif task_type == "question_answering":
                device_inputs = cls._to_device(inputs, device)
                with torch.no_grad():
                    outputs = model(**device_inputs)
                return {
                    "start_logits": outputs.start_logits,
                    "end_logits": outputs.end_logits
                }
                
            elif task_type == "masked_lm":
                # BERT-style [MASK] prediction — return logits, engine decodes top-k
                device_inputs = cls._to_device(inputs, device)
                with torch.no_grad():
                    outputs = model(**device_inputs)
                return {"logits": outputs.logits}
                
            else:
                # Base forward pass
                device_inputs = cls._to_device(inputs, device)
                with torch.no_grad():
                     outputs = model(**device_inputs)
                
                if hasattr(outputs, "last_hidden_state"):
                    return {"output": "Hidden States Emitted", "shape": list(outputs.last_hidden_state.shape)}
                return {"output": "Raw Outputs Emitted"}

        return await asyncio.to_thread(_run)
