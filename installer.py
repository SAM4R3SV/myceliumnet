#!/usr/bin/env python3
"""
installer.py — MyceliumNet v0.3.1 setup wizard
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

from core.ui        import *
from core.constants import (REGION_CODES, RECOVERY_CATEGORIES, APP_NAME,
                             ROOT_NODE_ID, ROOT_NODE_URL)
from core.identity  import (derive_identity, save_session, session_exists,
                             get_public_info)
from core.crypto    import suggest_grid_pattern, GRID_PATTERNS
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


def _collect_datos() -> dict:
    section("identidad — 5 datos personales")
    warn("Estos datos NUNCA se guardaran en disco.")
    warn("Solo se usan para generar tu ID. Anotalos en un lugar seguro.")
    blank()
    info("Escribe EXACTAMENTE como los recordaras — sin tildes si prefieres.")
    blank()

    fields = [
        ("nombre",    "Nombre completo"),
        ("fecha_nac", "Fecha de nacimiento (dd/mm/aaaa)"),
        ("lugar",     "Ciudad/lugar de nacimiento o residencia"),
        ("genero",    "Genero (ej: M, F, NB, ...)"),
        ("usuario",   "Nombre de usuario unico"),
    ]

    datos = {}
    for key, label in fields:
        datos[key] = ask(label)

    blank()
    highlight("Confirma tus datos:")
    for key, label in fields:
        print(f"  {c(C.DGRAY, f'{label}:'):<42} {c(C.WHITE, datos[key])}")
    blank()

    if not confirm("Son correctos?"):
        warn("Reiniciando captura de datos...")
        return _collect_datos()

    return datos


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


def _pick_grid(k_usuario: bytes) -> str:
    section("patron de rejilla")
    info("Agrega una capa de transposicion estructural al cifrado.")
    info("Una vez fijada, solo puede cambiarla una solicitud al servidor.")
    blank()

    suggested = suggest_grid_pattern(k_usuario)
    info(f"Patron sugerido para tu perfil: {c(C.GREEN, suggested)}")
    blank()

    for name, desc in GRID_PATTERNS.items():
        marker = c(C.GREEN, "* ") if name == suggested else "  "
        print(f"  {marker}{c(C.WHITE, name):<16} {c(C.DGRAY, desc)}")
    blank()

    if confirm(f"Usar el sugerido ({suggested})?"):
        ok(f"Rejilla: {suggested}")
        return suggested

    while True:
        choice = ask("nombre del patron")
        if choice in GRID_PATTERNS:
            ok(f"Rejilla: {choice}")
            return choice
        err(f"Patron invalido. Opciones: {', '.join(GRID_PATTERNS.keys())}")


def _pick_recovery() -> dict:
    section("recuperacion de sesion")
    info("Elige 3 preguntas de seguridad como respaldo.")
    info("Necesitaras 2 de 3 respuestas correctas para recuperar acceso.")
    blank()

    for i, cat in enumerate(RECOVERY_CATEGORIES, 1):
        print(f"  {c(C.DGRAY, f'[{i}]')} {cat.replace('_', ' ')}")
    blank()

    selected = {}
    count = 0
    chosen_indices = set()

    while count < 3:
        raw = ask(f"pregunta {count+1} (numero)")
        if not raw.isdigit():
            err("Ingresa un numero.")
            continue
        idx = int(raw) - 1
        if idx < 0 or idx >= len(RECOVERY_CATEGORIES):
            err("Numero fuera de rango.")
            continue
        if idx in chosen_indices:
            err("Ya elegiste esa pregunta.")
            continue
        q = RECOVERY_CATEGORIES[idx]
        a = ask(f"  respuesta para '{q.replace('_', ' ')}'")
        selected[q] = a
        chosen_indices.add(idx)
        count += 1

    ok("Preguntas de recuperacion configuradas.")
    return selected


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


def _save_config(server: dict, region: str, grid_pattern: str):
    cfg = {
        "server_url":   server.get("url", "local"),
        "server_label": server.get("label", "local"),
        "node_id":      server.get("node_id", "+0.LOCAL"),
        "region":       region,
        "grid_pattern": grid_pattern,
        "grid_locked":  True,
        "version":      "0.3.1"
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

    datos   = _collect_datos()
    alias   = _pick_alias()

    section("generando identidad")
    thinking("derivando ID y clave (esto tarda unos segundos)", steps=6)

    id_publico, k_usuario = derive_identity(datos, region)

    ok(f"ID publica generada: {id_publico[:16]}...{id_publico[-8:]}")
    info("Tu K_usuario esta en memoria. Ahora se cifrara localmente.")
    blank()

    password = _pick_password()
    grid     = _pick_grid(k_usuario)
    recovery = _pick_recovery()

    section("guardando sesion")
    thinking("cifrando y guardando", steps=4)

    save_session(
        k_usuario        = k_usuario,
        id_publico       = id_publico,
        alias            = alias,
        region           = region,
        password         = password,
        recovery_answers = recovery
    )

    _save_config(server, region, grid)

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

    del datos, k_usuario, password

    blank()
    line()
    ok(f"{APP_NAME} v0.3.1 instalado correctamente.")
    blank()
    token_display("Tu alias",  alias)
    token_display("Tu region", region)
    token_display("Nodo",      server.get("node_id", "local"))
    token_display("Rejilla",   grid)
    blank()
    warn("Anota tus 5 datos personales en un lugar seguro.")
    warn("Sin ellos no podras recuperar tu identidad si pierdes la sesion.")
    blank()
    info("Ejecuta  python main.py  para entrar a MyceliumNet.")
    line()
    blank()


if __name__ == "__main__":
    main()
