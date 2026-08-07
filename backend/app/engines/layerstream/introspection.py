import torch.nn as nn
from typing import Dict, Any

class ModelIntrospector:
    @staticmethod
    def detect_model_components(model: nn.Module) -> Dict[str, Any]:
        """
        Dynamically detects core components of any AutoModelForCausalLM structure.
        Returns embed, layers, norm, lm_head.
        """
        components = {}
        
        # 1. LM Head
        if hasattr(model, 'get_output_embeddings'):
            components['lm_head'] = model.get_output_embeddings()
        elif hasattr(model, 'lm_head'):
            components['lm_head'] = model.lm_head
        else:
            # Fallback for LM Head: usually the last linear layer
            linears = [m for m in model.modules() if isinstance(m, nn.Linear)]
            if linears:
                components['lm_head'] = linears[-1]
            
        base_model = getattr(model, model.base_model_prefix, model)
        
        # 2. Embedding Layer
        if hasattr(base_model, 'get_input_embeddings'):
            components['embed'] = base_model.get_input_embeddings()
        else:
            # Fallback for Embedding
            embeds = [m for m in base_model.modules() if isinstance(m, nn.Embedding)]
            if embeds:
                components['embed'] = embeds[0]
            
        # 3. Transformer Layers
        module_lists = [m for m in base_model.modules() if isinstance(m, nn.ModuleList)]
        if module_lists:
            # The transformer layers are typically the longest ModuleList
            longest_list = max(module_lists, key=lambda x: len(x))
            components['layers'] = longest_list
        else:
            raise ValueError("Could not dynamically detect transformer layers (nn.ModuleList).")
        
        # 4. Final Norm Layer
        for name, module in base_model.named_children():
            if 'norm' in name.lower() or 'ln_f' in name.lower():
                components['norm'] = module
                break
                
        if 'norm' not in components:
            norms = [m for m in base_model.modules() if 'norm' in m.__class__.__name__.lower()]
            if norms:
                components['norm'] = norms[-1]
            else:
                components['norm'] = None # Some models may not have a final norm
                
        # 5. Rotary Embeddings (RoPE)
        components['rotary_emb'] = None
        for name, module in base_model.named_modules():
            if "rotary_emb" in name:
                components['rotary_emb'] = module
                break

        # Validate existence
        if 'embed' not in components or components['embed'] is None:
            raise ValueError("Could not dynamically detect Embedding layer.")
        if 'lm_head' not in components or components['lm_head'] is None:
            raise ValueError("Could not dynamically detect LM head.")
            
        return components
