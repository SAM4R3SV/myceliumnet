"""
node_protocol.py — protocolo de comunicación entre nodos MyceliumNet

Jerarquía de nodos:
  Raíz:     +57              → nodo principal de región
  Nodo:     +57.MYCEL        → servidor identificado dentro de la región
  Subnodo:  +57.MYCEL.BAQ    → nodo local / barrio / comunidad

Comportamiento:
  - Registro de usuario en nodo
  - Enrutamiento de mensajes entre nodos
  - Túnel asíncrono (bandeja) vs túnel live (P2P simulado)
  - Redireccionamiento al cambiar de servidor
"""
import json
import time
import hashlib
from enum import Enum

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# ── Tipos de conexión ─────────────────────────────────────────────────────────

class TunnelType(str, Enum):
    ASYNC = "async"    # bandeja de entrada, mensajes guardados
    LIVE  = "live"     # ambos online, entrega inmediata


class NodeType(str, Enum):
    ROOT    = "root"    # +57
    NODE    = "node"    # +57.MYCEL
    SUBNODE = "subnode" # +57.MYCEL.BAQ


# ── Utilidades de ID de nodo ──────────────────────────────────────────────────

def parse_node_id(node_id: str) -> dict:
    """
    Parsea un ID de nodo y retorna su estructura.

    Ejemplos:
      "+57"           → {region: "+57", node: None, subnode: None, type: ROOT}
      "+57.MYCEL"     → {region: "+57", node: "MYCEL", subnode: None, type: NODE}
      "+57.MYCEL.BAQ" → {region: "+57", node: "MYCEL", subnode: "BAQ", type: SUBNODE}
    """
    parts = node_id.split(".")
    region  = parts[0]
    node    = parts[1] if len(parts) > 1 else None
    subnode = parts[2] if len(parts) > 2 else None

    if subnode:
        ntype = NodeType.SUBNODE
    elif node:
        ntype = NodeType.NODE
    else:
        ntype = NodeType.ROOT

    return {
        "region":  region,
        "node":    node,
        "subnode": subnode,
        "type":    ntype,
        "full":    node_id
    }


def build_node_id(region: str, node: str = None, subnode: str = None) -> str:
    """Construye un ID de nodo desde sus partes."""
    parts = [region]
    if node:
        parts.append(node.upper())
    if subnode:
        parts.append(subnode.upper())
    return ".".join(parts)


def route_message(sender_node: str, receiver_node: str) -> list[str]:
    """
    Calcula la ruta de un mensaje entre dos nodos.
    Retorna lista de nodos intermedios (el camino).

    Lógica:
      - Misma región → directo o via nodo raíz de región
      - Distinta región → via nodos raíz de ambas regiones
    """
    s = parse_node_id(sender_node)
    r = parse_node_id(receiver_node)

    if s["region"] == r["region"]:
        # Misma región: sender → raíz de región → receiver
        root = s["region"]
        route = [sender_node]
        if s["full"] != root:
            route.append(root)
        if r["full"] != root:
            route.append(receiver_node)
        return route
    else:
        # Distinta región: sender → raíz_sender → raíz_receiver → receiver
        return [sender_node, s["region"], r["region"], receiver_node]


# ── Cliente de nodo (HTTP) ────────────────────────────────────────────────────

def normalize_node_url(url: str) -> str:
    """
    Normaliza una URL de nodo aceptando los formatos:
      - https://dominio.com
      - http://dominio.com
      - http://1.2.3.4:8000
      - 1.2.3.4:8000       → http://1.2.3.4:8000
      - dominio.com        → https://dominio.com

    Nunca añade barra final.
    """
    url = url.strip().rstrip("/")
    if not url:
        return url
    # Si ya tiene esquema, respeta tal cual
    if url.startswith("http://") or url.startswith("https://"):
        return url
    # IP con puerto explícito → http (sin TLS)
    import re
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}(:\d+)?$", url):
        return f"http://{url}"
    # hostname o dominio sin esquema → https
    return f"https://{url}"



    """Cliente para comunicarse con un servidor/nodo MyceliumNet."""

    def __init__(self, server_url: str, node_id: str):
        self.url     = normalize_node_url(server_url)
        self.node_id = node_id
        self.timeout = 10

    def _post(self, endpoint: str, data: dict) -> dict | None:
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.post(f"{self.url}/{endpoint}", json=data,
                              timeout=self.timeout)
            return r.json() if r.ok else {"error": r.text}
        except Exception as e:
            return {"error": str(e)}

    def _get(self, endpoint: str, params: dict = None) -> dict | None:
        if not HAS_REQUESTS:
            return None
        try:
            r = requests.get(f"{self.url}/{endpoint}", params=params,
                             timeout=self.timeout)
            return r.json() if r.ok else {"error": r.text}
        except Exception as e:
            return {"error": str(e)}

    # ── Registro ──────────────────────────────────────────────────────────────

    def register_user(self, id_publico: str, alias: str,
                      region: str, node_id: str) -> dict:
        """Registra un usuario nuevo en este nodo."""
        return self._post("api/users/register", {
            "id_publico": id_publico,
            "alias":      alias,
            "region":     region,
            "node_id":    node_id,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S")
        }) or {}

    def verify_user_exists(self, id_publico: str) -> bool:
        """Verifica si un ID existe en la red (para validar contactos)."""
        result = self._get("api/users/exists", {"id": id_publico})
        return bool(result and result.get("exists"))

    def get_user_by_alias(self, alias: str, region: str = None) -> dict | None:
        """Busca un usuario por alias. Retorna su info pública o None."""
        params = {"alias": alias}
        if region:
            params["region"] = region
        result = self._get("api/users/lookup", params)
        if result and not result.get("error"):
            return result
        return None

    # ── Mensajes ──────────────────────────────────────────────────────────────

    def send_message(self, package: dict) -> dict:
        """Envía un paquete cifrado al servidor."""
        return self._post("api/messages/send", package) or {}

    def fetch_messages(self, id_publico: str) -> list[dict]:
        """Descarga mensajes pendientes para este usuario."""
        result = self._get("api/messages/fetch", {"id": id_publico})
        if result and isinstance(result.get("messages"), list):
            return result["messages"]
        return []

    def ack_message(self, msg_id: str, id_publico: str):
        """Confirma recepción de un mensaje (inicia countdown de 7 días)."""
        self._post("api/messages/ack", {
            "msg_id":     msg_id,
            "id_publico": id_publico
        })

    # ── Contactos ─────────────────────────────────────────────────────────────

    def send_contact_request(self, from_id: str, to_id: str,
                              from_alias: str, note: str = "") -> dict:
        """Envía una solicitud de contacto a través del servidor."""
        return self._post("api/contacts/request", {
            "from_id":    from_id,
            "to_id":      to_id,
            "from_alias": from_alias,
            "note":       note,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S")
        }) or {}

    def fetch_contact_requests(self, id_publico: str) -> list[dict]:
        """Descarga solicitudes de contacto pendientes."""
        result = self._get("api/contacts/pending", {"id": id_publico})
        if result and isinstance(result.get("requests"), list):
            return result["requests"]
        return []

    def respond_contact_request(self, request_id: str,
                                 id_publico: str, accept: bool) -> dict:
        """Acepta o rechaza una solicitud de contacto."""
        return self._post("api/contacts/respond", {
            "request_id": request_id,
            "id_publico": id_publico,
            "accepted":   accept
        }) or {}

    # ── Estado del nodo ───────────────────────────────────────────────────────

    def node_info(self) -> dict:
        """Obtiene información del nodo (versión, region, usuarios, uptime)."""
        return self._get("api/node/info") or {}

    def ping(self) -> float | None:
        """Mide latencia al nodo. Retorna ms o None."""
        try:
            import time as _t
            start = _t.monotonic()
            r = self._get("ping")
            if r is not None:
                return round((_t.monotonic() - start) * 1000, 1)
        except Exception:
            pass
        return None


# ── Túneles ───────────────────────────────────────────────────────────────────

class TunnelManager:
    """
    Gestiona el tipo de túnel según disponibilidad.

    - Si ambos usuarios tienen sesión activa en el servidor → LIVE
    - Si no → ASYNC (bandeja)
    """

    def __init__(self, client: NodeClient, my_id: str):
        self.client = client
        self.my_id  = my_id

    def check_live_available(self, dest_id: str) -> bool:
        """Verifica si el destinatario está activo en este momento."""
        result = self.client._get("api/presence/check", {"id": dest_id})
        return bool(result and result.get("online"))

    def get_tunnel_type(self, dest_id: str) -> TunnelType:
        """Determina qué tipo de túnel usar."""
        if self.check_live_available(dest_id):
            return TunnelType.LIVE
        return TunnelType.ASYNC

    def send_presence_heartbeat(self):
        """Notifica al servidor que este usuario está activo (cada ~30s)."""
        self.client._post("api/presence/heartbeat", {
            "id_publico": self.my_id,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S")
        })


# ── Transferencia de nodo ─────────────────────────────────────────────────────

def request_node_transfer(old_client: NodeClient, new_client: NodeClient,
                           id_publico: str, new_node_id: str) -> bool:
    """
    Solicita transferencia de usuario de un nodo a otro.

    El nodo original:
      1. Confirma la solicitud
      2. Activa redirección de mensajes al nuevo nodo por 30 días
      3. Notifica al nuevo nodo que registre al usuario

    Retorna True si la transferencia fue aceptada.
    """
    result = old_client._post("api/node/transfer_out", {
        "id_publico":  id_publico,
        "new_node_id": new_node_id,
        "new_node_url": new_client.url
    })
    return bool(result and result.get("accepted"))
