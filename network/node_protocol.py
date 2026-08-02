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
import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


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


class NodeClient:
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

    def register_user(self, id_publico: str, alias: str,
                      region: str, node_id: str) -> dict:
        return self._post("api/users/register", {
            "id_publico": id_publico,
            "alias":      alias,
            "region":     region,
            "node_id":    node_id,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S")
        }) or {}

    def verify_user_exists(self, id_publico: str) -> bool:
        result = self._get("api/users/exists", {"id": id_publico})
        return bool(result and result.get("exists"))

    def get_user_by_alias(self, alias: str, region: str = None) -> dict | None:
        params = {"alias": alias}
        if region:
            params["region"] = region
        result = self._get("api/users/lookup", params)
        if result and result.get("found"):
            return result
        return None

    def send_message(self, package: dict) -> dict:
        return self._post("api/messages/send", package) or {}

    def fetch_messages(self, id_publico: str) -> list[dict]:
        result = self._get("api/messages/fetch", {"id": id_publico})
        if result and isinstance(result.get("messages"), list):
            return result["messages"]
        return []

    def ack_message(self, msg_id: str, id_publico: str):
        self._post("api/messages/ack", {
            "msg_id":     msg_id,
            "id_publico": id_publico
        })

    def send_contact_request(self, from_id: str, to_id: str,
                              from_alias: str, note: str = "") -> dict:
        return self._post("api/contacts/request", {
            "from_id":    from_id,
            "to_id":      to_id,
            "from_alias": from_alias,
            "note":       note,
            "timestamp":  time.strftime("%Y-%m-%dT%H:%M:%S")
        }) or {}

    def fetch_contact_requests(self, id_publico: str) -> list[dict]:
        result = self._get("api/contacts/pending", {"id": id_publico})
        if result and isinstance(result.get("requests"), list):
            return result["requests"]
        return []

    def respond_contact_request(self, request_id: str,
                                 id_publico: str, accept: bool) -> dict:
        return self._post("api/contacts/respond", {
            "request_id": request_id,
            "id_publico": id_publico,
            "accepted":   accept
        }) or {}

    def node_info(self) -> dict:
        return self._get("api/node/info") or {}

    def check_version(self) -> dict:
        """Consulta la versión disponible en el servidor para el OTA."""
        return self._get("api/version") or {}

    def ping(self) -> float | None:
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

    def get_tunnel_type(self, dest_id: str) -> str:
        """Determina qué tipo de túnel usar."""
        if self.check_live_available(dest_id):
            return "live"
        return "async"

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
