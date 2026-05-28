#!/usr/bin/env python3
"""
update.py — MyceliumNet OTA updater v0.3.2
Uso: python update.py
     python update.py --force   (fuerza aunque sea la misma version)
     python update.py --check   (solo verifica, no actualiza)
"""
import sys
import os
import json
import hashlib
import shutil
import zipfile
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] Instala requests: pip install requests")
    sys.exit(1)

# ── Configuración ─────────────────────────────────────────────────────────────

# Carpetas/archivos que NUNCA se tocan en un update
PROTECTED = {
    "data",
    "messages",
    "docs",
    "wipe.log",
    "update.py",
}

# Archivos críticos: si el zip no los trae, el update se aborta
CRITICAL_FILES = [
    "main.py",
    "installer.py",
    "core/constants.py",
    "core/crypto.py",
    "core/identity.py",
    "core/ui.py",
    "network/node_protocol.py",
    "network/server_discovery.py",
]

# Zonas sensibles: si el contenido cambia de forma incompatible, advertir
SENSITIVE_MARKERS = {
    "core/identity.py": [
        "myceliumnet_v1_",   # salt del KDF — si cambia, rompe todas las identidades
        "n=2**15",           # parámetros Scrypt identidad
    ],
    "core/crypto.py": [
        '"mnv1"',            # versión del payload cifrado
        "AES-256-GCM",       # algoritmo
    ],
}

# ── Versión local ─────────────────────────────────────────────────────────────

def load_local_version() -> str:
    # Prioridad: constants.py > config.json
    constants = Path("core/constants.py")
    if constants.exists():
        for line in constants.read_text().splitlines():
            if line.strip().startswith("VERSION"):
                # VERSION = "0.3.1-alpha"
                parts = line.split("=")
                if len(parts) == 2:
                    return parts[1].strip().strip('"').strip("'")
    cfg = Path("data/config.json")
    if cfg.exists():
        try:
            return json.loads(cfg.read_text()).get("version", "0.0.0")
        except Exception:
            pass
    return "0.0.0"

# ── Servidor ──────────────────────────────────────────────────────────────────

def load_server_url() -> str:
    cfg = Path("data/config.json")
    if not cfg.exists():
        return ""
    try:
        return json.loads(cfg.read_text()).get("server_url", "")
    except Exception:
        return ""

def fetch_remote_info(server_url: str) -> dict | None:
    try:
        r = requests.get(f"{server_url.rstrip('/')}/api/version", timeout=8)
        if r.ok:
            return r.json()
    except Exception as e:
        print(f"  [ERROR] No se pudo contactar el servidor: {e}")
    return None

# ── Descarga ──────────────────────────────────────────────────────────────────

def download_zip(url: str, dest: Path) -> bool:
    try:
        print(f"  Descargando desde {url} ...")
        r = requests.get(url, stream=True, timeout=60)
        if not r.ok:
            print(f"  [ERROR] Descarga fallida: HTTP {r.status_code}")
            return False
        total = int(r.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total:
                    pct = int(downloaded / total * 100)
                    print(f"\r  Progreso: {pct}%  ", end="", flush=True)
        print()
        return True
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False

# ── Verificación de integridad ────────────────────────────────────────────────

def verify_zip_structure(zip_path: Path) -> tuple[bool, str, Path]:
    """
    Verifica que el zip tiene la estructura esperada.
    Retorna (ok, mensaje, src_root_dentro_del_tmp).
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            if not names:
                return False, "El zip está vacío.", Path()

            # GitHub pone todo en myceliumnet-main/
            first = names[0].split("/")[0]
            src_root_name = first if "/" in names[0] else ""

        return True, "OK", Path(src_root_name)
    except zipfile.BadZipFile:
        return False, "El archivo descargado está corrupto (BadZipFile).", Path()
    except Exception as e:
        return False, str(e), Path()


def check_critical_files(src_root: Path) -> list[str]:
    """Retorna lista de archivos críticos ausentes en el zip extraído."""
    missing = []
    for f in CRITICAL_FILES:
        if not (src_root / f).exists():
            missing.append(f)
    return missing


def check_sensitive_markers(src_root: Path) -> list[str]:
    """
    Verifica que los marcadores sensibles siguen presentes en los archivos
    del zip. Si alguno desaparece, significa que algo crítico cambió.
    Retorna lista de advertencias.
    """
    warnings = []
    for rel_path, markers in SENSITIVE_MARKERS.items():
        fpath = src_root / rel_path
        if not fpath.exists():
            continue
        content = fpath.read_text(errors="ignore")
        for marker in markers:
            if marker not in content:
                warnings.append(
                    f"ADVERTENCIA: '{marker}' no encontrado en {rel_path} — "
                    f"esto puede romper compatibilidad con sesiones existentes."
                )
    return warnings


def file_hash(path: Path) -> str:
    """SHA256 de un archivo."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def diff_files(src_root: Path, project_root: Path) -> dict:
    """
    Compara archivos del zip con los locales.
    Retorna dict con listas: new, modified, unchanged.
    """
    result = {"new": [], "modified": [], "unchanged": []}
    for src in src_root.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(src_root)
        if rel.parts[0] in PROTECTED:
            continue
        dest = project_root / rel
        if not dest.exists():
            result["new"].append(str(rel))
        elif file_hash(src) != file_hash(dest):
            result["modified"].append(str(rel))
        else:
            result["unchanged"].append(str(rel))
    return result

# ── Aplicar update ────────────────────────────────────────────────────────────

def apply_update(zip_path: Path, project_root: Path) -> tuple[int, int]:
    """
    Extrae y aplica el update respetando PROTECTED.
    Retorna (copiados, omitidos).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp)

        extracted = list(tmp.iterdir())
        src_root = extracted[0] if len(extracted) == 1 and extracted[0].is_dir() else tmp

        copied = 0
        skipped = 0
        for src in src_root.rglob("*"):
            if src.is_dir():
                continue
            rel = src.relative_to(src_root)
            if rel.parts[0] in PROTECTED:
                skipped += 1
                continue
            dest = project_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1

    return copied, skipped


def update_version_in_config(new_version: str):
    cfg_path = Path("data/config.json")
    if not cfg_path.exists():
        return
    try:
        cfg = json.loads(cfg_path.read_text())
        cfg["version"] = new_version
        cfg_path.write_text(json.dumps(cfg, indent=2))
    except Exception:
        pass

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    force      = "--force"  in sys.argv
    check_only = "--check"  in sys.argv

    project_root = Path(__file__).parent.resolve()

    server_url = load_server_url()
    if not server_url or server_url == "local":
        print("  [WARN] Modo local — sin servidor configurado para consultar updates.")
        sys.exit(0)

    local_ver = load_local_version()
    print(f"\n  MyceliumNet Updater")
    print(f"  Version local:  {local_ver}")

    remote = fetch_remote_info(server_url)
    if not remote:
        print("  [ERROR] No se pudo obtener info del servidor.")
        sys.exit(1)

    remote_ver   = remote.get("version", "0.0.0")
    download_url = remote.get("download_url", "")
    changelog    = remote.get("changelog", "")

    print(f"  Version remota: {remote_ver}")
    if changelog:
        print(f"  Cambios:        {changelog}")
    print()

    if local_ver == remote_ver and not force:
        print("  Ya tienes la version mas reciente.")
        sys.exit(0)

    if check_only:
        print(f"  Actualizacion disponible: {local_ver} → {remote_ver}")
        sys.exit(0)

    if not download_url:
        print("  [ERROR] El servidor no provee URL de descarga.")
        sys.exit(1)

    ans = input("  Actualizar ahora? [s/N] ").strip().lower()
    if ans != "s":
        print("  Actualización cancelada.")
        sys.exit(0)

    # Descarga
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = Path(tmp_zip.name)

    try:
        if not download_zip(download_url, zip_path):
            sys.exit(1)

        # Verificación de estructura
        ok_struct, msg, _ = verify_zip_structure(zip_path)
        if not ok_struct:
            print(f"  [ERROR] Verificacion fallida: {msg}")
            sys.exit(1)
        print("  Estructura del zip: OK")

        # Extraer en tmp para verificaciones previas a aplicar
        with tempfile.TemporaryDirectory() as verify_tmp:
            verify_tmp = Path(verify_tmp)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(verify_tmp)

            extracted = list(verify_tmp.iterdir())
            src_root = extracted[0] if len(extracted) == 1 and extracted[0].is_dir() else verify_tmp

            # Verificar archivos críticos
            missing = check_critical_files(src_root)
            if missing:
                print(f"  [ERROR] Archivos criticos ausentes en el update:")
                for f in missing:
                    print(f"    - {f}")
                print("  Update abortado por seguridad.")
                sys.exit(1)
            print(f"  Archivos criticos: {len(CRITICAL_FILES)}/{len(CRITICAL_FILES)} presentes")

            # Verificar marcadores sensibles
            warns = check_sensitive_markers(src_root)
            if warns:
                print()
                for w in warns:
                    print(f"  ⚠  {w}")
                print()
                cont = input("  Hay cambios en zonas criticas. Continuar de todas formas? [s/N] ").strip().lower()
                if cont != "s":
                    print("  Update cancelado.")
                    sys.exit(0)

            # Mostrar diff
            diff = diff_files(src_root, project_root)
            print(f"  Archivos nuevos:      {len(diff['new'])}")
            print(f"  Archivos modificados: {len(diff['modified'])}")
            print(f"  Sin cambios:          {len(diff['unchanged'])}")

            if diff["modified"]:
                show = input("  Ver archivos modificados? [s/N] ").strip().lower()
                if show == "s":
                    for f in diff["modified"]:
                        print(f"    ~ {f}")

        # Aplicar
        print("\n  Aplicando update...")
        copied, skipped = apply_update(zip_path, project_root)
        update_version_in_config(remote_ver)

        print(f"  {copied} archivos actualizados, {skipped} protegidos.")
        print(f"\n  ✓ Actualizado a {remote_ver}")
        print("  Reinicia la sesion: python main.py\n")

    finally:
        zip_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()