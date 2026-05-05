# MyceliumNet — Manual de Servidor / Nodo
**v0.3.0-alpha**

> **Montar un nodo en la red MyceliumNet requiere autorización del administrador de la red (`+57.MYCEL`).
> No es un proceso automático — debes solicitarlo y esperar aprobación antes de que tu nodo sea visible para los clientes.**

---

## Jerarquía de nodos

```
+57                    ← nodo raíz de región (Colombia)
├── +57.MYCEL          ← nodo maestro del proyecto (SAM4R3SV)
│   ├── +57.MYCEL.BOG  ← subnodo aprobado (Bogotá)
│   └── +57.MYCEL.BAQ  ← subnodo aprobado (Barranquilla)
└── +57.ESR            ← nodo aprobado en la misma región

+1                     ← nodo raíz USA/Canada
└── +1.NYC             ← nodo aprobado
```

**Reglas de nomenclatura:**
- Un nodo raíz por región (`+57`, `+1`, etc.) — asignado por el administrador
- Nodos nombrados: `+REGION.NOMBRE` — máximo 8 caracteres, solo mayúsculas y letras
- Subnodos: `+REGION.NODO.SUBREGION` — máximo 3 niveles de profundidad
- No puedes auto-asignarte un ID raíz de región — eso lo asigna `+57.MYCEL`

---

## Proceso de autorización

Antes de configurar nada, debes obtener autorización. El flujo es:

```
1. Tú: contacta al admin de la red (ver abajo)
2. Admin: revisa tu solicitud y te asigna un node_id
3. Tú: configuras y levantas tu servidor
4. Tú: envías el registro via /api/nodes/register (queda en estado "pending")
5. Admin: aprueba desde el panel → tu nodo queda visible en /api/nodes/list
6. Los clientes descargan la lista actualizada y pueden conectarse a tu nodo
```

**Contacto:** abre un issue en el repositorio GitHub del proyecto con el asunto `[NODO] Solicitud de registro` e incluye:
- Node ID que quieres (`+57.MYCEL.TU_NOMBRE`)
- Descripción del servidor (dónde corre, para qué comunidad)
- Tu ID pública en la red MyceliumNet (alias y región)

Sin aprobación tu nodo funciona técnicamente, pero **no aparece en el discovery** y los clientes no lo encontrarán.

---

## Opciones de despliegue

### Opción A — Render + Supabase (recomendado, sin costo inicial)

Ideal si no tienes servidor propio. Render tiene tier gratuito suficiente para un nodo pequeño.

1. Crea cuenta en [supabase.com](https://supabase.com) — crea un proyecto nuevo
2. En el SQL Editor de Supabase, ejecuta el schema completo (sección más abajo)
3. Anota tu `SUPABASE_URL` y `SUPABASE_KEY` (Settings → API)
4. Crea cuenta en [render.com](https://render.com) y conecta tu repo del servidor
5. En Render, configura las variables de entorno (sección más abajo)
6. Despliega — Render te da una URL pública `https://tu-app.onrender.com`
7. Verifica: `curl https://tu-app.onrender.com/ping` debe responder `{"ok": true}`
8. Registra tu nodo (ver sección "Registrar tu nodo")

> ⚠ El tier gratuito de Render duerme el servidor tras 15 minutos de inactividad.
> Para un nodo real en producción, usa el tier pagado o un VPS propio.

---

### Opción B — VPS propio con dominio

Para quien ya tiene un servidor con dominio y certificado SSL.

**Requisitos mínimos:**
- Ubuntu 22.04 LTS
- 512 MB RAM, 10 GB disco
- Python 3.10+
- Puerto 443 abierto (HTTPS) y dominio con certificado válido (Let's Encrypt sirve)

```bash
git clone https://github.com/SAM4R3SV/mycelServ
cd mycelServ
pip install -r requirements.txt --break-system-packages

# Configura el .env (ver Variables de entorno)
cp .env.example .env
nano .env

# Levanta el servidor
uvicorn main:app --host 0.0.0.0 --port 8000

# Con nginx como proxy inverso en el puerto 443:
# server_name tu-dominio.com → proxy_pass http://localhost:8000
```

Tu `NODE_URL` en el `.env` sería `https://tu-dominio.com`.

---

### Opción C — Sin dominio, con IP:puerto o portforwarding

A partir de v0.3.0 el servidor acepta URLs del tipo `http://IP:PUERTO` — ya no necesitas dominio.
Esto sirve para nodos privados, redes locales, o si haces portforwarding desde tu router.

**Portforwarding desde tu router:**
1. Asigna IP fija a tu máquina en la red local (desde el panel del router)
2. Abre el puerto que quieras usar (ej: 8765) hacia esa IP interna
3. Encuentra tu IP pública: `curl ifconfig.me`
4. Tu `NODE_URL` será `http://TU_IP_PUBLICA:8765`

**Limitaciones importantes con IP:puerto sin dominio:**
- Sin HTTPS — la comunicación entre nodos viaja sin cifrado TLS (el contenido de los mensajes sigue cifrado E2E, pero los metadatos son visibles en tránsito)
- Si tu IP pública cambia (ISP residencial), el nodo deja de ser alcanzable y debes actualizar el registro
- No recomendado para nodos públicos de larga duración — úsalo para nodos privados o pruebas

```bash
# Ejemplo: servidor corriendo en tu máquina con portforwarding al puerto 8765
uvicorn main:app --host 0.0.0.0 --port 8765

# En el .env:
# NODE_URL=http://203.0.113.42:8765
# NODE_ID=+57.MYCEL.LOCAL
```

El cliente normaliza automáticamente las URLs — `203.0.113.42:8765` se convierte en `http://203.0.113.42:8765` sin que tengas que especificar el esquema.

---

## Variables de entorno

Archivo `.env` en la raíz del servidor:

```env
# Identidad del nodo
NODE_ID=+57.MYCEL.BAQ
NODE_URL=https://tu-servidor.com
IS_MASTER=false
MASTER_NODE_ID=+57.MYCEL
MASTER_NODE_URL=https://mycelserv.onrender.com

# Base de datos (Supabase)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_KEY=eyJ...

# Seguridad
ADMIN_PASSWORD=contraseña-larga-y-aleatoria
SECRET_KEY=otra-clave-aleatoria-para-sesiones
MAX_SESSIONS=5

# Región
NODE_REGION=+57
NODE_NAME=Mi Nodo BAQ
```

> `IS_MASTER=true` solo va en el servidor principal (`+57.MYCEL`). No lo actives en tu nodo — rompe la lógica de aprobación.

---

## Schema de base de datos

Ejecuta esto completo en el SQL Editor de Supabase al crear el proyecto:

```sql
-- Usuarios registrados
CREATE TABLE users (
    id_publico    TEXT PRIMARY KEY,
    alias         TEXT NOT NULL,
    region        TEXT NOT NULL,
    node_id       TEXT NOT NULL,
    ip_hash       TEXT,
    is_banned     BOOLEAN DEFAULT FALSE,
    ban_reason    TEXT,
    registered_at TIMESTAMP DEFAULT NOW(),
    last_seen     TIMESTAMP
);

-- Mensajes cifrados (el servidor NO puede leer el contenido)
CREATE TABLE messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dest_id       TEXT NOT NULL REFERENCES users(id_publico),
    sender_id     TEXT NOT NULL,
    sender_alias  TEXT,
    dest_node     TEXT,
    payload       JSONB NOT NULL,
    tunnel_type   TEXT DEFAULT 'async',
    claimed_at    TIMESTAMP,
    expires_at    TIMESTAMP DEFAULT NOW() + INTERVAL '30 days',
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Solicitudes de contacto
CREATE TABLE contact_requests (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_id       TEXT NOT NULL,
    to_id         TEXT NOT NULL,
    from_alias    TEXT,
    note          TEXT,
    status        TEXT DEFAULT 'pending', -- 'pending', 'accepted', 'rejected'
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Presencia activa (para túnel live)
CREATE TABLE presence (
    id_publico    TEXT PRIMARY KEY REFERENCES users(id_publico),
    last_seen     TIMESTAMP DEFAULT NOW(),
    node_id       TEXT,
    ip_hash       TEXT
);

-- Sesiones activas por IP
CREATE TABLE sessions (
    id_publico    TEXT PRIMARY KEY,
    ip_hash       TEXT NOT NULL,
    node_id       TEXT,
    last_active   TIMESTAMP DEFAULT NOW()
);

-- Nodos registrados en la red
CREATE TABLE nodes (
    node_id       TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    region        TEXT NOT NULL,
    parent_node   TEXT,
    url           TEXT NOT NULL,
    admin_id      TEXT REFERENCES users(id_publico),
    status        TEXT DEFAULT 'pending', -- 'pending', 'active', 'rejected'
    latency_ms    FLOAT,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Transferencias de usuario entre nodos
CREATE TABLE node_transfers (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_publico    TEXT NOT NULL,
    old_node      TEXT NOT NULL,
    new_node      TEXT NOT NULL,
    new_node_url  TEXT NOT NULL,
    redirect_until TIMESTAMP DEFAULT NOW() + INTERVAL '30 days',
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Log de eventos del sistema
CREATE TABLE event_logs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type    TEXT NOT NULL,
    description   TEXT,
    ip_hash       TEXT,
    user_id       TEXT,
    created_at    TIMESTAMP DEFAULT NOW()
);

-- Índices para las queries más frecuentes
CREATE INDEX idx_messages_dest    ON messages(dest_id) WHERE claimed_at IS NULL;
CREATE INDEX idx_contacts_to      ON contact_requests(to_id) WHERE status = 'pending';
CREATE INDEX idx_presence_seen    ON presence(last_seen);
CREATE INDEX idx_nodes_status     ON nodes(status);
CREATE INDEX idx_users_alias      ON users(alias);
```

---

## Endpoints requeridos

Tu servidor debe implementar todos estos endpoints para ser compatible con la red v0.3.0:

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/ping` | Health check — `{"ok": true, "node_id": ..., "ts": ...}` |
| GET | `/api/node/info` | Versión, is_master, usuarios totales, uptime |
| GET | `/api/nodes/list` | Lista de nodos activos — el cliente la descarga al iniciar |
| POST | `/api/nodes/register` | Solicitar registro de este nodo (queda en `pending`) |
| POST | `/api/nodes/approve` | Aprobar/rechazar nodo — **solo nodo maestro** |
| POST | `/api/nodes/transfer_out` | Iniciar transferencia de usuario a otro nodo |
| POST | `/api/users/register` | Registrar usuario en la red |
| GET | `/api/users/exists` | Verificar si un ID existe |
| GET | `/api/users/lookup` | Buscar usuario por alias (y región opcional) |
| POST | `/api/users/ban` | Banear usuario — requiere `admin_pw` |
| GET | `/api/users/list` | Listar usuarios paginados — requiere `admin_pw` |
| POST | `/api/messages/send` | Recibir y almacenar mensaje cifrado |
| GET | `/api/messages/fetch` | Entregar mensajes pendientes a un usuario |
| POST | `/api/messages/ack` | Confirmar recepción — inicia TTL de 7 días |
| POST | `/api/contacts/request` | Enviar solicitud de contacto |
| GET | `/api/contacts/pending` | Solicitudes pendientes recibidas por un usuario |
| GET | `/api/contacts/status` | Estado de una solicitud enviada (para el emisor) |
| POST | `/api/contacts/respond` | Aceptar o rechazar solicitud |
| POST | `/api/presence/heartbeat` | Notificar que el usuario está activo |
| GET | `/api/presence/check` | Verificar si un usuario está online ahora |

---

## Cómo funciona el discovery (v0.3.0)

Antes, el cliente tenía los servidores hardcodeados. A partir de v0.3.0:

```
Al iniciar el cliente:
  1. Conecta al nodo maestro (hardcoded solo este, ROOT_NODE_URL en constants.py)
  2. Descarga GET /api/nodes/list → lista de todos los nodos activos aprobados
  3. Hace ping a todos en paralelo
  4. Selecciona el de menor latencia
  5. Guarda la lista en data/servers.json como cache

Si el nodo maestro no responde:
  → usa la cache local (data/servers.json)
  → si tampoco hay cache → DEFAULT_SERVERS (solo el maestro como semilla)
```

Esto significa que cuando apruebes un nodo nuevo desde el panel, los clientes lo descubrirán automáticamente en su próxima sesión sin ninguna actualización del cliente.

---

## Comunicación entre nodos

Los nodos se comunican directamente por HTTP/HTTPS. Cuando un mensaje llega con `dest_id` de un usuario registrado en otro nodo, el servidor lo reenvía automáticamente.

```
Mismo nodo raíz, nodos distintos:

  Usuario A en +57.MYCEL → mensaje para → Usuario B en +57.MYCEL.BAQ

  1. A envía a su servidor (+57.MYCEL)
  2. +57.MYCEL consulta en DB: B está en +57.MYCEL.BAQ
  3. +57.MYCEL reenvía el paquete cifrado a la URL de +57.MYCEL.BAQ
  4. B descarga de su servidor (+57.MYCEL.BAQ)
```

```
Regiones distintas:

  Usuario A en +57.MYCEL → mensaje para → Usuario C en +1.NYC

  A → +57.MYCEL → +57 (raíz Colombia) → +1 (raíz USA) → +1.NYC → C
```

Si el reenvío entre nodos falla, el mensaje se guarda localmente en el nodo del sender como fallback. No se pierde.

---

## Registrar tu nodo en la red

Una vez tienes tu servidor corriendo y autorización del admin:

```bash
# Desde el cliente Python, o directamente con curl:
curl -X POST https://mycelserv.onrender.com/api/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "node_id":   "+57.MYCEL.BAQ",
    "name":      "Nodo Barranquilla",
    "region":    "+57",
    "parent":    "+57.MYCEL",
    "url":       "http://203.0.113.42:8765",
    "admin_id":  "TU_ID_PUBLICA_HEX"
  }'
```

La respuesta será `{"ok": true, "status": "pending"}`. El admin verá la solicitud en el panel y la aprobará. Tras la aprobación, `GET /api/nodes/list` incluirá tu nodo y los clientes lo encontrarán.

---

## Seguridad del servidor

- El servidor **nunca puede leer** el contenido de los mensajes — solo almacena el paquete cifrado (`payload` en JSONB)
- Solo guarda el `id_publico` (hash Scrypt de los datos del usuario) — no hay forma de revertirlo al usuario real
- Los mensajes expiran automáticamente: 30 días sin reclamar, 7 días después del ACK
- Rate limiting activo en todos los endpoints vía `slowapi`
- Todas las IPs se almacenan hasheadas (`hash_ip()`) — nunca en texto plano
- Si usas IP:puerto sin HTTPS: recuerda que el contenido del mensaje sigue cifrado E2E, pero los metadatos (quién le escribe a quién, cuándo) son visibles en tránsito — úsalo solo en redes de confianza o para pruebas

---

## Variables críticas (cambios rompen compatibilidad)

Si modificas alguno de estos valores en el servidor, los clientes con versión anterior dejarán de funcionar:

| Variable | Valor actual | Qué rompe si cambia |
|----------|-------------|---------------------|
| `VERSION` en `constants.py` | `0.3.0-alpha` | Nada por sí solo, pero documenta el cambio |
| Salt del KDF de identidad | `"myceliumnet_v1_+57"` | Todas las identidades existentes |
| Algoritmo de cifrado | AES-256-GCM | Todos los mensajes en tránsito |
| Estructura de `payload` en mensajes | `{ct, nonce, tag, grid_key}` | Mensajes no se pueden descifrar |
| TTL de mensajes (`MSG_TTL_UNCLAIMED`) | 30 días | Expectativas de los usuarios |

---

## Licencia del servidor

- Puedes montar nodos dentro de la red MyceliumNet **con autorización del administrador**
- No puedes modificar el protocolo de comunicación entre nodos sin coordinación
- No puedes levantar una instancia de `IS_MASTER=true` paralela — hay un solo nodo maestro por red
- No puedes crear redes incompatibles usando este código sin cambiar el nombre del proyecto
- El código del cliente es completamente libre

Para dudas o solicitudes: issue en el repositorio GitHub del proyecto.
