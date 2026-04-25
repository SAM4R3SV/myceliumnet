BANNER = r"""
___  _____   __ _____  _____  _      _____  _   _ ___  ___ _   _  _____  _____
|  \/  |\ \ / //  __ \|  ___|| |    |_   _|| | | ||  \/  || \ | ||  ___||_   _|
| .  . | \ V / | /  \/| |__  | |      | |  | | | || .  . ||  \| || |__    | |
| |\/| |  \ /  | |    |  __| | |      | |  | | | || |\/| || . ` ||  __|   | |
| |  | |  | |  | \__/\| |___ | |____ _| |_ | |_| || |  | || |\  || |___   | |
\_|  |_/  \_/   \____/\____/ \_____/ \___/  \___/ \_|  |_/\_| \_/\____/   \_/
"""

TAGLINE  = "[ encrypted mesh · trust no server · know your node ]"
VERSION  = "0.2.0-alpha"
APP_NAME = "MyceliumNet"

# Nodo raiz principal
ROOT_NODE_ID  = "+57.MYCEL"
ROOT_NODE_URL = "https://myceliumnet-main.supabase.co"

# Region prefix codes
REGION_CODES = {
    "+57": "Colombia",
    "+1":  "USA/Canada",
    "+52": "Mexico",
    "+34": "Espana",
    "+54": "Argentina",
    "+55": "Brasil",
    "+44": "UK",
    "+49": "Alemania",
    "+0":  "Local/Sin region",
}

# Jerarquia de nodos:
#   Raiz:     +57             -> nodo principal de region (uno por pais)
#   Nodo:     +57.MYCEL       -> servidor con nombre dentro de la region
#   Subnodo:  +57.MYCEL.BAQ   -> nodo local (ciudad, comunidad, servidor privado)
NODE_ID_SEPARATOR = "."
MAX_NODE_DEPTH    = 3

# Security constants
MAX_LOGIN_ATTEMPTS  = 5
SESSION_TIMEOUT_MIN = 30
MSG_TTL_UNCLAIMED   = 30
MSG_TTL_CLAIMED     = 7
DICE_FACES          = 12

# Session recovery
RECOVERY_CATEGORIES = ["primera_mascota", "ciudad_favorita", "primer_colegio",
                        "apodo_infancia", "pelicula_favorita", "libro_favorito"]
