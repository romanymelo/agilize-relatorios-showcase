"""Contrato que um adaptador de portal precisa implementar.

Cada portal de origem (uma secretaria da fazenda, por exemplo) tem o seu
próprio fluxo de login, a sua própria forma de listar relatórios e o seu
próprio jeito de entregar o PDF. Tudo isso fica atrás desta interface, de
modo que o restante da aplicação — interface gráfica, lote, progresso,
tratamento de erro — não sabe nada sobre nenhum portal específico.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Periodo:
    """Intervalo de datas, no formato DD/MM/AAAA, exigido por alguns relatórios."""

    inicio: str
    fim: str


@dataclass(frozen=True)
class Relatorio:
    """Um relatório disponível no portal para a empresa autenticada."""

    codigo: str
    nome: str
    exige_periodo: bool = False


class AdaptadorIndisponivel(RuntimeError):
    """O adaptador pedido não está instalado nesta cópia do projeto."""


class PortalAdapter(ABC):
    """Interface mínima de um portal.

    O ciclo de vida é sempre o mesmo, e quem orquestra é a aplicação:

        adaptador.autenticar(page, usuario, senha)
        for relatorio in adaptador.listar_relatorios(page, solicitados):
            pagina_pdf = adaptador.emitir(page, relatorio, periodo)
            captura_pdf.salvar(context, pagina_pdf, destino)

    A implementação recebe um `Page` do Playwright já posicionado num
    contexto de navegador isolado e exclusivo daquela empresa, e não
    precisa se preocupar com limpeza de sessão nem com logout.
    """

    nome_portal: str = "portal genérico"

    @abstractmethod
    def autenticar(self, page, usuario: str, senha: str) -> None:
        """Deixa a sessão autenticada ou levanta exceção."""

    @abstractmethod
    def listar_relatorios(self, page, solicitados: set[str]) -> list[Relatorio]:
        """Devolve os relatórios realmente disponíveis, filtrados pelos códigos pedidos."""

    @abstractmethod
    def emitir(self, page, relatorio: Relatorio, periodo: Periodo):
        """Emite o relatório e devolve a `Page` onde o PDF foi aberto."""
