/**
 * Fundo inerte para diálogos (gaveta, folha de filtros, menu do celular).
 *
 * `aria-modal` é ignorado pelo TalkBack: sem isto, o leitor de tela sai do diálogo e lê a página
 * por trás. Com `inert`, o resto da página some para foco, clique e leitor de tela.
 *
 * Marca `inert` em tudo o que não é o diálogo nem um de seus ancestrais (descendo pelos ancestrais
 * até o <body>). `manter` lista elementos extras que ficam ativos (ex.: o botão que abre e fecha o
 * diálogo, o fundo clicável). Devolve a função que desfaz; ela é idempotente e só remove o que
 * ela mesma marcou (diálogos aninhados não se atrapalham). Chame-a no cleanup do efeito.
 */
export function tornarFundoInerte(aberto: Element, manter: Array<Element | null | undefined> = []): () => void {
  const alvos = [aberto, ...manter].filter((e): e is Element => !!e);
  const marcados: Element[] = [];

  const percorrer = (pai: Element) => {
    for (const filho of Array.from(pai.children)) {
      if (alvos.includes(filho)) continue;
      if (alvos.some((a) => filho.contains(a))) {
        percorrer(filho);
      } else if (!filho.hasAttribute("inert") && !["SCRIPT", "STYLE", "LINK", "TEMPLATE"].includes(filho.tagName)) {
        filho.setAttribute("inert", "");
        marcados.push(filho);
      }
    }
  };
  percorrer(document.body);

  let desfeito = false;
  return () => {
    if (desfeito) return;
    desfeito = true;
    for (const e of marcados) e.removeAttribute("inert");
  };
}
