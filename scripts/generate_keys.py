#!/usr/bin/env python3
"""Generate RSA 2048-bit key pair for RS256 JWT signing and verification (ADR-002)."""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_rsa_key_pair(output_dir: Path | str = "certs") -> tuple[Path, Path]:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    private_key_path = out_path / "jwt_private.pem"
    public_key_path = out_path / "jwt_public.pem"

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_path.write_bytes(private_pem)

    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key_path.write_bytes(public_pem)

    print(f"Generated RSA 2048-bit private key: {private_key_path}")
    print(f"Generated RSA 2048-bit public key:  {public_key_path}")
    return private_key_path, public_key_path


if __name__ == "__main__":
    generate_rsa_key_pair()
