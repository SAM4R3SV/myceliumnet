# MyceliumNet — Manual de Usuario
**v0.2.0-alpha**

---

## ¿Qué es MyceliumNet?

Un sistema de mensajería cifrada persona-a-persona. Tu identidad ES tu llave.
Nadie más puede leer tus mensajes — ni el servidor.

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

- **Verificación de servidores** — hace ping automático y muestra latencias
- **Región** — elige tu código de región (ej: +57 para Colombia)
- **Servidor** — selecciona el servidor más cercano o ingresa uno propio
- **5 datos personales** — NUNCA se guardan en disco. Son tu semilla de identidad
- **Alias** — tu nombre público en la red
- **Contraseña local** — protege tu sesión en este dispositivo
- **Patrón de rejilla** — capa de ofuscación estructural
- **Preguntas de recuperación** — por si olvidas la contraseña

> ⚠ Anota tus 5 datos personales en papel. Sin ellos no puedes recuperar tu identidad.

---

## Uso diario

```
python main.py
```

### Menú principal

| Comando    | Acción                        |
|------------|-------------------------------|
| `enviar`   | Cifrar y enviar un mensaje    |
| `recibir`  | Descifrar mensajes recibidos  |
| `contactos`| Gestionar tus contactos       |
| `estado`   | Ver estado del nodo           |
| `salir`    | Cerrar sesión                 |

También puedes escribir solo la primera letra: `e`, `r`, `c`, `s`.

---

## Enviar un mensaje

1. Escribe `enviar` en el menú
2. Ingresa el alias del destinatario (o su ID pública si no está en contactos)
3. El sistema detecta si está online (túnel directo) u offline (bandeja)
4. Elige dados físicos o virtuales para generar el token
5. Escribe tu mensaje
6. **Envía el TOKEN al destinatario por un canal separado** (Discord, en persona, etc.)

> El token es la "otra mitad" de la llave. Sin él, el mensaje no se puede descifrar.

---

## Recibir un mensaje

1. Si estás online, el sistema descarga mensajes del servidor automáticamente
2. O copia el archivo `.json` en `messages/inbox/`
3. Escribe `recibir` en el menú
4. Selecciona el mensaje
5. Ingresa el token que te dio el emisor
6. El mensaje se muestra descifrado

---

## Agregar contactos

Solo funciona con conexión al servidor. El servidor verifica que el ID existe antes de guardar el contacto, y envía una solicitud de aceptación al destinatario.

Datos requeridos:
- Alias del contacto
- ID pública (64 caracteres hex)
- Región (ej: +57)
- Nodo (ej: +57.MYCEL)

---

## Recuperar sesión

Si olvidaste la contraseña pero recuerdas tus 5 datos personales:

1. Ejecuta `python installer.py`
2. Elige reinstalar
3. Usa los mismos 5 datos → el sistema reconocerá tu identidad

Si el dispositivo fue comprometido y el sistema hizo wipe automático (5 intentos fallidos), ejecuta el instalador de nuevo. Tus mensajes en el servidor siguen ahí si no expiraron.

---

## Seguridad

- **AES-256-GCM** — el mismo cifrado que usa Signal
- **Argon2/Scrypt** — KDF resistente a GPU
- **Servidor ciego** — solo guarda paquetes sellados, no puede leerlos
- **Wipe automático** — 5 intentos fallidos borran la sesión local

### Lo que NO protege

- Si alguien conoce tus 5 datos personales exactos, puede intentar reconstruir tu ID
- El token viaja por un canal externo (ese momento es un punto débil)
- No está auditado — es un proyecto en desarrollo

---

## Modo offline

Sin internet, puedes:
- Cifrar mensajes y guardar el `.json` localmente
- Descifrar mensajes recibidos manualmente (copiando el `.json` al inbox)

No puedes (sin servidor):
- Agregar contactos
- Enviar mensajes por la red
- Verificar si alguien está online

---

## Preguntas frecuentes

**¿Mis datos personales se guardan en algún lado?**
No. Solo el resultado del KDF (una función matemática irreversible) se guarda, cifrado con tu contraseña local.

**¿Qué pasa si pierdo el dispositivo?**
Tus mensajes pendientes siguen en el servidor por 30 días. Instala en otro dispositivo con los mismos 5 datos y recuperas el acceso.

**¿Puedo tener varias cuentas?**
Sí, en carpetas separadas. Cada instalación es independiente.

**¿Cómo sé a qué servidor conectarme?**
El instalador hace ping automático y te muestra los disponibles con su latencia. Elige el de menor latencia.
