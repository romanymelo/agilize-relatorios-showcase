"""Camada de portais.

Esta edição pública acompanha a interface (`base.py`) e a captura de PDF
(`captura_pdf.py`), mas não o adaptador do portal da SEFAZ/AL. Veja o
README desta pasta.
"""

import importlib

from .base import (
    AdaptadorIndisponivel,
    Periodo,
    PortalAdapter,
    Relatorio,
)

__all__ = [
    "AdaptadorIndisponivel",
    "Periodo",
    "PortalAdapter",
    "Relatorio",
    "carregar_adaptador",
]


def carregar_adaptador(nome: str) -> PortalAdapter:
    """Carrega `portal.<nome>` e devolve o adaptador que ele expõe.

    Levanta `AdaptadorIndisponivel` quando o módulo não está presente, que é
    o caso desta edição pública para o adaptador `sefaz_al`.
    """
    try:
        modulo = importlib.import_module(f"{__name__}.{nome}")
    except ModuleNotFoundError as erro:
        raise AdaptadorIndisponivel(
            f"O adaptador '{nome}' não acompanha esta edição pública do projeto. "
            f"Veja portal/README.md."
        ) from erro

    try:
        fabrica = modulo.criar_adaptador
    except AttributeError as erro:
        raise AdaptadorIndisponivel(
            f"O módulo '{nome}' não expõe criar_adaptador()."
        ) from erro

    return fabrica()
