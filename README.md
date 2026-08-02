# MyceliumNet

Mensajería cifrada de extremo a extremo, minimalista, pensada para correr desde una terminal, incluido Termux en Android.

> **Estado: alpha, en migración activa.** Esta versión usa `mnv2`: identidad X25519 aleatoria, backup obligatorio y payload sin rejilla.

## Resumen

MyceliumNet es un cliente de mensajería cifrada con estas propiedades:

- Cifrado E2E con X25519 + AES-256-GCM.
- Identidad pública basada en clave pública, sin cuenta tradicional.
- Servidor zero-knowledge: solo retransmite y almacena paquetes cifrados.
- Dependencias ligeras de runtime.

## Instalación

```bash
git clone https://github.com/SAM4R3SV/myceliumnet.git
cd myceliumnet
pip install -r requirements.txt
python installer.py
```

Durante la instalación:

- No se piden datos personales para la identidad.
- Debes guardar el backup privado que se muestra una sola vez.
- El instalador no avanza hasta que confirmes ese backup.

## Uso

```bash
python main.py
```

Desde el menú puedes enviar, recibir, gestionar contactos y ver el estado del nodo.

## Seguridad

Garantizado por el diseño actual:

- El secreto compartido converge matemáticamente entre dos dispositivos.
- Tu identidad no depende de datos personales memorizables.
- El servidor no puede leer el contenido de los mensajes.

Pendiente por roadmap:

- Perfect Forward Secrecy.
- Reducción de inferencia del grafo social.
- Hardening completo del servidor.

## Migración

Si venías de `mnv1`:

- La identidad anterior no es compatible con esta versión.
- Debes reinstalar y generar una identidad nueva.
- Tus contactos también deben estar en `mnv2`.

## Uso comercial y sugerencias

Este repositorio está orientado a uso comercial interno o privado. Si quieres proponer cambios, abre una issue con la sugerencia y el contexto; no se aceptan cambios directos sin revisión.

## Licencia

Pendiente de definir.
