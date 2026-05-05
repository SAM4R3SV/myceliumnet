```
___  _____   __ _____  _____  _      _____  _   _ ___  ___ _   _  _____  _____
|  \/  |\ \ / //  __ \|  ___|| |    |_   _|| | | ||  \/  || \ | ||  ___||_   _|
| .  . | \ V / | /  \/| |__  | |      | |  | | | || .  . ||  \| || |__    | |
| |\/| |  \ /  | |    |  __| | |      | |  | | | || |\/| || . ` ||  __|   | |
| |  | |  | |  | \__/\| |___ | |____ _| |_ | |_| || |  | || |\  || |___   | |
\_|  |_/  \_/   \____/\____/ \_____/ \___/  \___/ \_|  |_/\_| \_/\____/   \_/

[ encrypted mesh · trust no server · know your node ]   v0.3.0-alpha
```

Sistema de mensajería cifrada persona-a-persona.
**Tu identidad es tu llave. El servidor no sabe nada.**

---

## Por qué MyceliumNet

- Sin cuentas. Sin contraseñas almacenadas. Sin intercambio de claves manual.
- El servidor solo guarda paquetes sellados — no puede leer nada.
- Red distribuida de nodos identificados por región (`+57.MYCEL`, `+1.NYC`, etc.)
- Cifrado real: AES-256-GCM + Argon2/Scrypt KDF.
- Funciona offline — los mensajes se sincronizan cuando vuelves a conectarte.

---

## Instalación rápida

**Requisitos:** Python 3.10+

```bash
git clone https://github.com/TU_USUARIO/myceliumnet
cd myceliumnet
pip install -r requirements.txt
python installer.py
```

Luego, cada vez:
```bash
python main.py
```

---

## Cómo funciona

```
1. Instalas con tus 5 datos personales → se genera tu ID pública + K_usuario
   (los datos NUNCA se guardan en disco)

2. Para enviar: sistema genera token aleatorio (dados d12)
   Mensaje cifrado con AES-256-GCM + rejilla de transposición
   Token viaja por canal separado al receptor

3. Para recibir: receptor ingresa token + sus datos reconstruyen la llave → descifra

4. Servidor: solo ve paquetes sellados identificados por hash
   No puede leer contenido. Mensajes expiran en 30 días.
```

---

## Red de nodos

```
+57                 Colombia (raíz)
└── +57.MYCEL       Servidor principal del proyecto
    ├── +57.MYCEL.BOG   Nodo Bogotá
    └── +57.MYCEL.BAQ   Nodo Barranquilla

+1                  USA/Canada (raíz)
└── +1.NYC          Nodo Nueva York
```

Cualquiera puede montar su propio nodo. Ver `docs/SERVER_MANUAL.md`.

---

## Estructura del proyecto

```
myceliumnet/
├── installer.py          # wizard de configuración
├── main.py               # cliente principal
├── core/
│   ├── constants.py      # versión, ROOT_NODE_URL, códigos de región, constantes
│   ├── ui.py             # terminal styling (verde micelium)
│   ├── identity.py       # KDF, sesión cifrada, wipe automático
│   └── crypto.py         # AES-256-GCM, rejilla, dados d12
├── network/
│   ├── server_discovery.py  # ping, latencia, discovery dinámico via /api/nodes/list
│   └── node_protocol.py     # protocolo entre nodos, normalize_node_url, túneles
├── docs/
│   ├── USER_MANUAL.md    # manual de usuario
│   └── SERVER_MANUAL.md  # manual para operadores de nodo
└── server/               # código del servidor (distribuido por separado)
```

### Endpoints del servidor (v0.3.0-alpha)

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/ping` | Health check, retorna node_id y timestamp |
| GET | `/api/node/info` | Info del nodo: versión, is_master, usuarios, uptime |
| GET | `/api/nodes/list` | Lista de nodos activos — fuente única para discovery del cliente |
| POST | `/api/nodes/register` | Solicitud de registro de nuevo nodo (queda pendiente) |
| POST | `/api/nodes/approve` | Aprobar/rechazar nodo (solo nodo maestro) |
| POST | `/api/nodes/transfer_out` | Iniciar transferencia de usuario a otro nodo |
| POST | `/api/users/register` | Registrar usuario en la red |
| GET | `/api/users/exists` | Verificar si un ID existe |
| GET | `/api/users/lookup` | Buscar usuario por alias (y región opcional) |
| POST | `/api/users/ban` | Banear usuario (admin) |
| GET | `/api/users/list` | Listar usuarios paginados (admin) |
| POST | `/api/messages/send` | Enviar paquete cifrado |
| GET | `/api/messages/fetch` | Descargar mensajes pendientes |
| POST | `/api/messages/ack` | Confirmar recepción (inicia TTL de 7 días) |
| POST | `/api/contacts/request` | Enviar solicitud de contacto |
| GET | `/api/contacts/pending` | Ver solicitudes pendientes recibidas |
| GET | `/api/contacts/status` | Consultar estado de una solicitud enviada |
| POST | `/api/contacts/respond` | Aceptar o rechazar solicitud |
| POST | `/api/presence/heartbeat` | Notificar que el usuario está activo |
| GET | `/api/presence/check` | Verificar si un usuario está online |

---

## Seguridad

| Componente | Implementación |
|------------|---------------|
| Cifrado | AES-256-GCM (autenticado) |
| KDF | Scrypt (resistente a GPU) |
| Servidor | Zero-knowledge — no puede leer mensajes |
| Sesión local | Cifrada con contraseña + wipe automático a 5 intentos |
| Aleatoriedad | Dados d12 virtuales (letras + números) u opcionales físicos |

**Para uso entre amigos, comunidades, juegos — más que suficiente.**
Para datos críticos: usa Signal.

---

## Roadmap

**v0.2.0-alpha** (base)
- [x] Cifrado local (AES-256-GCM + Scrypt)
- [x] Installer con wizard completo
- [x] Descubrimiento de servidores con ping
- [x] Protocolo de nodos distribuidos
- [x] Solicitudes de contacto verificadas por servidor
- [x] Transferencia entre nodos

**v0.3.0-alpha** (actual)
- [x] Discovery dinámico — cliente descarga lista de nodos via `/api/nodes/list`
- [x] Buscar contacto por alias — sin necesitar ID hex manualmente
- [x] Soporte IP:puerto en registro de nodos — sin dominio obligatorio
- [x] Estado de solicitud de contacto sincronizado — emisor ve si fue aceptado
- [x] Panel admin refleja correctamente si el nodo es maestro o hijo

**Próximo**
- [ ] Auto-update del cliente (`/api/version` + descarga zip)
- [ ] WebSocket para logs en tiempo real en panel
- [ ] Túnel live P2P cuando ambos están online
- [ ] GUI con customtkinter
- [ ] Plugin Minecraft (Paper/Spigot)

---

## Contribuir

Proyecto personal en desarrollo activo. Issues y PRs bienvenidos.
El código del cliente es libre. El protocolo de servidor tiene restricciones — ver `docs/SERVER_MANUAL.md`.

### Reglas de desarrollo

Antes de hacer un PR o modificar lógica central, seguir estas reglas:

**1. Constantes y versión**
Siempre verificar `core/constants.py` antes de cambiar lógica. `VERSION`, `ROOT_NODE_URL`, `ROOT_NODE_ID` y los TTL de mensajes viven ahí. No duplicar constantes en otros módulos — importarlas.

**2. Cifrado**
Cualquier cambio en `core/crypto.py` o en la derivación de claves (`core/identity.py`) requiere actualizar la tabla de Seguridad de este README y documentar el cambio en `docs/SERVER_MANUAL.md` sección "Variables Críticas". Cambios de cifrado rompen compatibilidad — bumpearn versión minor.

**3. Endpoints nuevos**
Todo endpoint nuevo en `server/api/routes.py` debe:
- Aparecer en la tabla de endpoints de este README
- Estar documentado en `docs/SERVER_MANUAL.md`
- Si modifica esquema DB: incluir migración SQL (nunca `DROP`/`CREATE` en producción)

**4. Esquema de base de datos**
Los cambios de esquema en Supabase van acompañados de un archivo `migrations/YYYYMMDD_descripcion.sql` con `ALTER TABLE` / `CREATE INDEX` según corresponda. Nunca destruir datos en producción con DROP.

---

*MyceliumNet — como el micelio: invisible, distribuido, conectado.*
