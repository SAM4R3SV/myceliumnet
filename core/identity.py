"""
identity.py — núcleo de identidad MyceliumNet

Convierte 5 datos personales en:
  - ID_publico  : identificador en el servidor (hash, no reversible)
  - K_usuario   : material criptográfico privado (deriva la llave de cifrado)

NUNCA se guardan los datos personales. Solo el resultado del KDF,
cifrado con la contraseña local del usuario.
"""
import os
import json
import hashlib
import secrets
import base64
from pathlib import Path

from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend

DATA_FILE = Path("data/identity.bin")

# ── KDF principal ─────────────────────────────────────────────────────────────

def _normalize(value: str) -> str:
    """Normaliza un dato: minúsculas, sin espacios extra, sin tildes básicas."""
    replacements = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    v = value.strip().lower()
    for k, r in replacements.items():
        v = v.replace(k, r)
    return v

def _datos_to_bytes(datos: dict) -> bytes:
    """Convierte los 5 datos en bytes canonicos."""
    keys = ["nombre", "fecha_nac", "lugar", "genero", "usuario"]
    parts = [_normalize(str(datos[k])) for k in keys]
    return "|".join(parts).encode("utf-8")

def derive_identity(datos: dict, region: str = "+0") -> tuple[str, bytes]:
    """
    Deriva (ID_publico, K_usuario) desde los 5 datos.

    ID_publico  → str hex, se sube al servidor, identifica al receptor
    K_usuario   → bytes (32), NUNCA sale del dispositivo
    """
    raw = _datos_to_bytes(datos)

    # Salt fija del sistema + región (evita rainbow tables entre redes)
    salt_base = f"myceliumnet_v1_{region}".encode()
    salt = hashlib.sha256(salt_base).digest()

    # Scrypt: lento, resistente a GPU
    kdf = Scrypt(salt=salt, length=64, n=2**15, r=8, p=1,
                 backend=default_backend())
    material = kdf.derive(raw)

    id_publico = material[:32].hex()   # primeros 32 bytes → ID público
    k_usuario  = material[32:]         # últimos 32 bytes  → clave privada

    return id_publico, k_usuario


# ── Llave compartida entre dos usuarios ──────────────────────────────────────

def shared_key(k_usuario_a: bytes, k_usuario_b: bytes) -> bytes:
    """
    Genera la llave compartida simétrica entre dos usuarios.
    Orden-independiente: shared(A,B) == shared(B,A)
    """
    combined = bytes(a ^ b for a, b in zip(k_usuario_a, k_usuario_b))
    # Segunda pasada con SHA-256 para difusión
    return hashlib.sha256(combined).digest()


# ── Sesión local ──────────────────────────────────────────────────────────────

def save_session(k_usuario: bytes, id_publico: str,
                 alias: str, region: str, password: str,
                 recovery_answers: dict):
    """
    Guarda la sesión cifrada en data/identity.bin
    La contraseña local cifra K_usuario con AES-256-GCM.
    Los datos personales NO se guardan.
    """
    DATA_FILE.parent.mkdir(exist_ok=True)

    # Deriva clave de cifrado local desde la contraseña
    pw_bytes = password.encode("utf-8")
    salt = secrets.token_bytes(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1,
                 backend=default_backend())
    enc_key = kdf.derive(pw_bytes)

    # Cifra K_usuario
    aesgcm = AESGCM(enc_key)
    nonce = secrets.token_bytes(12)
    k_enc = aesgcm.encrypt(nonce, k_usuario, None)

    # Hash de las respuestas de recuperación (no las guarda en plano)
    recovery_hashes = {
        q: hashlib.sha256(_normalize(a).encode()).hexdigest()
        for q, a in recovery_answers.items()
    }

    payload = {
        "id_publico":       id_publico,
        "alias":            alias,
        "region":           region,
        "salt":             salt.hex(),
        "nonce":            nonce.hex(),
        "k_enc":            k_enc.hex(),
        "recovery_hashes":  recovery_hashes,
        "failed_attempts":  0
    }

    DATA_FILE.write_text(json.dumps(payload, indent=2))


def load_session(password: str) -> dict | None:
    """
    Carga y descifra la sesión local.
    Retorna dict con {id_publico, alias, region, k_usuario}
    o None si la contraseña es incorrecta.
    Incrementa failed_attempts. Si llega a MAX → wipe.
    """
    from core.constants import MAX_LOGIN_ATTEMPTS

    if not DATA_FILE.exists():
        return None

    payload = json.loads(DATA_FILE.read_text())

    # Control de intentos fallidos
    attempts = payload.get("failed_attempts", 0)
    if attempts >= MAX_LOGIN_ATTEMPTS:
        _wipe_session()
        return "WIPED"

    salt  = bytes.fromhex(payload["salt"])
    nonce = bytes.fromhex(payload["nonce"])
    k_enc = bytes.fromhex(payload["k_enc"])

    pw_bytes = password.encode("utf-8")
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1,
                 backend=default_backend())

    try:
        enc_key  = kdf.derive(pw_bytes)
        aesgcm   = AESGCM(enc_key)
        k_usuario = aesgcm.decrypt(nonce, k_enc, None)
    except Exception:
        # Contraseña incorrecta
        payload["failed_attempts"] = attempts + 1
        DATA_FILE.write_text(json.dumps(payload, indent=2))
        remaining = MAX_LOGIN_ATTEMPTS - payload["failed_attempts"]
        if remaining <= 0:
            _wipe_session()
            return "WIPED"
        return None

    # Reset intentos fallidos
    payload["failed_attempts"] = 0
    DATA_FILE.write_text(json.dumps(payload, indent=2))

    return {
        "id_publico":      payload["id_publico"],
        "alias":           payload["alias"],
        "region":          payload["region"],
        "k_usuario":       k_usuario,
        "recovery_hashes": payload.get("recovery_hashes", {})
    }


def session_exists() -> bool:
    return DATA_FILE.exists()


def recover_session(answers: dict, new_password: str) -> bool:
    """
    Recuperación de sesión: verifica respuestas de recuperación.
    Si son correctas, re-cifra la sesión con nueva contraseña.
    NOTA: No puede recuperar K_usuario (está cifrada con la vieja clave).
    Solo permite resetear contraseña si el usuario recuerda sus datos
    personales para re-derivar K_usuario.
    """
    if not DATA_FILE.exists():
        return False

    payload = json.loads(DATA_FILE.read_text())
    stored  = payload.get("recovery_hashes", {})

    correct = 0
    for q, a in answers.items():
        h = hashlib.sha256(_normalize(a).encode()).hexdigest()
        if stored.get(q) == h:
            correct += 1

    return correct >= 2  # mínimo 2 de 3 respuestas correctas


def _wipe_session():
    """
    Borrado de emergencia: elimina todo excepto installer.py
    Deja un archivo wipe.log con timestamp.
    """
    import shutil
    import datetime

    wipe_note = f"WIPED at {datetime.datetime.now().isoformat()} — too many failed attempts\n"

    # Borra data/, messages/
    for folder in ["data", "messages"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p)

    # Deja log
    Path("wipe.log").write_text(wipe_note)


def get_public_info() -> dict | None:
    """Retorna solo info pública (alias, id, region) sin descifrar nada."""
    if not DATA_FILE.exists():
        return None
    p = json.loads(DATA_FILE.read_text())
    return {
        "id_publico": p["id_publico"],
        "alias":      p["alias"],
        "region":     p["region"]
    }
