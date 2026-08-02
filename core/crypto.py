import base64
import hashlib
import json
import secrets
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


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
    token = dice_to_token(rolls)
    return token, rolls


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
        info=b"myceliumnet_msg_v2",
        backend=default_backend()
    )
    return hkdf.derive(k_shared)


# ── Cifrado principal ─────────────────────────────────────────────────────────

def encrypt_message(plaintext: str, k_shared: bytes, token: str) -> dict:
    """
    Cifra un mensaje con AES-256-GCM.

    Retorna dict con todo lo necesario para descifrar
    (excepto k_shared y token, que los conocen solo los usuarios).
    """
    k_final  = derive_message_key(k_shared, token)
    raw      = plaintext.encode("utf-8")

    # Cifrado autenticado
    aesgcm   = AESGCM(k_final)
    nonce    = secrets.token_bytes(12)
    ciphertext = aesgcm.encrypt(nonce, raw, None)

    return {
        "nonce":      nonce.hex(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "version":    "mnv2",
    }


def decrypt_message(package: dict, k_shared: bytes, token: str) -> str:
    """
    Descifra un paquete cifrado con encrypt_message.
    Lanza ValueError si la clave/token son incorrectos.
    """
    version = package.get("version")
    if version == "mnv1":
        raise ValueError("Mensaje de versión anterior. Pide que te lo reenvíen.")
    if version != "mnv2":
        raise ValueError("Versión de paquete no compatible.")

    k_final  = derive_message_key(k_shared, token)
    nonce    = bytes.fromhex(package["nonce"])
    ct       = base64.b64decode(package["ciphertext"])

    # Descifrado autenticado
    aesgcm   = AESGCM(k_final)
    try:
        plaintext_bytes = aesgcm.decrypt(nonce, ct, None)
    except Exception:
        raise ValueError("Clave o token incorrectos — descifrado fallido.")

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
