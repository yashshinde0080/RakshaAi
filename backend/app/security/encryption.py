"""Model Encryption"""
import os
import secrets
import hashlib
from pathlib import Path
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64


class ModelEncryption:
    """Encrypt and decrypt model files"""

    HEADER_MAGIC = b"SOVEREIGN_ENC_v1"
    SALT_LEN = 32
    ITERATIONS = 480000

    def __init__(self, key: Optional[str] = None):
        if key:
            self.key = self._derive_key(key, b"")  # salt provided at call site
        else:
            self.key = self._generate_machine_key()

        self.fernet = Fernet(self.key)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password + per-install salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _machine_salt(self) -> bytes:
        """Derive a per-machine salt from hardware identifiers."""
        import platform
        import uuid
        machine_id = f"{platform.node()}-{uuid.getnode()}"
        return hashlib.sha256(machine_id.encode()).digest()

    def _generate_machine_key(self) -> bytes:
        """Generate key from machine identifiers."""
        salt = self._machine_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(b"sovereign_ai_machine_key"))

    def _key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive Fernet key from a user password + salt read from file header."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.ITERATIONS,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def _read_header(self, f) -> tuple[bytes, int]:
        """Read and validate header, return (salt, data_offset)."""
        header = f.read(56)
        if len(header) < 56:
            raise ValueError("Encrypted file too short — not a valid SovereignAI encrypted file")
        magic = header[:14]
        if magic != self.HEADER_MAGIC:
            raise ValueError(f"Invalid file magic: {magic!r}")
        salt = header[14:46]
        # bytes 46-56 are reserved, ignore
        return salt, 56

    async def encrypt_model(self, model_path: Path) -> Path:
        """Encrypt model files. Writes random salt to file header."""
        salt = secrets.token_bytes(self.SALT_LEN)
        machine_salt = self._machine_salt()
        key = self._derive_key("sovereign_ai_encryption", salt + machine_salt)
        fernet = Fernet(key)

        if model_path.is_dir():
            encrypted_files = []
            for root, dirs, files in os.walk(model_path):
                for file in files:
                    if file.endswith(('.bin', '.safetensors', '.pt', '.json', '.gguf')):
                        target_file = Path(root) / file
                        encrypted_path = target_file.with_suffix(target_file.suffix + ".enc")
                        with open(target_file, "rb") as f_in:
                            with open(encrypted_path, "wb") as f_out:
                                # Write header
                                f_out.write(self.HEADER_MAGIC)
                                f_out.write(salt)
                                f_out.write(b"\x00" * 10)  # reserved
                                # Write encrypted chunks
                                chunk_size = 64 * 1024 * 1024
                                while chunk := f_in.read(chunk_size):
                                    encrypted_chunk = fernet.encrypt(chunk)
                                    f_out.write(len(encrypted_chunk).to_bytes(8, "big"))
                                    f_out.write(encrypted_chunk)
                        target_file.unlink()
                        encrypted_files.append(encrypted_path)
            return model_path
        else:
            encrypted_path = model_path.with_suffix(model_path.suffix + ".enc")
            with open(model_path, "rb") as f_in:
                with open(encrypted_path, "wb") as f_out:
                    # Write header
                    f_out.write(self.HEADER_MAGIC)
                    f_out.write(salt)
                    f_out.write(b"\x00" * 10)  # reserved
                    # Write encrypted chunks
                    chunk_size = 64 * 1024 * 1024
                    while chunk := f_in.read(chunk_size):
                        encrypted_chunk = fernet.encrypt(chunk)
                        f_out.write(len(encrypted_chunk).to_bytes(8, "big"))
                        f_out.write(encrypted_chunk)
            model_path.unlink()
            return encrypted_path

    async def decrypt_model(self, encrypted_path: Path, password: str = "") -> bytes:
        """Decrypt model to memory. Reads salt from file header to derive key.

        Args:
            encrypted_path: Path to .enc file.
            password: User password for key derivation. If empty, uses machine key.
        """
        decrypted_data = bytearray()

        with open(encrypted_path, "rb") as f:
            salt, offset = self._read_header(f)
            f.seek(offset)

            # Derive the correct key based on whether a password is provided
            if password:
                key = self._key_from_password(password, salt)
            else:
                machine_salt = self._machine_salt()
                key = self._derive_key("sovereign_ai_encryption", salt + machine_salt)
            fernet = Fernet(key)

            while True:
                size_bytes = f.read(8)
                if not size_bytes:
                    break
                chunk_size = int.from_bytes(size_bytes, "big")
                encrypted_chunk = f.read(chunk_size)
                decrypted_chunk = fernet.decrypt(encrypted_chunk)
                decrypted_data.extend(decrypted_chunk)

        return bytes(decrypted_data)
    
    def compute_checksum(self, data: bytes) -> str:
        """Compute SHA256 checksum"""
        return hashlib.sha256(data).hexdigest()