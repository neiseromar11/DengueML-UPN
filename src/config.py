"""
DengueML-UPN - Módulo de Configuración Segura
=============================================
Lee configuración exclusivamente desde variables de entorno.
No contiene secretos escritos directamente en el código.
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv es opcional; las variables se leen directamente del SO
    pass


def get_config(key: str, default: str = "") -> str:
    """Obtiene un valor de configuración desde variables de entorno."""
    return os.getenv(key, default)


# ---------------------------------------------------------
# Variables de configuración del proyecto
# ---------------------------------------------------------
APP_ENV = get_config("APP_ENV", "development")
LOG_LEVEL = get_config("LOG_LEVEL", "INFO")
ENABLE_AUDIT_LOG = get_config("ENABLE_AUDIT_LOG", "true").lower() == "true"
BACKUP_PATH = get_config("BACKUP_PATH", "./backups")

# Distritos válidos dentro del alcance de DIRIS Lima Centro
DISTRITOS_VALIDOS = [
    "San Juan de Lurigancho", "Rímac", "Cercado de Lima",
    "La Victoria", "Breña", "San Luis", "Jesús María",
    "Lince", "San Isidro", "Pueblo Libre", "Magdalena",
    "San Miguel", "Miraflores", "Surquillo",
    "Todos los distritos (DIRIS Lima Centro)"
]

# Horizontes de predicción permitidos
HORIZONTES_VALIDOS = ["2 semanas", "3 semanas", "4 semanas"]

# Periodos válidos
PERIODOS_VALIDOS = ["Ene 2023 – Dic 2024", "Últimas 12 semanas"]
