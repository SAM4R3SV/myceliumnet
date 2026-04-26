"""
server_discovery.py — descubrimiento y selección de servidores MyceliumNet

Lógica:
  - Lista de servidores conocidos (hardcoded + cache local)
  - Ping a cada uno, mide latencia
  - Selecciona el más cercano automáticamente
  - Detecta modo offline y lo reporta al sistema
"""
import json
import time
import socket
import threading
from pathlib import Path
from urllib.parse import urlparse

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

SERVERS_CACHE = Path("data/servers.json")

# Servidores conocidos por defecto
DEFAULT_SERVERS = [
    {
        "id":      "+57.MYCEL",
        "name":    "MyceliumNet Main · Colombia",
        "url":     "https://mycelserv.onrender.com",
        "region":  "+57",
        "type":    "root",
        "public":  True
    },
]

PING_TIMEOUT  = 4    # segundos
MAX_SERVERS   = 20   # máximo en cache


# ── Utilidades de red ─────────────────────────────────────────────────────────

def _tcp_ping(host: str, port: int = 443, timeout: float = PING_TIMEOUT) -> float | None:
    """Ping TCP a host:port. Retorna latencia en ms o None si falla."""
    try:
        start = time.monotonic()
        with socket.create_connection((host, port), timeout=timeout):
            return (time.monotonic() - start) * 1000
    except (socket.timeout, socket.error, OSError):
        return None


def _http_ping(url: str, timeout: float = PING_TIMEOUT) -> float | None:
    """Ping HTTP GET /ping. Retorna latencia en ms o None."""
    if not HAS_REQUESTS:
        return None
    try:
        start = time.monotonic()
        r = requests.get(f"{url.rstrip('/')}/ping", timeout=timeout)
        ms = (time.monotonic() - start) * 1000
        return ms if r.status_code < 500 else None
    except Exception:
        return None


def ping_server(server: dict) -> dict:
    """
    Mide latencia a un servidor.
    Retorna el dict del servidor con campos añadidos:
      latency_ms, online, last_checked
    """
    url  = server.get("url", "")
    host = urlparse(url).hostname or url

    # Intenta HTTP primero, luego TCP
    ms = _http_ping(url) if HAS_REQUESTS else None
    if ms is None:
        ms = _tcp_ping(host)

    result = dict(server)
    result["latency_ms"]    = round(ms, 1) if ms is not None else None
    result["online"]        = ms is not None
    result["last_checked"]  = time.strftime("%Y-%m-%dT%H:%M:%S")
    return result


def ping_all(servers: list[dict], on_result=None) -> list[dict]:
    """
    Hace ping a todos los servidores en paralelo.
    on_result(server_result) se llama cuando cada uno termina.
    """
    results = [None] * len(servers)
    lock = threading.Lock()

    def worker(i, srv):
        r = ping_server(srv)
        with lock:
            results[i] = r
            if on_result:
                on_result(r)

    threads = [threading.Thread(target=worker, args=(i, s), daemon=True)
               for i, s in enumerate(servers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=PING_TIMEOUT + 1)

    return [r for r in results if r is not None]


# ── Cache local ───────────────────────────────────────────────────────────────

def load_servers() -> list[dict]:
    """Carga servidores desde cache local. Si no existe, usa DEFAULT_SERVERS."""
    if SERVERS_CACHE.exists():
        try:
            return json.loads(SERVERS_CACHE.read_text())
        except Exception:
            pass
    return list(DEFAULT_SERVERS)


def save_servers(servers: list[dict]):
    SERVERS_CACHE.parent.mkdir(exist_ok=True)
    # Limita a MAX_SERVERS, prioriza online y menor latencia
    sorted_s = sorted(
        servers,
        key=lambda s: (0 if s.get("online") else 1, s.get("latency_ms") or 9999)
    )
    SERVERS_CACHE.write_text(json.dumps(sorted_s[:MAX_SERVERS], indent=2))


def add_server(url: str, node_id: str, region: str, name: str = "") -> dict:
    """Agrega un servidor personalizado a la cache."""
    servers = load_servers()
    entry = {
        "id":     node_id,
        "name":   name or node_id,
        "url":    url,
        "region": region,
        "type":   "node",
        "public": False
    }
    # Evita duplicados por URL
    servers = [s for s in servers if s.get("url") != url]
    servers.append(entry)
    save_servers(servers)
    return entry


# ── Selección automática ──────────────────────────────────────────────────────

def best_server(results: list[dict]) -> dict | None:
    """Retorna el servidor online con menor latencia."""
    online = [s for s in results if s.get("online")]
    if not online:
        return None
    return min(online, key=lambda s: s.get("latency_ms") or 9999)


def check_connectivity() -> bool:
    """Verifica si hay conexión a internet básica."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


# ── Descubrimiento completo (para el installer y menú estado) ─────────────────

def discover(show_progress=None) -> dict:
    """
    Proceso completo de descubrimiento:
      1. Verifica conectividad
      2. Carga servidores conocidos
      3. Hace ping a todos en paralelo
      4. Guarda resultados en cache
      5. Retorna resumen

    show_progress(server_result) → callback opcional para UI en tiempo real
    """
    online = check_connectivity()
    if not online:
        return {
            "connected": False,
            "servers":   [],
            "best":      None,
            "message":   "Sin conexión a internet. Modo local activado."
        }

    servers = load_servers()
    results = ping_all(servers, on_result=show_progress)
    save_servers(results)

    best = best_server(results)
    online_count = sum(1 for s in results if s.get("online"))

    return {
        "connected":    True,
        "servers":      results,
        "best":         best,
        "online_count": online_count,
        "message":      f"{online_count}/{len(results)} servidores en línea"
    }
