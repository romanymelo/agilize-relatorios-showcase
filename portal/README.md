# Camada de portais

Esta pasta define o contrato que separa a aplicação do portal de onde os
relatórios são extraídos.

| Arquivo | Conteúdo |
|---|---|
| `base.py` | A interface `PortalAdapter` e os tipos `Relatorio` e `Periodo` |
| `captura_pdf.py` | As quatro estratégias de captura de PDF, em cascata |
| `__init__.py` | Carregamento dinâmico do adaptador por nome |
| `sefaz_al.py` | **Não incluído nesta edição pública** |

## Por que `sefaz_al.py` não está aqui

O adaptador da SEFAZ/AL é o núcleo comercial do projeto. Ele concentra o que
levou mais tempo para existir e o que não se deduz lendo o código: as URLs
internas de cada um dos três sistemas, os seletores que sobrevivem ao HTML
real do portal, os tempos de espera calibrados na tentativa e erro contra um
serviço instável, e as táticas de autenticação que cada subsistema exige —
um aceita preenchimento direto do campo, outro só funciona digitando com o
teclado depois de clicar no rótulo.

Esse conhecimento operacional é o que diferencia o produto. O restante do
projeto está publicado por inteiro.

## Implementando um adaptador

Qualquer portal pode ser plugado implementando `PortalAdapter` e expondo uma
função `criar_adaptador()` no módulo:

```python
# portal/meu_portal.py
from .base import PortalAdapter, Periodo, Relatorio


class MeuPortal(PortalAdapter):
    nome_portal = "Meu Portal"

    def autenticar(self, page, usuario, senha):
        page.goto("https://exemplo.gov.br/login")
        page.get_by_placeholder("Usuário").fill(usuario)
        page.get_by_placeholder("Senha").fill(senha)
        page.get_by_role("button", name="Entrar").click()

    def listar_relatorios(self, page, solicitados):
        disponiveis = [
            Relatorio(codigo="extrato", nome="Extrato"),
            Relatorio(codigo="notas", nome="Notas de Entrada", exige_periodo=True),
        ]
        return [r for r in disponiveis if r.codigo in solicitados]

    def emitir(self, page, relatorio, periodo):
        if relatorio.exige_periodo:
            page.get_by_label("Data inicial").fill(periodo.inicio)
            page.get_by_label("Data final").fill(periodo.fim)
        with page.expect_popup() as popup:
            page.get_by_role("button", name="Emitir").click()
        return popup.value


def criar_adaptador():
    return MeuPortal()
```

A aplicação cuida do resto: contexto isolado por empresa, barra de progresso,
captura do PDF, nomeação do arquivo, isolamento de erros e planilha de status.
