"""Captura do PDF a partir da página que o portal abriu.

Na prática, um mesmo portal entrega o relatório de três formas diferentes
dependendo do módulo: como URL direta, como `blob:` gerado no navegador, ou
embutido num `<embed>`/`<iframe>` em base64. Nenhuma estratégia sozinha cobre
todos os casos, então elas são tentadas em cascata, da mais fiel à mais
tolerante. A última recorre a imprimir a página, o que sempre produz um
arquivo, ainda que com menos fidelidade que o original.
"""

import base64


def salvar(context, page, destino: str) -> bool:
    """Tenta salvar o PDF da `page` em `destino`. Devolve True se conseguiu."""
    estrategias = (
        _via_fetch_na_pagina,
        _via_requisicao_autenticada,
        _via_embed_base64,
        _via_impressao,
    )
    for estrategia in estrategias:
        try:
            if estrategia(context, page, destino):
                return True
        except Exception:
            continue
    return False


def _via_fetch_na_pagina(context, page, destino: str) -> bool:
    """Busca a própria URL de dentro da página.

    Funciona para `blob:`, que só existe no contexto do navegador e não pode
    ser baixado de fora dele.
    """
    bytes_pdf = page.evaluate(
        """async () => {
            const url = window.location.href;
            if (url && (url.startsWith('http') || url.startsWith('blob:'))) {
                const r = await fetch(url);
                const bf = await r.arrayBuffer();
                return Array.from(new Uint8Array(bf));
            }
            return null;
        }"""
    )
    if not bytes_pdf:
        return False
    with open(destino, "wb") as f:
        f.write(bytes(bytes_pdf))
    return True


def _via_requisicao_autenticada(context, page, destino: str) -> bool:
    """Baixa pela API de requisições do contexto, que carrega os cookies da sessão."""
    if not page.url.startswith("http"):
        return False
    with open(destino, "wb") as f:
        f.write(context.request.get(page.url).body())
    return True


def _via_embed_base64(context, page, destino: str) -> bool:
    """Extrai o PDF embutido num visualizador na própria página."""
    b64_pdf = page.evaluate(
        """async () => {
            const el = document.querySelector('embed, object, iframe');
            if (!el) return null;
            const url = el.src || el.data;
            if (!url || url.includes('about:blank')) return null;

            if (url.startsWith('data:application/pdf;base64,')) {
                return url.split(',')[1];
            }

            const res = await fetch(url);
            const buffer = await res.arrayBuffer();
            const bytes = new Uint8Array(buffer);
            let binary = '';
            for (let i = 0; i < bytes.byteLength; i++) {
                binary += String.fromCharCode(bytes[i]);
            }
            return window.btoa(binary);
        }"""
    )
    if not b64_pdf:
        return False
    with open(destino, "wb") as f:
        f.write(base64.b64decode(b64_pdf))
    return True


def _via_impressao(context, page, destino: str) -> bool:
    """Último recurso: imprime a página renderizada."""
    page.pdf(path=destino, format="A4")
    return True
