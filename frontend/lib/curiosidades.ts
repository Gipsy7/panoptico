// Escolha das "curiosidades" da cidade na home, depois que a pessoa confirma onde está.
// Lógica pura (sem rede): recebe o que a API devolveu e monta os números literais, cada um com a
// média do estado ao lado (quando existe), o link da página e a fonte com data. Sem dado, o item
// não entra. Não há nota, ranking nem adjetivo.

import type { Camara, ContasMunicipio, DinheiroFederalMunicipio, EmendasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

export type CuriosidadeFonte = { nome: string; url?: string; atualizadoEm: string | null };

export type Curiosidade = {
  id: "repasses" | "contas" | "emendas" | "vereadores";
  rotulo: string;
  valor: string;
  /** Explicação curta da unidade, em letra menor. */
  detalhe?: string;
  media?: { rotulo: string; valor: string };
  href: string;
  fonte: CuriosidadeFonte;
};

export type EntradaCuriosidades = {
  cidade: { nome: string; uf: string; ibge: string };
  federal?: DinheiroFederalMunicipio | null;
  contas?: ContasMunicipio | null;
  emendas?: EmendasMunicipio | null;
  camara?: Camara | null;
  /** Último ano fechado dos repasses (o ano em curso soma só os meses já publicados). */
  anoLimiteRepasses: number;
};

export const MAXIMO_CURIOSIDADES = 4;

const positivo = (n: number | null | undefined): n is number => n != null && Number.isFinite(n) && n > 0;

export function escolherCuriosidades(e: EntradaCuriosidades): Curiosidade[] {
  const { cidade } = e;
  const itens: Curiosidade[] = [];

  const serie = e.federal?.serie ?? [];
  const ultimo = serie.filter((s) => s.ano <= e.anoLimiteRepasses).at(-1) ?? serie.at(-1);
  if (e.federal && ultimo && positivo(ultimo.por_habitante)) {
    const fonte = e.federal.fontes[0];
    const datas = e.federal.fontes.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)).sort();
    itens.push({
      id: "repasses",
      rotulo: `A União repassou à prefeitura, por morador, em ${ultimo.ano}`,
      valor: formatarReais(ultimo.por_habitante, true),
      detalhe: "Dinheiro de impostos federais que chega à prefeitura (como o FPM)",
      media: positivo(ultimo.media_estado_por_habitante)
        ? { rotulo: `Média das cidades de ${cidade.uf}`, valor: formatarReais(ultimo.media_estado_por_habitante, true) }
        : undefined,
      href: `/impostos-e-repasses/${cidade.uf}/${cidade.ibge}`,
      fonte: { nome: fonte?.nome ?? "Tesouro Nacional", url: fonte?.url, atualizadoEm: datas[0] ?? null },
    });
  }

  const c = e.contas;
  if (c && positivo(c.despesa_paga) && positivo(c.despesa_por_habitante)) {
    itens.push({
      id: "contas",
      rotulo: `A prefeitura gastou, por morador, em ${c.ano}`,
      valor: formatarReais(c.despesa_por_habitante, true),
      detalhe: "Despesa paga, segundo a prestação de contas da prefeitura",
      media: positivo(c.media_uf_despesa_por_habitante)
        ? { rotulo: `Média das cidades de ${cidade.uf}`, valor: formatarReais(c.media_uf_despesa_por_habitante, true) }
        : undefined,
      href: `/cidade/${cidade.ibge}`,
      fonte: { nome: c.fonte_nome, url: c.fonte_url, atualizadoEm: c.atualizado_em },
    });
  }

  const em = e.emendas;
  if (em) {
    const novo = em.total_geral != null;
    const total = em.total_geral ?? em.total;
    const porHab = novo ? em.por_habitante_geral : em.por_habitante;
    const mediaUf = novo ? em.media_uf_por_habitante_geral : em.media_uf_por_habitante;
    if (positivo(total) && positivo(porHab)) {
      const inicio = em.periodo?.inicio ?? em.desde;
      const fim = em.periodo?.fim ?? em.por_ano.at(-1)?.ano ?? em.desde;
      itens.push({
        id: "emendas",
        rotulo: `Dinheiro de emendas de parlamentares, por morador (${inicio === fim ? inicio : `${inicio} a ${fim}`})`,
        valor: formatarReais(porHab, true),
        detalhe: `Total de ${formatarReais(total, true)} no período`,
        media: positivo(mediaUf)
          ? { rotulo: `Média das cidades de ${cidade.uf}`, valor: formatarReais(mediaUf, true) }
          : undefined,
        href: `/cidade/${cidade.ibge}`,
        fonte: { nome: em.fonte_nome, url: em.fonte_url, atualizadoEm: em.atualizado_em },
      });
    }
  }

  const ve = e.camara?.itens.filter((v) => v.em_exercicio).length ?? 0;
  if (e.camara && ve > 0) {
    itens.push({
      id: "vereadores",
      rotulo: `Câmara Municipal de ${cidade.nome}`,
      valor: `${ve} ${ve === 1 ? "vereador" : "vereadores"}`,
      detalhe: "Em exercício hoje",
      href: `/representantes?uf=${cidade.uf}&municipio=${cidade.ibge}`,
      fonte: { nome: e.camara.fonte_nome, url: e.camara.fonte_url, atualizadoEm: e.camara.atualizado_em },
    });
  }

  return itens.slice(0, MAXIMO_CURIOSIDADES);
}

/** Sorteia uma só curiosidade entre as disponíveis (gerador injetável para os testes). */
export function sortearCuriosidade(itens: readonly Curiosidade[], aleatorio: () => number = Math.random): Curiosidade | null {
  if (!itens.length) return null;
  return itens[Math.min(itens.length - 1, Math.floor(aleatorio() * itens.length))];
}
