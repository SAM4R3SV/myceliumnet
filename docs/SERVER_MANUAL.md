# MyceliumNet — Manual de Servidor / Nodo
**v0.2.0-alpha**

---

## Jerarquía de nodos

```
+57                    ← nodo raíz de región (Colombia)
├── +57.MYCEL          ← nodo nombrado (servidor principal del proyecto)
│   ├── +57.MYCEL.BOG  ← subnodo (Bogotá)
│   └── +57.MYCEL.BAQ  ← subnodo (Barranquilla)
└── +57.ESR            ← otro nodo en la misma región

+1                     ← nodo raíz USA/Canada
└── +1.NYC             ← nodo nombrado
```

**Reglas:**
- Un nodo raíz por región (ej: `+57`)
- Nodos nombrados bajo la raíz: `+región.NOMBRE`
- Subnodos: `+región.NODO.SUBREGION` (máximo 3 niveles)
- Los IDs son en mayúsculas, sin espacios, máximo 8 caracteres por segmento

---

## Configurar un nodo (servidor propio)

### Opción A — Supabase (recomendado para empezar)

1. Crea cuenta en [supabase.com](https://supabase.com) (gratis)
2. Nuevo proyecto → anota la URL y la API key
3. En el SQL Editor, ejecuta el schema de la base de datos (ver abajo)
4. Despliega la API (ver carpeta `server/`)
5. Registra tu nodo en la red principal contactando a `+57.MYCEL`

### Opción B — VPS propio

Requisitos mínimos:
- Ubuntu 22.04 LTS
- 512MB RAM, 10GB disco
- Python 3.10+
- Puerto 443 abierto (HTTPS)

```bash
git clone https://github.com/samuel/myceliumnet
cd myceliumnet/server
pip install -r requirements_server.txt
python server.py --node-id +57.MYCEL.BAQ --region +57 --port 8443
```

---

## Schema de base de datos

```sql
-- Usuarios registrados
CREATE TABLE users (
    id_publico   TEXT PRIMARY KEY,
    alias        TEXT NOT NULL,
    region       TEXT NOT NULL,
    node_id      TEXT NOT NULL,
    registered   TIMESTAMP DEFAULT NOW(),
    last_seen    TIMESTAMP
);

-- Mensajes cifrados (el servidor NO puede leer el contenido)
CREATE TABLE messages (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dest_id      TEXT NOT NULL REFERENCES users(id_publico),
    sender_id    TEXT NOT NULL,
    payload      JSONB NOT NULL,        -- paquete cifrado completo
    tunnel_type  TEXT DEFAULT 'async',  -- 'async' o 'live'
    created_at   TIMESTAMP DEFAULT NOW(),
    claimed_at   TIMESTAMP,
    expires_at   TIMESTAMP DEFAULT NOW() + INTERVAL '30 days'
);

-- Solicitudes de contacto
CREATE TABLE contact_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_id      TEXT NOT NULL,
    to_id        TEXT NOT NULL,
    from_alias   TEXT,
    note         TEXT,
    status       TEXT DEFAULT 'pending',  -- 'pending', 'accepted', 'rejected'
    created_at   TIMESTAMP DEFAULT NOW()
);

-- Presencia (para túnel live)
CREATE TABLE presence (
    id_publico   TEXT PRIMARY KEY REFERENCES users(id_publico),
    last_seen    TIMESTAMP DEFAULT NOW(),
    node_id      TEXT
);

-- Transferencias entre nodos
CREATE TABLE node_transfers (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    id_publico   TEXT NOT NULL,
    old_node     TEXT NOT NULL,
    new_node     TEXT NOT NULL,
    new_node_url TEXT NOT NULL,
    redirect_until TIMESTAMP DEFAULT NOW() + INTERVAL '30 days',
    created_at   TIMESTAMP DEFAULT NOW()
);
```

---

## Endpoints requeridos

Tu servidor debe implementar estos endpoints para ser compatible con la red:

| Endpoint                    | Método | Descripción                              |
|-----------------------------|--------|------------------------------------------|
| `/ping`                     | GET    | Health check — responde `{"ok": true}`  |
| `/api/node/info`            | GET    | Info del nodo (versión, región, uptime) |
| `/api/users/register`       | POST   | Registrar nuevo usuario                  |
| `/api/users/exists`         | GET    | Verificar si un ID existe                |
| `/api/users/lookup`         | GET    | Buscar usuario por alias                 |
| `/api/messages/send`        | POST   | Recibir y almacenar mensaje cifrado      |
| `/api/messages/fetch`       | GET    | Entregar mensajes pendientes             |
| `/api/messages/ack`         | POST   | Confirmar recepción (inicia TTL 7 días)  |
| `/api/contacts/request`     | POST   | Enviar solicitud de contacto             |
| `/api/contacts/pending`     | GET    | Listar solicitudes pendientes            |
| `/api/contacts/respond`     | POST   | Aceptar o rechazar solicitud             |
| `/api/presence/heartbeat`   | POST   | Registrar usuario como activo            |
| `/api/presence/check`       | GET    | Verificar si un usuario está online      |
| `/api/node/transfer_out`    | POST   | Iniciar transferencia a otro nodo        |

---

## Comunicación entre nodos

Los nodos se comunican directamente via HTTPS. Cuando un mensaje llega con `dest_id` de otro nodo, el servidor lo reenvía al nodo correspondiente.

```
Usuario A (+57.MYCEL) → envía a → Usuario B (+57.MYCEL.BAQ)

Flujo:
  1. A → servidor +57.MYCEL (mensaje cifrado)
  2. +57.MYCEL detecta que B está en +57.MYCEL.BAQ
  3. +57.MYCEL → reenvía a → +57.MYCEL.BAQ
  4. B descarga de +57.MYCEL.BAQ
```

Para rutas entre regiones:
```
Usuario A (+57.MYCEL) → Usuario C (+1.NYC)

  A → +57.MYCEL → +57 (raíz Colombia) → +1 (raíz USA) → +1.NYC → C
```

---

## Registrar tu nodo en la red

Para que otros usuarios puedan encontrar tu nodo:

1. Configura tu servidor con un ID válido (ej: `+57.MYCEL.BAQ`)
2. Asegúrate de que el endpoint `/ping` responde públicamente
3. Contacta al operador del nodo raíz de tu región (`+57.MYCEL`)
4. Proporciona: URL pública, node_id, región, nombre descriptivo
5. El nodo raíz añadirá tu servidor a su lista de nodos conocidos

---

## Seguridad del servidor

- El servidor NUNCA puede leer el contenido de los mensajes (cifrado E2E)
- Solo almacena el `id_publico` (hash irreversible) de los usuarios
- Los mensajes expiran automáticamente (30 días sin reclamar, 7 días después)
- Implementa rate limiting en todos los endpoints
- Usa HTTPS obligatorio — nunca HTTP en producción

---

## Variables de entorno recomendadas

```env
MYCELIUMNET_NODE_ID=+57.MYCEL.BAQ
MYCELIUMNET_REGION=+57
MYCELIUMNET_PARENT_NODE=+57.MYCEL
MYCELIUMNET_PARENT_URL=https://myceliumnet-main.supabase.co
DATABASE_URL=postgresql://...
SECRET_KEY=...
```

---

## Licencia del servidor

El código del servidor se distribuye bajo licencia restringida:
- Puedes montar nodos **dentro de la red MyceliumNet** libremente
- No puedes modificar el protocolo de comunicación entre nodos sin coordinación
- No puedes crear redes paralelas incompatibles con el protocolo v0.2+
- El código del cliente (usuario) es completamente libre

Para dudas: abre un issue en el repositorio GitHub del proyecto.
