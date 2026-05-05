#!/usr/bin/env python3
"""
update.py — MyceliumNet v0.3.1 OTA updater
Uso: python update.py
     python update.py --force   (fuerza aunque sea la misma version)
"""
import sys
import os
import json
import shutil
import zipfile
import tempfile
from pathlib import Path

try:
    import requests
except ImportError:
    print("[ERROR] Instala requests: pip install requests")
    sys.exit(1)

# Carpetas y archivos que NUNCA se tocan en un update
PROTECTED = {
    "data",
    "messages",
    "docs",
    "updater.py",   # no se sobreescribe a sí mismo
}

def load_local_version() -> str:
    cfg = Path("data/config.json")
    if cfg.exists():
        try:
            return json.loads(cfg.read_text()).get("version", "0.0.0")
        except Exception:
            pass
    return "0.0.0"

def fetch_remote_info(server_url: str) -> dict | None:
    try:
        r = requests.get(f"{server_url.rstrip('/')}/api/version", timeout=8)
        if r.ok:
            return r.json()
    except Exception as e:
        print(f"[ERROR] No se pudo contactar el servidor: {e}")
    return None

def download_zip(url: str, dest: Path) -> bool:
    try:
        print(f"  Descargando {url} ...")
        r = requests.get(url, stream=True, timeout=30)
        if not r.ok:
            print(f"[ERROR] Descarga fallida: {r.status_code}")
            return False
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def apply_update(zip_path: Path, project_root: Path):
    """
    Extrae el zip en un directorio temporal y copia los archivos
    al proyecto, respetando PROTECTED.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        print("  Extrayendo...")
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(tmp)

        # GitHub pone todo dentro de una carpeta raíz tipo "myceliumnet-main/"
        extracted_dirs = list(tmp.iterdir())
        src_root = extracted_dirs[0] if len(extracted_dirs) == 1 else tmp

        copied = 0
        skipped = 0
        for src in src_root.rglob("*"):
            if src.is_dir():
                continue

            rel = src.relative_to(src_root)
            top = rel.parts[0]  # primera carpeta/archivo del path relativo

            if top in PROTECTED:
                skipped += 1
                continue

            dest = project_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            copied += 1

        print(f"  {copied} archivos actualizados, {skipped} protegidos.")

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

def main():
    force = "--force" in sys.argv

    # Detecta raíz del proyecto (donde está este script)
    project_root = Path(__file__).parent.resolve()

    # Lee servidor desde config
    cfg_path = project_root / "data" / "config.json"
    if not cfg_path.exists():
        print("[ERROR] No hay sesion configurada. Ejecuta installer.py primero.")
        sys.exit(1)

    cfg        = json.loads(cfg_path.read_text())
    server_url = cfg.get("server_url", "local")

    if server_url == "local":
        print("[WARN] Modo local — no hay servidor para consultar updates.")
        sys.exit(0)

    local_ver = load_local_version()
    print(f"\n  MyceliumNet Updater")
    print(f"  Version local:  {local_ver}")

    remote = fetch_remote_info(server_url)
    if not remote:
        print("[ERROR] No se pudo obtener info del servidor.")
        sys.exit(1)

    remote_ver   = remote.get("version", "0.0.0")
    download_url = remote.get("download_url", "")
    changelog    = remote.get("changelog", "")

    print(f"  Version remota: {remote_ver}")
    if changelog:
        print(f"  Cambios: {changelog}")
    print()

    if local_ver == remote_ver and not force:
        print("  Ya tienes la version mas reciente.")
        sys.exit(0)

    if not download_url:
        print("[ERROR] El servidor no provee URL de descarga.")
        sys.exit(1)

    ans = input("  Actualizar ahora? [s/N] ").strip().lower()
    if ans != "s":
        print("  Actualización cancelada.")
        sys.exit(0)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
        zip_path = Path(tmp_zip.name)

    try:
        if not download_zip(download_url, zip_path):
            sys.exit(1)
        apply_update(zip_path, project_root)
        update_version_in_config(remote_ver)
        print(f"\n  Actualizado a {remote_ver} correctamente.")
        print("  Reinicia la sesion: python main.py\n")
    finally:
        zip_path.unlink(missing_ok=True)

if __name__ == "__main__":
    main()