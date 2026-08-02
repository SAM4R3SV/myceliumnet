# MyceliumNet — Manual de Usuario
**v0.4.0-alpha**

## Qué es MyceliumNet

Sistema de mensajería cifrada persona a persona. Tu identidad es una clave pública X25519 y tus mensajes no se leen en el servidor.

## Requisitos

- Python 3.10 o superior
- Windows, Linux o macOS
- Internet opcional; el modo local sigue funcionando sin red

## Instalación

1. Descarga y descomprime el proyecto.
2. Abre una terminal en la carpeta raíz.
3. Instala dependencias con `pip install -r requirements.txt`.
4. Ejecuta `python installer.py`.

Durante la instalación:

- No se piden datos personales para la identidad.
- Se genera un keypair X25519 nuevo.
- La clave privada se muestra una sola vez y debes guardarla.
- El instalador no sigue hasta que confirmes el backup.

## Uso diario

Ejecuta `python main.py`.

Comandos principales:

- `enviar` para cifrar y enviar un mensaje.
- `recibir` para descifrar mensajes nuevos.
- `contactos` para gestionar contactos.
- `estado` para ver tu sesión y servidor.
- `salir` para cerrar sesión.

## Enviar un mensaje

1. Elige `enviar`.
2. Selecciona un contacto o ingresa su `ID_publico`.
3. El cliente detecta si el destinatario está online.
4. Genera el token con dados virtuales o con dados físicos ingresados manualmente.
5. Escribe el mensaje.
6. Envía el token por otro canal.

## Recibir un mensaje

1. Elige `recibir`.
2. Si estás online, el cliente descarga mensajes del servidor.
3. Selecciona el mensaje.
4. Ingresa el token compartido.
5. Lee el mensaje descifrado.

## Contactos

Los contactos se gestionan desde `contactos`.

- El sistema sincroniza solicitudes pendientes cuando entras al menú.
- Puedes buscar por alias o ingresar el ID manualmente si hace falta.
- Si aceptas una solicitud, el contacto queda marcado como confirmado.

## Estado

La pantalla `estado` muestra:

- Alias, región y nodo.
- Servidor activo.
- Estado online o local.
- Versión del payload.
- Tu `ID_publico`.
- Cantidad de mensajes en inbox y outbox.

## Recuperar sesión

Si olvidas la contraseña local:

1. Reinstala con `python installer.py`.
2. Restaura tu backup privado.
3. Crea una nueva contraseña local.

Si no guardaste el backup, no hay recuperación de la identidad.

## Modo offline

Sin internet puedes:

- Guardar mensajes cifrados localmente.
- Descifrar archivos `.json` copiados manualmente.
- Ver contactos ya guardados.

Sin servidor no puedes:

- Agregar contactos nuevos.
- Enviar mensajes por red.
- Saber si alguien está online.

## Seguridad

| Componente | Implementación |
|---|---|
| Identidad | X25519 aleatorio |
| Mensajes | AES-256-GCM |
| Secreto compartido | X25519 + HKDF-SHA256 |
| Sesión local | Cifrada con tu contraseña |
| Token | Dados virtuales o físicos |

## Preguntas frecuentes

**¿Se piden 5 datos personales?**
No. Esa versión ya no existe.

**¿Qué pasa si pierdo el dispositivo?**
Puedes recuperar la identidad solo si guardaste el backup privado.

**¿Qué es la rejilla?**
Ya no existe. El cifrado actual usa AES-256-GCM sin esa capa.

**¿El servidor puede leer mis mensajes?**
No. Solo ve paquetes cifrados y metadatos mínimos.
