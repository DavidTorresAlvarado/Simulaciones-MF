# Variables generales
GRAVEDAD = 9.81
DIAMETRO_TUBERIA = 0.1
COLOR_HOMOGENEO = "#2ecc71"
COLOR_HETEROGENEO = "#f1c40f"
COLOR_SALTACION = "#e67e22"
COLOR_LECHO = "#e74c3c"

# ESTO ES LO QUE TE FALTA
BASE_FLUIDOS = {
    "Agua": {"rho_f": 1000, "mu": 0.001, "nu": 1e-6},
    "Aceite": {"rho_f": 850, "mu": 0.05, "nu": 5e-5},
    "Glicerina": {"rho_f": 1260, "mu": 1.4, "nu": 0.001}
}