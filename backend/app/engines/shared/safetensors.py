"""Safetensors checkpoint compatibility for torch < 2.6.

transformers refuses ``torch.load`` on ``.bin`` checkpoints when torch < 2.6
(CVE-2025-32434, https://nvd.nist.gov/vuln/detail/CVE-2025-32434). Models
that only ship ``pytorch_model.bin`` therefore fail to load. Converting the
checkpoint to safetensors once sidesteps the restriction — ``from_pretrained``
prefers safetensors whenever it is present.
"""
from pathlib import Path

import torch


def ensure_safetensors(model_path: str) -> None:
    """Convert ``pytorch_model.bin`` -> ``model.safetensors`` in-place if needed."""
    model_dir = Path(model_path)
    if model_dir.is_file():
        model_dir = model_dir.parent
    if not model_dir.is_dir():
        return

    # Already has safetensors weights (incl. sharded) — nothing to do.
    if list(model_dir.glob("*.safetensors")):
        return

    # Only convert a single, unsharded checkpoint. Sharded .bin repos are
    # rare and need index-aware conversion; leave them alone rather than
    # silently producing a partial safetensors file.
    bin_files = sorted(model_dir.glob("*.bin"))
    if len(bin_files) != 1:
        return
    if (model_dir / "pytorch_model.bin.index.json").exists():
        return

    try:
        from safetensors.torch import save_file
        print(f"[safetensors] Converting {bin_files[0].name} for torch<2.6 compatibility...")
        state_dict = torch.load(bin_files[0], map_location="cpu", weights_only=True)
        # Clone to break shared-memory aliasing (weight tying, e.g. BERT's
        # cls.predictions.decoder.weight == bert.embeddings.word_embeddings.weight)
        # and force contiguity (torch.load can return transposed views) — both
        # of which save_file rejects.
        state_dict = {k: v.clone().contiguous() for k, v in state_dict.items()}
        save_file(state_dict, model_dir / "model.safetensors")
    except Exception as e:
        print(f"[safetensors] Conversion failed, leaving original weights. "
              f"Model may not load on torch < 2.6. Error: {e}")


if __name__ == "__main__":
    # Self-check: a .bin checkpoint gets converted to loadable safetensors.
    import tempfile

    from safetensors.torch import load_file

    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        # Shared tensor (weight tying) + non-contiguous view (transpose).
        # save_file rejects both; the converter must handle them.
        tied = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
        non_contig = tied.t()
        assert not non_contig.is_contiguous()
        torch.save({"w": tied, "tied": tied, "t": non_contig}, d / "pytorch_model.bin")
        ensure_safetensors(str(d))
        assert (d / "model.safetensors").exists()
        loaded = load_file(str(d / "model.safetensors"))
        assert loaded["w"].tolist() == [[1.0, 2.0], [3.0, 4.0]]
        assert loaded["tied"].tolist() == [[1.0, 2.0], [3.0, 4.0]]
        assert loaded["t"].tolist() == [[1.0, 3.0], [2.0, 4.0]]
        print("ok")
