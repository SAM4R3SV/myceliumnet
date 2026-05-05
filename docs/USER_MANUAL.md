# MyceliumNet — Manual de Usuario
**v0.3.0-alpha**

---

## ¿Qué es MyceliumNet?

Un sistema de mensajería cifrada persona-a-persona. Tu identidad ES tu llave.
Nadie puede leer tus mensajes — ni el servidor, ni el operador del nodo.

---

## Requisitos

- Python 3.10 o superior
- Windows 10/11, Linux, o macOS
- Conexión a internet (opcional — funciona en modo local sin red)

Verificar Python:
```
python --version
```

---

## Instalación

1. Descarga y descomprime el zip del proyecto
2. Abre una terminal en la carpeta `myceliumnet/`
3. Instala dependencias:
```
pip install -r requirements.txt
```
4. Ejecuta el instalador:
```
python installer.py
```

El instalador te guía paso a paso:

- **Discovery automático** — descarga la lista de nodos disponibles desde el servidor principal, hace ping a todos y muestra latencias en tiempo real
- **Región** — elige tu código de región (ej: `+57` para Colombia)
- **Servidor** — selecciona el nodo de menor latencia, o ingresa uno propio por URL o IP:puerto
- **5 datos personales** — NUNCA se guardan en disco. Son tu semilla de identidad
- **Alias** — tu nombre público visible en la red
- **Contraseña local** — protege tu sesión en este dispositivo
- **Patrón de rejilla** — capa extra de ofuscación estructural en los mensajes
- **Preguntas de recuperación** — por si olvidas la contraseña local

> ⚠ Anota tus 5 datos personales en papel y guárdalos en un lugar seguro.
> Son irreemplazables. Sin ellos no puedes recuperar tu identidad ni tus mensajes.

---

## Uso diario

```
python main.py
```

### Menú principal

| Comando | Acción |
|---------|--------|
| `enviar` | Cifrar y enviar un mensaje |
| `recibir` | Descifrar mensajes recibidos |
| `contactos` | Gestionar tus contactos |
| `estado` | Ver estado del nodo y del servidor |
| `salir` | Cerrar sesión |

También puedes escribir solo la primera letra: `e`, `r`, `c`, `s`.

---

## Enviar un mensaje

1. Escribe `enviar` en el menú
2. Si tienes contactos guardados, se muestran con su región y nodo
3. Escribe el alias del destinatario
   - Si está en tus contactos: usa sus datos automáticamente
   - Si no está: pide los datos manualmente (ver sección Contactos)
4. El sistema detecta si está online:
   - **Online** → túnel directo (entrega inmediata)
   - **Offline** → bandeja de entrada (lo descarga cuando se conecte)
5. Genera el token — elige dados físicos o virtuales
6. Escribe tu mensaje
7. **Envía el TOKEN al destinatario por un canal separado** (Discord, en persona, etc.)

> El token es la "otra mitad" de la llave. El servidor no lo ve. Sin él, el mensaje es indescifrable.

---

## Recibir un mensaje

Si estás online, el sistema verifica mensajes del servidor automáticamente al entrar a `recibir`.

1. Escribe `recibir` en el menú
2. El sistema descarga mensajes pendientes del servidor (si hay conexión)
3. Se muestra la lista de mensajes en el inbox local
4. Selecciona el número del mensaje
5. Ingresa el token que te dio el emisor
6. El mensaje se muestra descifrado en pantalla

También puedes recibir mensajes offline copiando el archivo `.json` manualmente a la carpeta `messages/inbox/`.

---

## Contactos

Los contactos se gestionan desde `contactos` en el menú principal.

### Ver tus contactos

Al entrar al menú de contactos, el sistema sincroniza automáticamente el estado de tus solicitudes enviadas con el servidor. Si alguien aceptó tu solicitud mientras estabas desconectado, verás el cambio de `pendiente` a `confirmado` sin hacer nada.

Los contactos muestran:
- Alias y región
- Nodo donde están registrados
- Estado: **confirmado** (puedes escribirles) o **pendiente** (esperando que acepten)

### Agregar un contacto (v0.3.0)

Ya no necesitas el ID hex de 64 caracteres. Solo necesitas su alias:

1. Escribe `contactos` → `Agregar contacto`
2. Escribe el **alias** del contacto (tal como aparece en la red)
3. Opcionalmente, filtra por región (ej: `+57`) si hay ambigüedad
4. El servidor busca al usuario y muestra su información
5. Confirmas y se envía la solicitud

Si el alias no se encuentra, el sistema te ofrece ingresar el ID hex manualmente como alternativa.

> La búsqueda por alias distingue mayúsculas/minúsculas y debe ser exacta.
> Si alguien usa `ElPepe` en la red, buscarlo como `elpepe` no lo encontrará.

### Ver solicitudes recibidas

Desde `contactos` → `Ver solicitudes pendientes`:

- Muestra quién te quiere agregar, su alias, y su nota opcional
- Selecciona el número y confirma si aceptas o rechazas
- Si aceptas, el contacto se guarda automáticamente como confirmado

### Estado de las solicitudes que enviaste

Cuando envías una solicitud, queda como `pendiente` en tu lista de contactos.
La próxima vez que abras el menú de contactos, el sistema consulta al servidor y actualiza el estado automáticamente si la otra persona aceptó. No necesitas hacer nada.

---

## Estado del nodo (`estado`)

Muestra información completa de tu sesión actual:

- Tu alias, región y nodo asignado
- URL del servidor al que estás conectado
- Estado de conexión (online / local-offline)
- Patrón de rejilla activo
- Versión del cliente
- Tu ID pública (primeros 24 caracteres)
- Cantidad de mensajes en inbox y outbox local

Si estás online, consulta también al servidor:
- Total de usuarios registrados
- Usuarios activos ahora mismo
- Nodos activos en la red
- Si el servidor al que estás conectado es el nodo maestro o un nodo hijo

Desde esta pantalla también puedes **cambiar de servidor** si quieres moverte a un nodo distinto. El sistema solicita la transferencia al servidor actual, que redirigirá tus mensajes por 30 días mientras te registras en el nuevo.

---

## Elegir un servidor al que conectarte

Durante la instalación, el cliente descarga automáticamente la lista de nodos disponibles desde el servidor principal de la red. Luego hace ping a todos y te los muestra ordenados por latencia.

Puedes conectarte a:
- **Nodos de la lista** — servidores aprobados por el administrador de la red
- **Un nodo propio** — si alguien de confianza montó su propio servidor, puedes ingresar su URL o IP:puerto directamente
- **Nodo local** — sin conexión, para uso completamente offline

Si ingresas una URL del tipo `203.0.113.42:8765` (IP y puerto sin `http://`), el cliente lo normaliza automáticamente.

---

## Recuperar sesión

Si olvidaste la contraseña local pero recuerdas tus 5 datos personales:

1. Ejecuta `python installer.py`
2. Elige reinstalar
3. Usa exactamente los mismos 5 datos → el sistema reconoce tu identidad

Tus mensajes pendientes en el servidor permanecen hasta que expiren (30 días sin descargar, 7 días después de descargarlos).

Si el sistema hizo wipe automático (5 intentos fallidos de contraseña), ejecuta el instalador de nuevo con los mismos datos. Tu identidad en la red se reconstruye completamente.

---

## Modo offline

Sin internet puedes:
- Cifrar mensajes y guardar el `.json` localmente en `messages/outbox/`
- Descifrar mensajes copiando el `.json` a `messages/inbox/` manualmente
- Ver tus contactos ya guardados

No puedes sin servidor:
- Agregar contactos nuevos (el servidor debe verificar que el alias existe)
- Enviar mensajes por la red
- Ver si alguien está online
- Sincronizar solicitudes de contacto

---

## Seguridad

| Componente | Implementación |
|------------|---------------|
| Cifrado de mensajes | AES-256-GCM (autenticado) |
| Derivación de identidad | Scrypt (resistente a GPU) |
| Clave de sesión | HKDF-SHA256 entre tú y el destinatario |
| Servidor | Zero-knowledge — solo guarda paquetes sellados |
| Sesión local | Cifrada con tu contraseña + wipe automático a 5 intentos |
| Aleatoriedad del token | Dados d12 virtuales o físicos opcionales |
| IPs en el servidor | Se almacenan hasheadas, nunca en texto plano |

### Lo que NO protege

- Si alguien conoce tus 5 datos personales exactos, puede reconstruir tu ID
- El token viaja por un canal externo — ese momento es un punto de atención
- Si te conectas a un nodo con IP:puerto sin HTTPS, los metadatos (quién escribe a quién, cuándo) son visibles en tránsito — el contenido del mensaje sigue cifrado
- No está auditado — es un proyecto en desarrollo activo

**Para uso entre amigos, comunidades y grupos de confianza.**
Para comunicaciones de alto riesgo real: usa Signal.

---

## Preguntas frecuentes

**¿Mis 5 datos personales se guardan en algún lado?**
No. Solo el resultado del KDF (una función matemática irreversible) se guarda en disco, cifrado con tu contraseña local. Los datos originales nunca tocan el disco.

**¿Qué pasa si pierdo el dispositivo?**
Tus mensajes pendientes siguen en el servidor por 30 días. Instala en otro dispositivo con los mismos 5 datos y recuperas acceso completo.

**¿Cómo sabe el destinatario el token?**
No lo sabe automáticamente. Tú debes enviárselo por otro canal (Discord, Telegram, en persona). Eso es intencional: el servidor nunca ve el token.

**¿Puedo tener varias identidades?**
Sí, en carpetas separadas. Cada instalación es completamente independiente.

**¿El servidor sabe quién le escribe a quién?**
Ve los `id_publico` (hashes) del sender y del destinatario, y los timestamps. No puede asociarlos a personas reales a menos que ya sepa quién es cada hash — que solo tú sabes.

**¿Qué es el patrón de rejilla?**
Una capa de transposición estructural aplicada antes del cifrado AES. Agrega ofuscación adicional al orden de los bytes del mensaje. Se configura una vez en el instalador.

**El servidor aparece como "dormido" y tarda en responder**
El nodo maestro corre en Render tier gratuito, que duerme tras 15 minutos sin actividad. El primer ping puede tardar 30-60 segundos en "despertar" el servidor. Los nodos propios en VPS no tienen este problema.
