import torch

class Sampler:
    @staticmethod
    def sample(logits: torch.Tensor, temperature: float = 0.7, top_p: float = 0.9, top_k: int = 50) -> torch.Tensor:
        """
        Robust, non-destructive sampling utility for batch generation logits.
        """
        # Take logits over the sequence and avoid mutating inference-graph tensors
        logits = logits[:, -1, :].clone()

        if temperature <= 0.0:
            return torch.argmax(logits, dim=-1).unsqueeze(-1)

        logits = logits / temperature

        # Top-K Masking
        if top_k > 0:
            v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
            logits[logits < v[:, [-1]]] = float('-inf')

        # Top-p Nucleus filtering
        if top_p < 1.0:
            sorted_logits, sorted_indices = torch.sort(logits, descending=True)
            cumulative_probs = torch.cumsum(torch.softmax(sorted_logits, dim=-1), dim=-1)
            
            sorted_indices_to_remove = cumulative_probs > top_p
            sorted_indices_to_remove[..., 1:] = sorted_indices_to_remove[..., :-1].clone()
            sorted_indices_to_remove[..., 0] = 0

            indices_to_remove = sorted_indices_to_remove.scatter(1, sorted_indices, sorted_indices_to_remove)
            logits[indices_to_remove] = float('-inf')

        probs = torch.softmax(logits, dim=-1)
        next_token = torch.multinomial(probs, num_samples=1)
        return next_token
