"""
ui.py — terminal styling for MyceliumNet
Minimalista, elegante, oscuro. Sin excesos.
"""
import sys
import time

# ANSI color codes
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"

    # Paleta MyceliumNet: blancos, grises, verde micelium, rojo alerta
    WHITE   = "\033[97m"
    GRAY    = "\033[37m"
    DGRAY   = "\033[90m"
    GREEN   = "\033[92m"    # micelium green — confirmaciones
    DGREEN  = "\033[32m"    # dark green — bordes, separadores
    RED     = "\033[91m"    # errores, alertas
    YELLOW  = "\033[93m"    # advertencias
    CYAN    = "\033[96m"    # prompts, inputs
    MAGENTA = "\033[95m"    # tokens, claves visibles


def _supports_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

USE_COLOR = _supports_color()

def c(code, text):
    """Aplica color ANSI a un texto. Exportada para uso en otros módulos."""
    if not USE_COLOR:
        return text
    return f"{code}{text}{C.RESET}"

# alias interno
_c = c


# ── Primitivos ──────────────────────────────────────────────────────────────

def ok(msg):
    print(_c(C.GREEN, f"  ✔  {msg}"))

def err(msg):
    print(_c(C.RED, f"  ✘  {msg}"))

def warn(msg):
    print(_c(C.YELLOW, f"  ⚠  {msg}"))

def info(msg):
    print(_c(C.DGRAY, f"  ·  {msg}"))

def highlight(msg):
    print(_c(C.WHITE + C.BOLD, f"  »  {msg}"))

def token_display(label, value):
    """Muestra un token/clave con estilo especial."""
    print(f"  {_c(C.DGRAY, label)}: {_c(C.MAGENTA + C.BOLD, value)}")


# ── Separadores y estructura ─────────────────────────────────────────────────

def line(char="─", width=72):
    print(_c(C.DGRAY, char * width))

def section(title):
    print()
    print(_c(C.DGREEN, "┌─ ") + _c(C.GREEN + C.BOLD, title.upper()) + _c(C.DGREEN, " " + "─" * max(0, 68 - len(title))))

def blank():
    print()


# ── Banner ───────────────────────────────────────────────────────────────────

def banner():
    from core.constants import BANNER, TAGLINE, VERSION
    if USE_COLOR:
        # Gradiente manual: líneas alternas gray → white
        lines = BANNER.strip("\n").split("\n")
        shades = [C.DGRAY, C.GRAY, C.WHITE, C.WHITE, C.GRAY, C.DGRAY]
        for i, ln in enumerate(lines):
            shade = shades[i % len(shades)]
            print(f"{shade}{ln}{C.RESET}")
    else:
        print(BANNER)
    print(_c(C.DGREEN, f"  {TAGLINE}"))
    print(_c(C.DGRAY, f"  v{VERSION}"))
    blank()


# ── Input con estilo ─────────────────────────────────────────────────────────

def ask(prompt, secret=False):
    """Input estilizado. secret=True oculta lo que escribe (contraseñas)."""
    import getpass
    styled = _c(C.CYAN, f"  ❯ {prompt}: ")
    if secret:
        return getpass.getpass(styled)
    return input(styled).strip()

def ask_choice(prompt, options: list[str]) -> str:
    """Muestra opciones numeradas y retorna la elegida."""
    blank()
    print(_c(C.GRAY, f"  {prompt}"))
    for i, opt in enumerate(options, 1):
        print(_c(C.DGRAY, f"    [{i}]") + f" {opt}")
    while True:
        raw = ask("opción")
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]
        err("Opción inválida.")

def confirm(prompt) -> bool:
    raw = ask(f"{prompt} [s/n]").lower()
    return raw in ("s", "si", "sí", "y", "yes")


# ── Animaciones simples ───────────────────────────────────────────────────────

def thinking(msg="procesando", steps=3):
    """Animación de puntos suspensivos."""
    if not USE_COLOR:
        print(f"  {msg}...")
        return
    for i in range(steps):
        sys.stdout.write(f"\r  {_c(C.DGRAY, msg + '.' * (i+1) + '   ')}")
        sys.stdout.flush()
        time.sleep(0.25)
    sys.stdout.write(f"\r  {' ' * (len(msg) + 10)}\r")
    sys.stdout.flush()

def progress_bar(current, total, width=40, label=""):
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * current / total)
    sys.stdout.write(f"\r  {_c(C.DGREEN, bar)} {_c(C.WHITE, f'{pct}%')} {_c(C.DGRAY, label)}")
    sys.stdout.flush()
    if current >= total:
        print()


# ── Tabla simple ─────────────────────────────────────────────────────────────

def table(rows: list[tuple], headers: list[str] = None):
    """Tabla minimalista de 2 columnas."""
    if headers:
        print(_c(C.DGRAY, f"  {'  '.join(f'{h:<24}' for h in headers)}"))
        line("·", 50)
    for row in rows:
        cols = [f"{str(c):<24}" for c in row]
        print(_c(C.GRAY, "  ") + _c(C.DGRAY, "  ").join(cols))
