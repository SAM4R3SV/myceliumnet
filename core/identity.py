from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
import json
import secrets
from pathlib import Path

DATA_FILE = Path("data/identity.bin")

def generate_identity() -> tuple[str, bytes]:
    """
    Genera una identidad nueva basada en un keypair X25519 aleatorio.

    Retorna (id_publico, k_usuario):
      - id_publico: clave pública X25519 en hex
      - k_usuario: clave privada X25519 en bytes crudos
    """
    priv = X25519PrivateKey.generate()
    pub = priv.public_key()
    return pub.public_bytes_raw().hex(), priv.private_bytes_raw()


def format_backup_key(k_usuario: bytes, chunk_size: int = 8, line_chunks: int = 4) -> str:
    """Formatea la clave privada como backup legible en bloques."""
    hex_key = k_usuario.hex()
    chunks = [hex_key[i:i + chunk_size] for i in range(0, len(hex_key), chunk_size)]
    lines = [" ".join(chunks[i:i + line_chunks]) for i in range(0, len(chunks), line_chunks)]
    return "\n".join(lines)


# ── Sesión local ──────────────────────────────────────────────────────────────

def save_session(k_usuario: bytes, id_publico: str,
                 alias: str, region: str, password: str):
    """
    Guarda la sesión cifrada en data/identity.bin
    La contraseña local cifra K_usuario con AES-256-GCM.
    La identidad pública se guarda como texto opaco.
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

    payload = {
        "id_publico":      id_publico,
        "alias":           alias,
        "region":          region,
        "salt":            salt.hex(),
        "nonce":           nonce.hex(),
        "k_enc":           k_enc.hex(),
        "failed_attempts": 0,
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
        "id_publico": payload["id_publico"],
        "alias":      payload["alias"],
        "region":     payload["region"],
        "k_usuario":  k_usuario,
    }


def session_exists() -> bool:
    return DATA_FILE.exists()


def _wipe_session():
    """
    Borrado de emergencia: elimina todo excepto installer.py
    Deja un archivo wipe.log con timestamp.
    """
    import datetime
    import shutil

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
