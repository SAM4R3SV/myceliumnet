```
___  _____   __ _____  _____  _      _____  _   _ ___  ___ _   _  _____  _____
|  \/  |\ \ / //  __ \|  ___|| |    |_   _|| | | ||  \/  || \ | ||  ___||_   _|
| .  . | \ V / | /  \/| |__  | |      | |  | | | || .  . ||  \| || |__    | |
| |\/| |  \ /  | |    |  __| | |      | |  | | | || |\/| || . ` ||  __|   | |
| |  | |  | |  | \__/\| |___ | |____ _| |_ | |_| || |  | || |\  || |___   | |
\_|  |_/  \_/   \____/\____/ \_____/ \___/  \___/ \_|  |_/\_| \_/\____/   \_/

[ encrypted mesh · trust no server · know your node ]   v0.3.0-alpha
```

Proyecto personal de mensajería cifrada persona-a-persona, hecho por mi cuenta mientras aprendía sobre redes y criptografía básica.
**La idea es que tu identidad sea tu llave y que el servidor no pueda leer el contenido de los mensajes.**

> ⚠️ Esto es un proyecto en progreso, hecho a pulso y todavía con bastantes cosas sin pulir. No está pensado para nada serio ni crítico, es más un experimento personal que voy mejorando con el tiempo.

---

## Qué intenta hacer

- No usa cuentas con contraseña tradicional.
- El servidor solo debería guardar paquetes ya cifrados, no contenido legible.
- Hay una idea de red de nodos por región (`+57.MYCEL`, `+1.NYC`, etc.) aunque todavía es bastante experimental.
- Intenta funcionar offline y sincronizar después.

No prometo que todo esto esté implementado de forma perfecta — hay partes que funcionan mejor que otras.

---

## Problemas conocidos

Hay varias cosas rotas o a medias ahora mismo:

- Las solicitudes de contacto a veces no sincronizan bien el estado entre nodos.
- La actualización del cliente (OTA) no es confiable todavía, básicamente no funciona del todo.
- Hay fallos sueltos en el discovery de nodos y en reconexión que no he logrado aislar bien.

Voy a ir corrigiendo esto poco a poco. No descarto reescribir partes grandes del proyecto más adelante si encuentro que la base tiene problemas de fondo que no se pueden parchar fácil.

---

## Instalación

**Requisitos:** Python 3.10+

```bash
git clone https://github.com/SAM4R3SV/myceliumnet
cd myceliumnet
pip install -r requirements.txt
python installer.py
```

Luego, cada vez:
```bash
python main.py
```

---

## Idea general de cómo funciona

```
1. Instalas con algunos datos personales → se genera tu ID + una llave local
   (en teoría los datos no quedan guardados tal cual en disco)

2. Para enviar: se genera un token random
   El mensaje se cifra y el token viaja por un canal separado al receptor

3. Para recibir: el receptor usa el token + sus datos para reconstruir la llave

4. El servidor solo ve paquetes sellados, identificados por hash
   Los mensajes expiran después de un tiempo
```

Es la idea de diseño, no garantizo que cada parte esté implementada exactamente así de bien en la práctica.

---

## Estructura del proyecto

```
myceliumnet/
├── installer.py          # wizard de configuración
├── main.py               # cliente principal
├── core/                 # constantes, UI, identidad, cripto
├── network/               # discovery y protocolo entre nodos
├── docs/                  # manuales (medio incompletos todavía)
└── server/                # código del servidor (aparte)
```

---

## Roadmap / cosas pendientes

- [ ] Arreglar sincronización de solicitudes de contacto entre nodos
- [ ] Hacer que la actualización OTA del cliente funcione de verdad
- [ ] Logs en tiempo real en el panel admin
- [ ] Conexión directa entre dos usuarios cuando ambos están online
- [ ] Posiblemente una interfaz gráfica más adelante
- [ ] Reescribir partes del proyecto si encuentro que vale más la pena que seguir parchando

---

*MyceliumNet — un proyecto que sigo construyendo a medida que aprendo.*