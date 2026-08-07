"""Tokenizer Implementation"""
from typing import List, Optional
from pathlib import Path
import json
import re


class Tokenizer:
    """Simple tokenizer for GGUF models"""
    
    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.vocab: dict = {}
        self.reverse_vocab: dict = {}
        self.eos_token_id = 2
        self.bos_token_id = 1
        self.pad_token_id = 0
        
        self._load_vocab()
    
    def _load_vocab(self):
        """Load vocabulary from model or separate file"""
        # Try to find vocab file
        if self.model_path.is_dir():
             vocab_path = self.model_path / "tokenizer.json"
        else:
             vocab_path = self.model_path.parent / "tokenizer.json"
        
        if vocab_path.exists():
            with open(vocab_path) as f:
                data = json.load(f)
                if "model" in data and "vocab" in data["model"]:
                    self.vocab = data["model"]["vocab"]
        else:
            # Use default vocabulary (simplified)
            # Real implementation extracts from GGUF
            self.vocab = {f"token_{i}": i for i in range(32000)}
        
        self.reverse_vocab = {v: k for k, v in self.vocab.items()}
    
    def encode(self, text: str) -> List[int]:
        """Encode text to token IDs"""
        tokens = []
        
        # Simple word-level tokenization preserving spaces
        words = re.findall(r'\w+|[^\w]', text)
        
        for word in words:
            if word in self.vocab:
                tokens.append(self.vocab[word])
            else:
                # Unknown token handling
                for char in word:
                    token_key = f"token_{ord(char) % 32000}"
                    tokens.append(self.vocab.get(token_key, 0))
        
        return tokens
    
    def decode(self, token_ids: List[int]) -> str:
        """Decode token IDs to text"""
        tokens = []
        
        for tid in token_ids:
            if tid in self.reverse_vocab:
                token = self.reverse_vocab[tid]
                if token.startswith("token_"):
                    try:
                        char_code = int(token.split("_")[1])
                        tokens.append(chr(char_code))
                    except:
                        tokens.append(token)
                else:
                    tokens.append(" " + token)
            else:
                tokens.append(f"[{tid}]")
        
        return "".join(tokens).strip()
    
    def get_vocab_size(self) -> int:
        """Get vocabulary size"""
        return len(self.vocab)