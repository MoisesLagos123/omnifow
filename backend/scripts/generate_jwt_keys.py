"""Genera el par de claves RS256 (RSA 3072) para JWT en `backend/keys/`.

Uso:
    python scripts/generate_jwt_keys.py
"""
from __future__ import annotations

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def main() -> None:
    keys_dir = Path(__file__).resolve().parent.parent / "keys"
    #keys_dir = Path(__file__).resolve().parent.parent / "keys-prod"
    keys_dir.mkdir(parents=True, exist_ok=True)

    private_path = keys_dir / "jwt_private.pem"
    public_path = keys_dir / "jwt_public.pem"

    if private_path.exists() and public_path.exists():
        print(f"Las claves ya existen en {keys_dir}. No se sobreescriben.")
        return

    key = rsa.generate_private_key(public_exponent=65537, key_size=3072)

    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    private_path.write_bytes(private_pem)
    public_path.write_bytes(public_pem)
    private_path.chmod(0o600)

    print(f"Claves generadas en {keys_dir}")


if __name__ == "__main__":
    main()
