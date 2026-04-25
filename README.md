```
___  _____   __ _____  _____  _      _____  _   _ ___  ___ _   _  _____  _____
|  \/  |\ \ / //  __ \|  ___|| |    |_   _|| | | ||  \/  || \ | ||  ___||_   _|
| .  . | \ V / | /  \/| |__  | |      | |  | | | || .  . ||  \| || |__    | |
| |\/| |  \ /  | |    |  __| | |      | |  | | | || |\/| || . ` ||  __|   | |
| |  | |  | |  | \__/\| |___ | |____ _| |_ | |_| || |  | || |\  || |___   | |
\_|  |_/  \_/   \____/\____/ \_____/ \___/  \___/ \_|  |_/\_| \_/\____/   \_/

[ encrypted mesh · trust no server · know your node ]   v0.2.0-alpha
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
│   ├── constants.py      # versión, códigos de región, constantes
│   ├── ui.py             # terminal styling (verde micelium)
│   ├── identity.py       # KDF, sesión cifrada, wipe automático
│   └── crypto.py         # AES-256-GCM, rejilla, dados d12
├── network/
│   ├── server_discovery.py  # ping, latencia, selección de servidor
│   └── node_protocol.py     # protocolo entre nodos, túneles, transferencias
├── docs/
│   ├── USER_MANUAL.md    # manual de usuario
│   └── SERVER_MANUAL.md  # manual para operadores de nodo
└── server/               # código del servidor (distribuido por separado)
```

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

- [x] Cifrado local (AES-256-GCM + Argon2)
- [x] Installer con wizard completo
- [x] Descubrimiento de servidores con ping
- [x] Protocolo de nodos distribuidos
- [x] Solicitudes de contacto verificadas por servidor
- [x] Transferencia entre nodos
- [ ] Servidor de referencia (FastAPI + Supabase)
- [ ] Túnel live P2P cuando ambos están online
- [ ] GUI con customtkinter
- [ ] Plugin Minecraft (Paper/Spigot)

---

## Contribuir

Proyecto personal en desarrollo activo. Issues y PRs bienvenidos.
El código del cliente es libre. El protocolo de servidor tiene restricciones — ver `docs/SERVER_MANUAL.md`.

---

*MyceliumNet — como el micelio: invisible, distribuido, conectado.*
