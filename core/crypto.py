"""
crypto.py — motor criptográfico de MyceliumNet

Capas:
  1. AES-256-GCM     → cifrado real y autenticado
  2. Rejilla          → transposición estructural configurable
  3. Dados virtuales  → aleatoriedad para tokens (d12, letras+números)
"""
import os
import secrets
import hashlib
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


# ── Dados virtuales d12 ───────────────────────────────────────────────────────

# Caras del d12: números 1-6 + letras seleccionadas
D12_FACES = ["1","2","3","4","5","6","A","B","C","D","E","F"]

def roll_d12(n: int = 6) -> list[str]:
    """Lanza n dados d12 virtuales. Retorna lista de resultados."""
    return [secrets.choice(D12_FACES) for _ in range(n)]

def dice_to_token(rolls: list[str]) -> str:
    """Convierte una tirada en token hex de 32 bytes."""
    seed = "".join(rolls).encode()
    # Amplifica entropía con SHA-256
    return hashlib.sha256(seed + secrets.token_bytes(16)).hexdigest()

def generate_token() -> tuple[str, list[str]]:
    """
    Genera un token seguro.
    Retorna (token_hex, rolls_display) para mostrar los dados al usuario.
    """
    rolls  = roll_d12(12)   # 12 dados
    random = secrets.token_hex(16)
    combined = "".join(rolls) + random
    token = hashlib.sha256(combined.encode()).hexdigest()
    return token, rolls


# ── Rejilla de transposición ──────────────────────────────────────────────────

GRID_PATTERNS = {
    "spiral":   "espiral — difícil de analizar",
    "zigzag":   "zigzag — rápido",
    "diagonal": "diagonal — moderado",
    "reverse":  "inverso — simple pero efectivo",
}

def suggest_grid_pattern(k_usuario: bytes) -> str:
    """Sugiere un patrón de rejilla basado en los datos del usuario."""
    idx = k_usuario[0] % len(GRID_PATTERNS)
    return list(GRID_PATTERNS.keys())[idx]

def _apply_grid(data: bytes, pattern: str, cols: int = 8) -> bytes:
    """Aplica transposición por columnas con el patrón elegido."""
    if not data:
        return data

    # Padding
    pad = (cols - len(data) % cols) % cols
    data = data + b'\x00' * pad

    rows = [data[i:i+cols] for i in range(0, len(data), cols)]

    if pattern == "reverse":
        result = b"".join(row[::-1] for row in rows)
    elif pattern == "zigzag":
        result = b"".join(row if i % 2 == 0 else row[::-1]
                          for i, row in enumerate(rows))
    elif pattern == "diagonal":
        flat = list(data)
        n = len(flat)
        indices = sorted(range(n), key=lambda x: (x % cols + x // cols) % n)
        result = bytes(flat[i] for i in indices)
    elif pattern == "spiral":
        # Espiral simple: intercala filas normales e invertidas alternando cols
        result = b""
        for i, row in enumerate(rows):
            shift = i % cols
            result += row[shift:] + row[:shift]
    else:
        result = data

    return result[:len(data) - pad] if pad else result

def _reverse_grid(data: bytes, pattern: str, original_len: int, cols: int = 8) -> bytes:
    """Invierte la transposición."""
    pad = (cols - original_len % cols) % cols
    data_padded = data + b'\x00' * pad if len(data) < original_len + pad else data

    rows = [data_padded[i:i+cols] for i in range(0, len(data_padded), cols)]

    if pattern == "reverse":
        result = b"".join(row[::-1] for row in rows)
    elif pattern == "zigzag":
        result = b"".join(row if i % 2 == 0 else row[::-1]
                          for i, row in enumerate(rows))
    elif pattern == "diagonal":
        flat = list(data_padded)
        n = len(flat)
        indices = sorted(range(n), key=lambda x: (x % cols + x // cols) % n)
        reverse_map = [0] * n
        for new_i, old_i in enumerate(indices):
            reverse_map[old_i] = new_i
        result = bytes(flat[reverse_map[i]] for i in range(n))
    elif pattern == "spiral":
        result = b""
        for i, row in enumerate(rows):
            shift = i % cols
            result += row[-(shift):] + row[:-(shift)] if shift else row
    else:
        result = data_padded

    return result[:original_len]


# ── Clave de mensaje ──────────────────────────────────────────────────────────

def derive_message_key(k_shared: bytes, token: str) -> bytes:
    """
    Deriva la clave final de cifrado de un mensaje.
    K_final = HKDF(K_shared + token)
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=token.encode(),
        info=b"myceliumnet_msg_v1",
        backend=default_backend()
    )
    return hkdf.derive(k_shared)


# ── Cifrado principal ─────────────────────────────────────────────────────────

def encrypt_message(plaintext: str, k_shared: bytes, token: str,
                    grid_pattern: str = "zigzag") -> dict:
    """
    Cifra un mensaje con AES-256-GCM + rejilla.

    Retorna dict con todo lo necesario para descifrar
    (excepto k_shared y token, que los conocen solo los usuarios).
    """
    k_final  = derive_message_key(k_shared, token)
    raw      = plaintext.encode("utf-8")
    original_len = len(raw)

    # Capa 1: rejilla
    gridded  = _apply_grid(raw, grid_pattern)

    # Capa 2: AES-256-GCM
    aesgcm   = AESGCM(k_final)
    nonce    = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, gridded, None)

    return {
        "nonce":        nonce.hex(),
        "ciphertext":   base64.b64encode(ciphertext).decode(),
        "grid_pattern": grid_pattern,
        "original_len": original_len,
        "version":      "mnv1"
    }


def decrypt_message(package: dict, k_shared: bytes, token: str) -> str:
    """
    Descifra un paquete cifrado con encrypt_message.
    Lanza ValueError si la clave/token son incorrectos.
    """
    if package.get("version") != "mnv1":
        raise ValueError("Versión de paquete no compatible.")

    k_final  = derive_message_key(k_shared, token)
    nonce    = bytes.fromhex(package["nonce"])
    ct       = base64.b64decode(package["ciphertext"])
    grid     = package["grid_pattern"]
    orig_len = package["original_len"]

    # Capa 2: AES-256-GCM
    aesgcm   = AESGCM(k_final)
    try:
        gridded = aesgcm.decrypt(nonce, ct, None)
    except Exception:
        raise ValueError("Clave o token incorrectos — descifrado fallido.")

    # Capa 1: invertir rejilla
    plaintext_bytes = _reverse_grid(gridded, grid, orig_len)

    return plaintext_bytes.decode("utf-8")


# ── Utilidades de contactos ───────────────────────────────────────────────────

def contacts_file() -> Path:
    return Path("data/contacts.json")

def load_contacts() -> dict:
    f = contacts_file()
    if f.exists():
        return json.loads(f.read_text())
    return {}

def save_contact(alias: str, id_publico: str, region: str, note: str = ""):
    contacts = load_contacts()
    contacts[alias] = {
        "id_publico": id_publico,
        "region":     region,
        "note":       note
    }
    contacts_file().write_text(json.dumps(contacts, indent=2))

def get_contact(alias: str) -> dict | None:
    return load_contacts().get(alias)
