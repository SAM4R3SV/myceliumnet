#!/usr/bin/env python3
"""
main.py — MyceliumNet v0.3.1
"""
import sys
import os
import json
import datetime
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.ui        import *
from core.constants import APP_NAME, SESSION_TIMEOUT_MIN
from core.identity  import (load_session, session_exists, recover_session,
                             derive_identity, save_session, get_public_info)
from core.crypto    import (encrypt_message, decrypt_message, generate_token,
                             roll_d12, load_contacts, save_contact, get_contact)

_SESSION = {}
_NODE_CLIENT = None
_ONLINE = False


def _load_config() -> dict:
    f = Path("data/config.json")
    if f.exists():
        return json.loads(f.read_text())
    return {"grid_pattern": "zigzag", "server_url": "local", "node_id": "+0.LOCAL"}


def _init_node_client(cfg: dict):
    global _NODE_CLIENT, _ONLINE
    url = cfg.get("server_url", "local")
    if url == "local":
        _ONLINE = False
        return
    try:
        from network.node_protocol import NodeClient
        from network.server_discovery import check_connectivity
        if check_connectivity():
            _NODE_CLIENT = NodeClient(url, cfg.get("node_id", ""))
            _ONLINE = True
        else:
            _ONLINE = False
    except Exception:
        _ONLINE = False


def _start_heartbeat():
    """Envia presencia al servidor cada 30s en background."""
    def beat():
        while _ONLINE and _NODE_CLIENT and _SESSION.get("id_publico"):
            try:
                from network.node_protocol import TunnelManager
                tm = TunnelManager(_NODE_CLIENT, _SESSION["id_publico"])
                tm.send_presence_heartbeat()
            except Exception:
                pass
            threading.Event().wait(30)
    t = threading.Thread(target=beat, daemon=True)
    t.start()


# ── Login ─────────────────────────────────────────────────────────────────────

def do_login():
    global _SESSION
    banner()
    section("iniciar sesion")

    pub = get_public_info()
    if pub:
        info(f"Nodo: {c(C.GREEN, pub['alias'])}  region {pub['region']}")
        blank()

    attempts = 0
    while attempts < 5:
        pw = ask("contrasena local", secret=True)
        result = load_session(pw)

        if result == "WIPED":
            blank()
            err("Demasiados intentos fallidos.")
            err("La sesion ha sido eliminada por seguridad.")
            err("Ejecuta installer.py para configurar de nuevo.")
            sys.exit(1)

        if result is None:
            attempts += 1
            remaining = 5 - attempts
            err(f"Contrasena incorrecta. Intentos restantes: {remaining}")
            continue

        _SESSION = result
        cfg = _load_config()
        _SESSION.update(cfg)
        ok(f"Bienvenido, {c(C.GREEN + C.BOLD, result['alias'])}")
        blank()

        _init_node_client(cfg)
        if _ONLINE:
            info(f"Conectado a {cfg.get('node_id', 'servidor')}")
            _start_heartbeat()
        else:
            warn("Modo local — sin conexion al servidor.")
        break
    else:
        err("Sesion bloqueada.")
        sys.exit(1)


# ── Enviar mensaje ────────────────────────────────────────────────────────────

def do_send():
    section("enviar mensaje")

    if not _ONLINE:
        warn("Sin conexion. Solo puedes guardar mensajes localmente.")
        warn("El receptor debera copiar el archivo .json manualmente.")
        blank()

    contacts = load_contacts()
    if contacts:
        info("Contactos guardados:")
        for alias, data in contacts.items():
            print(f"  {c(C.GREEN, alias):<22} {c(C.DGRAY, data['region'])}  {c(C.DGRAY, data.get('node_id',''))}")
        blank()

    dest_alias = ask("alias del destinatario")
    contact    = get_contact(dest_alias)

    if contact:
        dest_id     = contact["id_publico"]
        dest_region = contact["region"]
        dest_node   = contact.get("node_id", "")
        info(f"Usando contacto guardado: {dest_alias}")
    else:
        warn("Contacto no encontrado. Ingresa sus datos manualmente.")
        dest_id     = ask("ID publica del destinatario (hex)")
        dest_region = ask("region del destinatario (ej: +57)")
        dest_node   = ask("nodo del destinatario (ej: +57.MYCEL)")

    blank()

    # Tunnel type
    tunnel_type = "async"
    if _ONLINE and _NODE_CLIENT:
        from network.node_protocol import TunnelManager
        tm = TunnelManager(_NODE_CLIENT, _SESSION["id_publico"])
        if tm.check_live_available(dest_id):
            tunnel_type = "live"
            info("Destinatario en linea — tunel directo disponible.")
        else:
            info("Destinatario offline — modo bandeja de entrada.")
    blank()

    # Token
    section("generando token")
    use_physical = confirm("Usar dados fisicos?")

    if use_physical:
        info("Lanza 12 dados de 12 caras. Caras validas: 1-6 y A-F")
        raw_rolls = ask("resultados (ej: 3 A 2 F 1 B ...)").upper().split()
        valid = {"1","2","3","4","5","6","A","B","C","D","E","F"}
        rolls = [r for r in raw_rolls if r in valid]
        from core.crypto import dice_to_token
        import secrets
        token = dice_to_token(rolls) + secrets.token_hex(8)
        token = token[:64]
    else:
        token, rolls = generate_token()
        blank()
        info("Dados virtuales:")
        print("  " + c(C.MAGENTA, " - ".join(rolls)))

    blank()
    token_display("TOKEN", token[:16] + "..." + token[-8:])
    warn("Envia este token al destinatario por un canal separado.")
    blank()

    msg = ask("escribe tu mensaje")
    if not msg:
        err("Mensaje vacio.")
        return

    import hashlib
    k_self   = _SESSION["k_usuario"]
    id_dest  = bytes.fromhex(dest_id[:64]) if len(dest_id) >= 64 else dest_id.encode()
    k_shared = hashlib.sha256(k_self + id_dest).digest()

    grid = _SESSION.get("grid_pattern", "zigzag")
    thinking("cifrando", steps=3)

    raw_package = encrypt_message(msg, k_shared, token, grid)

    package = {
        "sender_id":    _SESSION["id_publico"],
        "sender_alias": _SESSION.get("alias", "?"),
        "dest_id":      dest_id,
        "dest_node":    dest_node,
        "tunnel_type":  tunnel_type,
        "token_hint":   token[:4] + "****",
        "timestamp":    datetime.datetime.now().isoformat(),
        "payload":      raw_package,
    }

    # Intenta enviar por red si esta online
    sent_online = False
    if _ONLINE and _NODE_CLIENT:
        thinking("enviando al servidor", steps=3)
        result = _NODE_CLIENT.send_message(package)
        if not result.get("error"):
            ok("Mensaje enviado al servidor.")
            sent_online = True
        else:
            warn(f"Error de red: {result.get('error')}")
            warn("Guardado localmente como respaldo.")

    # Siempre guarda en outbox local
    ts  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = Path(f"messages/outbox/{dest_alias}_{ts}.json")
    out.write_text(json.dumps(package, indent=2))

    blank()
    if not sent_online:
        ok(f"Mensaje cifrado guardado en: {out}")
        info("Pasa este archivo al destinatario junto con el token.")
    blank()
    token_display("TOKEN COMPLETO", token)


# ── Recibir ───────────────────────────────────────────────────────────────────

def do_receive():
    section("descifrar mensaje")

    # Intenta descargar del servidor primero
    if _ONLINE and _NODE_CLIENT:
        thinking("verificando mensajes en servidor", steps=2)
        remote = _NODE_CLIENT.fetch_messages(_SESSION["id_publico"])
        if remote:
            ok(f"{len(remote)} mensaje(s) nuevo(s) en el servidor.")
            for i, pkg in enumerate(remote):
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                fname = f"messages/inbox/server_{ts}_{i}.json"
                Path(fname).write_text(json.dumps(pkg, indent=2))
                if pkg.get("id"):
                    _NODE_CLIENT.ack_message(pkg["id"], _SESSION["id_publico"])
            ok("Mensajes descargados al inbox local.")
        else:
            info("No hay mensajes nuevos en el servidor.")
        blank()

    inbox = list(Path("messages/inbox").glob("*.json"))
    if not inbox:
        info("No hay mensajes en el inbox.")
        info("Copia archivos .json de mensajes en messages/inbox/")
        return

    blank()
    info("Mensajes disponibles:")
    for i, f in enumerate(inbox, 1):
        try:
            pkg = json.loads(f.read_text())
            sender = pkg.get("sender_alias", pkg.get("sender_id","?")[:12])
            ts     = pkg.get("timestamp","?")[:16]
            print(f"  {c(C.DGRAY, f'[{i}]')} {c(C.WHITE, sender):<22} {c(C.DGRAY, ts)}  {f.name}")
        except Exception:
            print(f"  {c(C.DGRAY, f'[{i}]')} {f.name}")
    blank()

    raw = ask("numero de mensaje a descifrar")
    if not raw.isdigit() or not (1 <= int(raw) <= len(inbox)):
        err("Seleccion invalida.")
        return

    msg_file = inbox[int(raw) - 1]
    package  = json.loads(msg_file.read_text())

    blank()
    info(f"De:    {c(C.WHITE, package.get('sender_alias', package.get('sender_id','?')[:16]))}")
    info(f"Fecha: {package.get('timestamp','?')[:16]}")
    blank()

    token = ask("token del emisor")
    if not token:
        err("Token vacio.")
        return

    import hashlib
    sender_id = package.get("sender_id", "")
    k_self    = _SESSION["k_usuario"]
    id_sender = bytes.fromhex(sender_id[:64]) if len(sender_id) >= 64 else sender_id.encode()
    k_shared  = hashlib.sha256(k_self + id_sender).digest()

    thinking("descifrando", steps=3)

    try:
        plaintext = decrypt_message(package, k_shared, token)
    except ValueError as e:
        err(f"No se pudo descifrar: {e}")
        return

    blank()
    line()
    print(f"\n  {c(C.WHITE + C.BOLD, 'MENSAJE:')}\n")
    print(f"  {c(C.GREEN, plaintext)}\n")
    line()
    blank()

    if confirm("Guardar copia descifrada?"):
        out = Path(f"messages/inbox/{msg_file.stem}_decrypted.txt")
        out.write_text(f"De: {package.get('sender_alias', package.get('sender_id','?'))}\n"
                       f"Nodo: {package.get('dest_node','?')}\n"
                       f"Fecha: {package.get('timestamp','?')}\n\n{plaintext}\n")
        ok(f"Guardado: {out}")

    if confirm("Eliminar el .json cifrado original?"):
        msg_file.unlink()
        ok("Archivo cifrado eliminado.")


# ── Contactos ─────────────────────────────────────────────────────────────────

def _sync_contact_status():
    """
    Consulta al servidor qué solicitudes enviadas por este usuario
    fueron aceptadas y actualiza el campo 'confirmed' en contacts.json.
    Se llama silenciosamente al abrir la vista de contactos.
    """
    if not _ONLINE or not _NODE_CLIENT:
        return
    try:
        contacts = load_contacts()
        changed  = False
        cf       = Path("data/contacts.json")

        for alias, data in contacts.items():
            if data.get("confirmed"):
                continue  # ya confirmado, no re-consultar
            
            # Intenta sincronizar por request_id si existe
            req_id = data.get("request_id", "")
            if req_id:
                result = _NODE_CLIENT._get("api/contacts/status", {"request_id": req_id})
                if result and result.get("status") == "accepted":
                    contacts[alias]["confirmed"] = True
                    changed = True
                    continue
            
            # Fallback: consultar por to_id si no hay request_id o falló la consulta
            to_id = data.get("id_publico", "")
            if to_id:
                result = _NODE_CLIENT._get("api/contacts/status", {"to_id": to_id})
                if result and result.get("status") == "accepted":
                    contacts[alias]["confirmed"] = True
                    changed = True

        if changed:
            cf.write_text(json.dumps(contacts, indent=2))
    except Exception:
        pass  # sync es best-effort, no bloquea UX


def do_contacts():
    section("contactos")

    # Sincroniza estado confirmed en background sin bloquear
    _sync_contact_status()

    contacts = load_contacts()

    if not contacts:
        info("No tienes contactos guardados.")
    else:
        blank()
        for alias, data in contacts.items():
            status = c(C.GREEN, "confirmado") if data.get("confirmed") else c(C.YELLOW, "pendiente")
            print(f"  {c(C.WHITE, alias):<22} {c(C.DGRAY, data['region']):<12} "
                  f"{c(C.DGRAY, data.get('node_id','')):<20} {status}")

    blank()
    opts = ["Agregar contacto", "Ver solicitudes pendientes", "Volver"]
    choice = ask_choice("Que quieres hacer?", opts)

    if choice == "Agregar contacto":
        _add_contact()
    elif choice == "Ver solicitudes pendientes":
        _view_contact_requests()


def _add_contact():
    section("agregar contacto")

    if not _ONLINE:
        err("Sin conexion al servidor.")
        err("No puedes agregar contactos en modo local.")
        err("El servidor debe verificar que el ID existe.")
        return

    blank()
    alias   = ask("alias del contacto")
    region  = ask("region (opcional, ej: +57 — Enter para buscar en todas)")
    note    = ask("nota opcional")

    if not alias:
        err("El alias es obligatorio.")
        return

    # ── Lookup por alias ──────────────────────────────────────────────────────
    thinking("buscando usuario en la red", steps=2)
    lookup = _NODE_CLIENT.get_user_by_alias(alias, region or None)

    if not lookup:
        blank()
        err(f"No se encontro ningun usuario con alias '{alias}'" +
            (f" en region {region}" if region else "") + ".")
        warn("Verifica el alias exacto o prueba sin filtro de region.")
        blank()
        # Fallback: entrada manual si el usuario lo prefiere
        if not confirm("Ingresar ID hex manualmente?"):
            return
        id_pub  = ask("ID publica (hex 64 chars)")
        region  = ask("region (ej: +57)")
        node_id = ask("nodo (ej: +57.MYCEL)")
        if not all([id_pub, region, node_id]):
            err("Datos incompletos.")
            return
        # Verifica que el ID existe aunque el alias no matcheó
        thinking("verificando ID en la red", steps=2)
        if not _NODE_CLIENT.verify_user_exists(id_pub):
            err("El ID no fue encontrado en la red.")
            return
        ok("ID verificado.")
    else:
        id_pub  = lookup["id_publico"]
        region  = lookup.get("region", region or "?")
        node_id = lookup.get("node_id", "")
        blank()
        ok(f"Usuario encontrado:")
        info(f"  Alias:  {alias}")
        info(f"  Region: {region}")
        info(f"  Nodo:   {node_id}")
        info(f"  ID:     {id_pub[:16]}...")
        blank()
        if not confirm("Enviar solicitud de contacto?"):
            info("Cancelado.")
            return

    info("Enviando solicitud de contacto...")

    result = _NODE_CLIENT.send_contact_request(
        from_id    = _SESSION["id_publico"],
        to_id      = id_pub,
        from_alias = _SESSION.get("alias", "?"),
        note       = note
    )

    if result.get("error"):
        err(f"Error al enviar solicitud: {result['error']}")
        return

    # Guarda localmente como pendiente
    save_contact(alias, id_pub, region, note)
    contacts = load_contacts()
    contacts[alias]["node_id"]    = node_id
    contacts[alias]["confirmed"]  = False
    contacts[alias]["request_id"] = result.get("request_id", "")
    Path("data/contacts.json").write_text(json.dumps(contacts, indent=2))

    blank()
    ok(f"Solicitud enviada a {alias}.")
    info("El contacto aparecera como 'confirmado' cuando acepte la solicitud.")


def _view_contact_requests():
    section("solicitudes de contacto")

    if not _ONLINE:
        warn("Sin conexion al servidor.")
        return

    thinking("descargando solicitudes", steps=2)
    requests = _NODE_CLIENT.fetch_contact_requests(_SESSION["id_publico"])

    if not requests:
        info("No hay solicitudes pendientes.")
        return

    blank()
    for i, req in enumerate(requests, 1):
        print(f"  {c(C.DGRAY, f'[{i}]')} De: {c(C.WHITE, req.get('from_alias','?')):<20} "
              f"ID: {c(C.DGRAY, req.get('from_id','?')[:16])}...")
        if req.get("note"):
            print(f"       Nota: {req['note']}")
    blank()

    raw = ask("numero de solicitud a responder (0 para salir)")
    if raw == "0" or not raw.isdigit():
        return

    idx = int(raw) - 1
    if not (0 <= idx < len(requests)):
        err("Invalido.")
        return

    req    = requests[idx]
    accept = confirm(f"Aceptar solicitud de {req.get('from_alias','?')}?")

    result = _NODE_CLIENT.respond_contact_request(
        req.get("request_id", req.get("id","")),
        _SESSION["id_publico"],
        accept
    )

    if accept and not result.get("error"):
        save_contact(req.get("from_alias","?"), req.get("from_id",""),
                     req.get("region","?"), req.get("note",""))
        contacts = load_contacts()
        alias = req.get("from_alias","?")
        if alias in contacts:
            contacts[alias]["confirmed"] = True
            Path("data/contacts.json").write_text(json.dumps(contacts, indent=2))
        ok(f"Contacto {req.get('from_alias','?')} agregado.")
    elif not accept:
        ok("Solicitud rechazada.")
    else:
        err(f"Error: {result.get('error')}")


# ── Estado del nodo ───────────────────────────────────────────────────────────

def do_status():
    section("estado del nodo")
    cfg = _load_config()
    blank()

    net_status = c(C.GREEN, "en linea") if _ONLINE else c(C.RED, "local/offline")
    table([
        ("Alias",        _SESSION.get("alias", "?")),
        ("Region",       _SESSION.get("region", "?")),
        ("Nodo",         cfg.get("node_id", "?")),
        ("Servidor",     cfg.get("server_url", "local")[:40]),
        ("Conexion",     net_status),
        ("Rejilla",      cfg.get("grid_pattern", "?")),
        ("Version",      cfg.get("version", "0.3.1")),
        ("ID publica",   _SESSION.get("id_publico","?")[:24] + "..."),
    ])
    blank()

    inbox_count  = len(list(Path("messages/inbox").glob("*.json")))
    outbox_count = len(list(Path("messages/outbox").glob("*.json")))
    table([
        ("Mensajes en inbox",  inbox_count),
        ("Mensajes en outbox", outbox_count),
    ])

    if _ONLINE and _NODE_CLIENT:
        blank()
        section("info del servidor")
        thinking("consultando", steps=2)
        info_node = _NODE_CLIENT.node_info()
        if info_node and not info_node.get("error"):
            for k, v in info_node.items():
                print(f"  {c(C.DGRAY, k):<24} {v}")
        else:
            warn("No se pudo obtener info del servidor.")

    blank()
    if confirm("Cambiar de servidor?"):
        _change_server()


def _change_server():
    section("cambiar servidor")
    info("Se transferiran tus datos al nuevo servidor.")
    info("El servidor actual redirigira tus mensajes por 30 dias.")
    blank()

    new_url     = ask("URL del nuevo servidor")
    new_node_id = ask("ID del nodo (ej: +57.MYCEL.BAQ)")
    new_name    = ask("nombre descriptivo")

    if not confirm(f"Confirmar cambio a {new_node_id}?"):
        info("Cambio cancelado.")
        return

    from network.server_discovery import add_server, ping_server
    from network.node_protocol import NodeClient, request_node_transfer

    new_srv = add_server(new_url, new_node_id, _SESSION.get("region","?"), new_name)

    thinking("probando nuevo servidor", steps=2)
    result = ping_server(new_srv)
    if not result["online"]:
        err("El nuevo servidor no responde.")
        return

    ok(f"Nuevo servidor responde en {result['latency_ms']}ms")

    thinking("solicitando transferencia", steps=3)
    new_client = NodeClient(new_url, new_node_id)

    transferred = False
    if _NODE_CLIENT:
        transferred = request_node_transfer(
            _NODE_CLIENT, new_client,
            _SESSION["id_publico"], new_node_id
        )

    if transferred:
        ok("Transferencia confirmada por el servidor actual.")
    else:
        warn("No se pudo confirmar la transferencia automatica.")
        warn("Registrandote directamente en el nuevo servidor...")

    new_client.register_user(
        _SESSION["id_publico"],
        _SESSION.get("alias","?"),
        _SESSION.get("region","?"),
        new_node_id
    )

    cfg = _load_config()
    cfg["server_url"]   = new_url
    cfg["server_label"] = new_name
    cfg["node_id"]      = new_node_id
    Path("data/config.json").write_text(json.dumps(cfg, indent=2))

    ok(f"Ahora conectado a {new_node_id}")
    info("Reinicia la sesion para aplicar los cambios.")


# ── Menu principal ────────────────────────────────────────────────────────────

MENU_OPTIONS = [
    ("enviar",     "Cifrar y enviar mensaje",    do_send),
    ("recibir",    "Descifrar mensaje recibido", do_receive),
    ("contactos",  "Gestionar contactos",        do_contacts),
    ("estado",     "Estado del nodo",            do_status),
    ("salir",      "Cerrar sesion",              None),
]

def main_menu():
    while True:
        blank()
        line()
        net = c(C.GREEN, "online") if _ONLINE else c(C.RED, "local")
        print(f"  {c(C.GREEN + C.BOLD, _SESSION.get('alias','?'))}  "
              f"{c(C.DGRAY, _SESSION.get('region','?'))}  "
              f"{c(C.DGRAY, _SESSION.get('node_id',''))}  [{net}]")
        line()
        blank()

        for cmd, label, _ in MENU_OPTIONS:
            print(f"  {c(C.CYAN, cmd):<20} {c(C.DGRAY, label)}")

        blank()
        choice = ask("comando").lower().strip()

        matched = False
        for cmd, _, fn in MENU_OPTIONS:
            if choice == cmd or (len(choice) == 1 and cmd.startswith(choice)):
                matched = True
                if fn is None:
                    blank()
                    ok("Sesion cerrada.")
                    blank()
                    return
                fn()
                break

        if not matched:
            err(f"Comando desconocido: '{choice}'")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    os.system("cls" if os.name == "nt" else "clear")

    if not session_exists():
        banner()
        err("No hay sesion configurada.")
        info("Ejecuta  python installer.py  para configurar tu nodo.")
        blank()
        if confirm("Ejecutar el instalador ahora?"):
            import installer
            installer.main()
        return

    do_login()
    main_menu()


if __name__ == "__main__":
    main()
