#!/usr/bin/env python3
"""
installer.py — MyceliumNet v0.4.0 setup wizard
"""
import sys
import os
import subprocess
import json
import platform
from pathlib import Path

if sys.version_info < (3, 10):
    print("\n  [ERROR] MyceliumNet requiere Python 3.10 o superior.")
    print(f"  Version detectada: {platform.python_version()}")
    sys.exit(1)

REQUIRED_PACKAGES = ["cryptography", "colorama", "requests"]

def check_and_install():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"\n  Instalando dependencias: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install",
                               "--quiet", *missing])
        print("  Dependencias instaladas.\n")

check_and_install()

sys.path.insert(0, str(Path(__file__).parent))

from core.ui        import *  # noqa: F403
from core.constants import (REGION_CODES, APP_NAME, VERSION)
from core.identity  import (generate_identity, format_backup_key,
                             save_session, session_exists)
from network.server_discovery import discover, add_server, ping_server


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_folders():
    for folder in ["data", "messages/inbox", "messages/outbox", "docs"]:
        Path(folder).mkdir(parents=True, exist_ok=True)


def _check_connectivity_step() -> dict:
    """Paso 0: verifica conexion y descubre servidores disponibles."""
    section("verificando conexion")
    info("Comprobando disponibilidad de servidores...")
    blank()

    discovered = {"connected": False, "servers": [], "best": None}
    results_seen = []

    def on_result(srv):
        results_seen.append(srv)
        status = c(C.GREEN, f"  {srv['latency_ms']}ms") if srv["online"] else c(C.RED, "  sin respuesta")
        print(f"  {c(C.DGRAY, srv['id']):<28}{status}  {c(C.DGRAY, srv['name'])}")

    discovered = discover(show_progress=on_result)
    blank()

    if not discovered["connected"]:
        warn("Sin conexion a internet.")
        warn("Modo local activado — podras configurar el servidor mas tarde.")
        warn("NOTA: En modo local NO podras agregar contactos ni enviar mensajes.")
    else:
        count = discovered.get("online_count", 0)
        ok(f"{count} servidor(es) en linea.")
        if discovered["best"]:
            b = discovered["best"]
            ok(f"Mejor servidor: {c(C.GREEN, b['id'])}  ({b['latency_ms']}ms)")

    return discovered


def _pick_server(discovered: dict) -> dict:
    section("seleccionar servidor")

    servers_online = [s for s in discovered.get("servers", []) if s.get("online")]

    if not discovered.get("connected") or not servers_online:
        info("Sin servidores disponibles. Usando modo local.")
        return {"label": "local", "url": "local", "node_id": "+0.LOCAL"}

    blank()
    info("Servidores disponibles:")
    options = []
    for s in servers_online:
        label = f"{s['id']:<18} {s['name']} ({s['latency_ms']}ms)"
        options.append((label, s))

    options.append(("Ingresar URL de servidor personalizado", None))
    options.append(("Sin servidor (modo local)",             "local"))

    for i, (label, _) in enumerate(options, 1):
        print(f"  {c(C.DGRAY, f'[{i}]')} {label}")
    blank()

    while True:
        raw = ask("opcion")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            label, val = options[int(raw) - 1]
            if val == "local":
                return {"label": "local", "url": "local", "node_id": "+0.LOCAL"}
            if val is None:
                url     = ask("URL del servidor (ej: https://tuserver.com)")
                node_id = ask("ID del nodo (ej: +57.MYCEL.BAQ)")
                region  = ask("region (ej: +57)")
                name    = ask("nombre descriptivo")
                srv = add_server(url, node_id, region, name)
                info("Probando conexion...")
                result = ping_server(srv)
                if result["online"]:
                    ok(f"Servidor respondio en {result['latency_ms']}ms")
                    return {"label": name, "url": url, "node_id": node_id}
                else:
                    warn("El servidor no respondio. Se usara de todas formas.")
                    return {"label": name, "url": url, "node_id": node_id}
            s = val
            ok(f"Servidor seleccionado: {s['id']}")
            return {"label": s["name"], "url": s["url"],
                    "node_id": s["id"], "region": s["region"]}
        err("Opcion invalida.")


def _pick_region() -> str:
    section("region")
    info("El codigo de region identifica tu nodo en la red.")
    blank()

    for code, name in REGION_CODES.items():
        print(f"  {c(C.DGRAY, code):<20} {name}")
    blank()

    while True:
        choice = ask("tu codigo de region (ej: +57)")
        if choice in REGION_CODES:
            ok(f"Region: {REGION_CODES[choice]}")
            return choice
        if choice.startswith("+") and choice[1:].isdigit():
            warn(f"Codigo no estandar: {choice}. Se usara como esta.")
            return choice
        err("Codigo invalido. Debe empezar con '+' seguido de numeros.")


def _pick_alias() -> str:
    section("alias publico")
    info("Este es el nombre con el que otros usuarios te ven en la red.")
    blank()
    alias = ask("alias (ej: sombra, voidknight, ...)")
    ok(f"Alias: {alias}")
    return alias


def _pick_password() -> str:
    section("contrasena local")
    info("Protege tu sesion en este dispositivo.")
    blank()

    while True:
        p1 = ask("contrasena", secret=True)
        if len(p1) < 8:
            err("Minimo 8 caracteres.")
            continue
        p2 = ask("confirmar contrasena", secret=True)
        if p1 != p2:
            err("Las contrasenass no coinciden.")
            continue
        ok("Contrasena configurada.")
        return p1


def _register_on_server(server: dict, id_publico: str,
                         alias: str, region: str) -> bool:
    """Intenta registrar el usuario en el servidor elegido."""
    if server.get("url") == "local":
        return True
    try:
        from network.node_protocol import NodeClient
        client = NodeClient(server["url"], server.get("node_id", ""))
        result = client.register_user(id_publico, alias, region,
                                       server.get("node_id", ""))
        return not result.get("error")
    except Exception:
        return False


def _save_config(server: dict, region: str):
    cfg = {
        "server_url":   server.get("url", "local"),
        "server_label": server.get("label", "local"),
        "node_id":      server.get("node_id", "+0.LOCAL"),
        "region":       region,
        "payload_version": "mnv2",
        "version":      VERSION,
    }
    Path("data/config.json").write_text(json.dumps(cfg, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    os.system("cls" if os.name == "nt" else "clear")
    banner()

    if session_exists():
        warn("Ya existe una sesion configurada en este directorio.")
        if not confirm("Reinstalar? (se borrara la sesion actual)"):
            info("Instalacion cancelada. Usa main.py para entrar.")
            return

    line()
    highlight(f"Bienvenido al instalador de {APP_NAME}")
    info("Este proceso configura tu nodo. Tarda ~2 minutos.")
    blank()

    # Paso 0: conectividad y descubrimiento de servidores
    discovered = _check_connectivity_step()

    # Pasos normales
    region  = _pick_region()
    server  = _pick_server(discovered)
    _create_folders()

    alias   = _pick_alias()

    section("generando identidad")
    thinking("generando keypair X25519 (esto tarda unos segundos)", steps=4)

    id_publico, k_usuario = generate_identity()

    ok(f"ID publica generada: {id_publico[:16]}...{id_publico[-8:]}")
    info("Tu clave privada esta en memoria. Guardala antes de continuar.")
    blank()

    section("backup de recuperacion")
    info("Esta clave privada se mostrara una sola vez.")
    info("Guardala fuera del dispositivo. Sin ese backup no hay recuperacion.")
    blank()
    print(format_backup_key(k_usuario))
    blank()

    if not confirm("¿Ya guardaste tu backup?"):
        err("Instalacion cancelada para proteger tu identidad.")
        return

    password = _pick_password()

    section("guardando sesion")
    thinking("cifrando y guardando", steps=3)

    save_session(
        k_usuario        = k_usuario,
        id_publico       = id_publico,
        alias            = alias,
        region           = region,
        password         = password,
    )

    _save_config(server, region)

    # Registro en servidor
    if server.get("url") != "local":
        section("registrando en servidor")
        thinking("conectando", steps=3)
        registered = _register_on_server(server, id_publico, alias, region)
        if registered:
            ok("Usuario registrado en el servidor.")
        else:
            warn("No se pudo registrar en el servidor ahora.")
            warn("Se reintentara automaticamente al iniciar sesion.")

    del k_usuario, password

    blank()
    line()
    ok(f"{APP_NAME} {VERSION} instalado correctamente.")
    blank()
    token_display("Tu alias",  alias)
    token_display("Tu region", region)
    token_display("Nodo",      server.get("node_id", "local"))
    blank()
    warn("Anota tu backup privado en un lugar seguro.")
    warn("Sin ese backup no podras recuperar tu identidad si pierdes la sesion.")
    blank()
    info("Ejecuta  python main.py  para entrar a MyceliumNet.")
    line()
    blank()


if __name__ == "__main__":
    main()
