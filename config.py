"""Configuración leída del fichero .env.

El .env no entra en git ni viaja en el rsync del deploy: se copia a mano a la
Raspberry una única vez.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent
load_dotenv(RAIZ / ".env")


def _entero(nombre: str) -> int:
    valor = os.environ.get(nombre, "").strip()
    if not valor:
        return 0
    if not valor.isdigit():
        raise ValueError(
            f"{nombre} debe ser el ID numérico de Discord, no «{valor}». "
            "Actívate el modo desarrollador en Discord y usa «Copiar ID»."
        )
    return int(valor)


def _lista_enteros(nombre: str) -> tuple[int, ...]:
    """Lee una lista de IDs separados por comas.

    Acepta espacios y saltos de línea alrededor, y también punto y coma, porque
    es lo que sale al pegar varios IDs a mano. Quita repetidos conservando el
    orden: el primero es el canal principal.
    """
    crudo = os.environ.get(nombre, "").replace(";", ",").replace("\n", ",")
    valores: list[int] = []
    for trozo in crudo.split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if not trozo.isdigit():
            raise ValueError(
                f"{nombre} contiene «{trozo}», que no es un ID de Discord. "
                "Deben ser números separados por comas, por ejemplo:\n"
                f"  {nombre}=123456789012345678,987654321098765432"
            )
        valores.append(int(trozo))
    return tuple(dict.fromkeys(valores))


TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()

# Canales donde vive el bot, separados por comas. Fuera de ellos los comandos
# responden con un aviso privado en vez de ensuciar otros canales.
CANALES = _lista_enteros("CANAL_ID")

# Adonde van los avisos de una criatura que no tiene canal propio guardado
# (las nacidas antes de que el bot admitiera varios canales).
CANAL_PRINCIPAL = CANALES[0] if CANALES else 0

# Servidores donde registrar los slash commands directamente, separados por
# comas. Así aparecen al instante; sin esto Discord tarda hasta una hora en
# propagarlos globalmente. El bot funciona en todos los servidores a los que se
# le invite: cada uno lleva sus propias mascotas y su propio ranking.
GUILDS = _lista_enteros("GUILD_ID")

# Canales donde el bot mantiene el manual, separados por comas. Ahí publica las
# páginas de `paginas_de_ayuda()` y las **edita en el sitio** en cada arranque,
# así que no pueden quedarse desfasadas: el texto sale de las mismas constantes
# que el juego.
#
# Es opcional, y sin él no se publica nada: en local no hay canal, y un servidor
# sin canal de info sigue funcionando igual. Admite varios porque cada servidor
# necesita el suyo —un canal vive en un servidor y sólo lo ve quien está en él—.
CANALES_INFO = _lista_enteros("CANAL_INFO_ID")

RUTA_BD = Path(os.environ.get("RUTA_BD", RAIZ / "tamagotchi.db"))

# --- IA: que las criaturas hablen ------------------------------------------

# NVIDIA cloud expone una API compatible con la de OpenAI.
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "").strip()
NVIDIA_URL = os.environ.get(
    "NVIDIA_URL", "https://integrate.api.nvidia.com/v1/chat/completions"
)
# DeepSeek expone la misma API compatible con OpenAI, así que sirve el mismo
# cliente. Se paga aparte y es opcional: sin esta clave el bot tira de NVIDIA.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_URL = os.environ.get(
    "DEEPSEEK_URL", "https://api.deepseek.com/chat/completions"
)


@dataclass(frozen=True)
class Proveedor:
    """A dónde va cada modelo, con qué clave y con qué campos propios.

    Existe porque un modelo de pago y otro gratuito no comparten ni URL ni
    clave: antes había una sola de cada, así que la cadena de recambio —que es
    lo que evita que el bot se quede mudo— sólo podía saltar entre modelos del
    mismo proveedor.
    """

    nombre: str
    url: str
    api_key: str
    # Campos que sólo entiende este proveedor. Hoy los dos sirven para lo mismo:
    # apagar el razonamiento, que aquí no aporta nada —son tres líneas en boca
    # de un pollito— y en DeepSeek viene encendido en `high` y se cobra.
    extras: dict = field(default_factory=dict)


PROVEEDOR_POR_DEFECTO = "nvidia"

PROVEEDORES: dict[str, Proveedor] = {
    "nvidia": Proveedor(
        nombre="nvidia", url=NVIDIA_URL, api_key=NVIDIA_API_KEY,
        extras={"chat_template_kwargs": {"thinking": False}},
    ),
    "deepseek": Proveedor(
        nombre="deepseek", url=DEEPSEEK_URL, api_key=DEEPSEEK_API_KEY,
        extras={"thinking": {"type": "disabled"}},
    ),
}


def resolver_modelo(entrada: str) -> tuple[Proveedor, str]:
    """`«deepseek:deepseek-v4-pro»` → (proveedor DeepSeek, «deepseek-v4-pro»).

    Sin prefijo se asume NVIDIA, así que los `.env` anteriores siguen valiendo.
    Un prefijo desconocido —una errata— se trata como parte del nombre y sale
    por NVIDIA: fallará ese modelo y la cadena de recambio hará el resto, que es
    mucho mejor que dejar mudas a las criaturas por una letra de más.
    """
    proveedor, separador, modelo = entrada.partition(":")
    if separador and proveedor in PROVEEDORES:
        return PROVEEDORES[proveedor], modelo
    return PROVEEDORES[PROVEEDOR_POR_DEFECTO], entrada


# Modelos a probar en orden, cada uno con su proveedor delante. NVIDIA marca
# modelos como DEGRADED sin avisar —le pasó a deepseek-v4-flash a las pocas
# horas de ponerlo en producción— así que el bot se pasa solo al siguiente en
# vez de quedarse mudo hasta que alguien lo redespliegue.
#
# El razonador va el último aunque funcione: gasta más de mil caracteres
# pensando en inglés para soltar tres líneas de pollito, así que es lento y
# caro para lo que se le pide. Se queda como tercer recambio porque tener uno
# más ha salvado el día varias veces.
# DeepSeek va el primero **aunque no todo el mundo pague**: los modelos de un
# proveedor sin clave se saltan solos, así que sin `DEEPSEEK_API_KEY` esta lista
# se comporta exactamente igual que antes. Poner la clave es lo único que hace
# falta para que pase a mandar, sin tocar esta variable en cada máquina.
MODELOS_IA = tuple(
    m.strip() for m in os.environ.get(
        "MODELO_IA",
        "deepseek:deepseek-v4-pro,"
        "mistralai/mistral-nemotron,"
        "deepseek-ai/deepseek-v4-flash,"
        "nvidia/llama-3.3-nemotron-super-49b-v1.5",
    ).split(",") if m.strip()
)

# Sin ninguna clave el bot arranca igual: las criaturas contestan con sus frases
# de respaldo escritas a mano. Hablar es un extra, no un requisito. Basta con la
# de un proveedor: se mira sobre los modelos configurados y no sobre todos los
# proveedores, porque tener clave de uno que no usas no hace hablar a nadie.
IA_ACTIVA = any(resolver_modelo(m)[0].api_key for m in MODELOS_IA)

# Cuántos mensajes puede mandarle cada persona a su criatura por hora, y cuánto
# hay que esperar entre uno y otro.
LIMITE_CHARLA_POR_HORA = 20
SEGUNDOS_ENTRE_MENSAJES = 4

# Cada cuánto se revisa si alguna criatura se ha muerto de hambre.
MINUTOS_ENTRE_REVISIONES = 15


def verificar() -> None:
    """Falla pronto y con un mensaje útil si falta algo esencial."""
    problemas = []
    if not TOKEN:
        problemas.append(
            "Falta DISCORD_TOKEN. Sácalo de "
            "https://discord.com/developers/applications → tu app → Bot → Reset Token."
        )
    if not CANALES:
        problemas.append(
            "Falta CANAL_ID. Clic derecho sobre el canal → Copiar ID "
            "(hace falta activar Ajustes → Avanzado → Modo desarrollador). "
            "Puedes poner varios separados por comas."
        )
    if problemas:
        raise SystemExit(
            "No puedo arrancar:\n  - " + "\n  - ".join(problemas)
            + f"\n\nEdita {RAIZ / '.env'} (tienes .env.ejemplo de plantilla)."
        )
