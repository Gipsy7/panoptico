/**
 * Cartão do perfil em imagem (Feed e Stories): escolhe qual número vai grande e quais
 * vão na faixa. Mesmos números e médias dos cartões do perfil; número sem média no
 * perfil também aparece sem média aqui (nunca se inventa média). Função pura, testada em
 * cartao.test.ts; o desenho fica em lib/og-cartao.tsx.
 */
import { formatarGastos, formatarReaisCompacto } from "@/lib/formato";

const INTEIRO = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const DECIMAL = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export type FormatoCartao = "feed" | "stories";

export function lerFormato(valor: string | null): FormatoCartao {
  return valor === "stories" ? "stories" : "feed";
}

/** Um número do cartão. `media` e `nota` são linhas de contexto (média da Casa, ou o que a fonte diz). */
export type NumeroCartao = {
  rotulo: string;
  valor: string;
  /** Texto da primeira linha menor, já com o "de N": "de 118 votações de 2026". */
  complemento?: string;
  /** "Média da Câmara: 104 de 118". Só existe quando o perfil mostra média para o número. */
  media?: string;
  nota?: string;
};

export type DadosCartao = {
  nome: string;
  /** "Deputado federal · MDB · SC". */
  contexto: string;
  foto: string | null;
  principal: NumeroCartao | null;
  /** Até 3 números da faixa clara. */
  outros: NumeroCartao[];
  /** Frase factual para o cartão sem número (ex.: Executivo). */
  frase: string | null;
  /** "Fonte: Câmara dos Deputados · atualizado em 10/10/2026". */
  fonte: string;
};

/** Média em percentual vira contagem sobre o mesmo total ("104" de 118). */
export function mediaEmContagem(percentual: number, total: number): number {
  return Math.round((percentual * total) / 100);
}

function textoMedia(rotuloCasa: string, valor: string): string {
  return `${rotuloCasa}: ${valor}`;
}

/**
 * Principal = primeiro número com média; se nenhum tiver, o primeiro que não seja zero (um "0" enorme
 * sem a média ao lado parece acusação e costuma ser dado que a fonte não publica). O resto vai à faixa (até 3).
 */
export function escolherNumeros(candidatos: NumeroCartao[]): {
  principal: NumeroCartao | null;
  outros: NumeroCartao[];
} {
  let i = candidatos.findIndex((c) => c.media !== undefined);
  if (i < 0) i = candidatos.findIndex((c) => !/^0(,0+)?$/.test(c.valor));
  if (i < 0) return { principal: null, outros: candidatos.slice(0, 3) };
  return {
    principal: candidatos[i],
    outros: candidatos.filter((_, j) => j !== i).slice(0, 3),
  };
}

/** Diz o cargo da pessoa: "Deputado federal · MDB · SC". */
export function juntarContexto(partes: (string | null | undefined)[]): string {
  return partes.filter(Boolean).join(" · ");
}

type EntradaFederal = {
  nome: string;
  casa: "camara" | "senado";
  cargo: string;
  partido: string | null;
  uf: string | null;
  foto: string | null;
  fonte: string;
  presenca?: {
    ano: number;
    votou: number;
    total_votacoes: number;
    media_casa_percentual: number | null;
  } | null;
  gastos?: { ano: number; total: number; media_casa: number } | null;
  projetos?: {
    desde: string;
    primeiro_autor: number;
    media_casa_primeiro_autor: number;
  } | null;
  governo?: {
    iguais: number;
    total: number;
    media_percentual: number | null;
  } | null;
};

export function montarFederal(e: EntradaFederal): DadosCartao {
  const casa = e.casa === "camara" ? "Média da Câmara" : "Média do Senado";
  const c: NumeroCartao[] = [];
  const p = e.presenca;
  if (p && p.total_votacoes > 0) {
    c.push({
      rotulo: `Votou em ${p.ano}`,
      valor: String(p.votou),
      complemento: `das ${p.total_votacoes} votações de ${p.ano}`,
      media:
        p.media_casa_percentual !== null
          ? textoMedia(
              casa,
              `${mediaEmContagem(p.media_casa_percentual, p.total_votacoes)} de ${p.total_votacoes}`,
            )
          : undefined,
    });
  }
  if (e.gastos) {
    c.push({
      rotulo: "Gastos do gabinete (cota)",
      valor:
        e.gastos.total === 0
          ? formatarGastos(0)
          : formatarReaisCompacto(e.gastos.total),
      complemento: `em ${e.gastos.ano}`,
      media: textoMedia(casa, formatarReaisCompacto(e.gastos.media_casa)),
    });
  }
  if (e.projetos) {
    c.push({
      rotulo: "Projetos como autor principal",
      valor: INTEIRO.format(e.projetos.primeiro_autor),
      complemento: `desde ${e.projetos.desde.slice(0, 4)}`,
      media: textoMedia(
        casa,
        DECIMAL.format(e.projetos.media_casa_primeiro_autor),
      ),
    });
  }
  if (e.governo && e.governo.total > 0) {
    c.push({
      rotulo: "Votou como o Governo orientou",
      valor: `${e.governo.iguais} de ${e.governo.total}`,
      media:
        e.governo.media_percentual !== null
          ? textoMedia(
              casa,
              `${mediaEmContagem(e.governo.media_percentual, e.governo.total)} de ${e.governo.total}`,
            )
          : undefined,
    });
  }
  const { principal, outros } = escolherNumeros(c);
  return {
    nome: e.nome,
    contexto: juntarContexto([e.cargo, e.partido, e.uf]),
    foto: e.foto,
    principal,
    outros,
    frase: principal ? null : `${e.cargo}${e.uf ? ` por ${e.uf}` : ""}.`,
    fonte: e.fonte,
  };
}

type EntradaLocal = {
  nome: string;
  /** "camara" = vereador; "assembleia" = deputado estadual ou distrital. */
  casa: "camara" | "assembleia";
  cargo: string;
  partido: string | null;
  uf: string | null;
  foto: string | null;
  fonte: string;
  presenca?: {
    sessoes: number;
    presencas: number;
    media_casa: number | null;
  } | null;
  gastos?: {
    ano: number;
    total: number;
    media_casa: number | null;
    media_parcial?: boolean;
    media_descricao?: string | null;
  } | null;
  projetos: number;
  proposicoes: number;
  subsidio?: number | null;
};

export function montarLocal(e: EntradaLocal): DadosCartao {
  const casa = e.casa === "camara" ? "Média da Câmara" : "Média da Assembleia";
  const c: NumeroCartao[] = [];
  const p = e.presenca;
  if (p && p.sessoes > 0) {
    c.push({
      rotulo: "Presença nas sessões",
      valor: INTEIRO.format(p.presencas),
      complemento: `de ${INTEIRO.format(p.sessoes)} sessões, ano atual e anterior`,
      media:
        p.media_casa !== null
          ? textoMedia(
              casa,
              `${mediaEmContagem(p.media_casa, p.sessoes)} de ${INTEIRO.format(p.sessoes)}`,
            )
          : undefined,
    });
  }
  if (e.gastos) {
    const g = e.gastos;
    c.push({
      rotulo: "Verba do gabinete",
      valor: g.total === 0 ? formatarGastos(0) : formatarReaisCompacto(g.total),
      complemento: `em ${g.ano}`,
      media:
        g.media_casa !== null
          ? textoMedia(casa, formatarReaisCompacto(g.media_casa)) +
            (g.media_parcial && g.media_descricao
              ? ` (${g.media_descricao})`
              : "")
          : undefined,
    });
  }
  // Nenhuma proposição na fonte costuma ser autoria que a câmara não publica: não vira número.
  if (e.proposicoes > 0)
    c.push({
      rotulo: "Projetos como autor ou coautor",
      valor: INTEIRO.format(e.projetos),
      complemento: "ano atual e anterior",
      nota: `${INTEIRO.format(e.proposicoes)} proposições no total`,
    });
  if (e.subsidio != null) {
    c.push({
      rotulo: "Salário bruto por mês",
      valor: formatarReaisCompacto(e.subsidio),
      nota: e.casa === "camara" ? undefined : "Igual para toda a Assembleia",
    });
  }
  const { principal, outros } = escolherNumeros(c);
  return {
    nome: e.nome,
    contexto: juntarContexto([e.cargo, e.partido, e.uf]),
    foto: e.foto,
    principal,
    outros,
    frase: principal ? null : `${e.cargo}${e.uf ? ` em ${e.uf}` : ""}.`,
    fonte: e.fonte,
  };
}

type EntradaEleito = {
  nome: string;
  cargo: string;
  unidade: string | null;
  partido: string | null;
  uf: string | null;
  situacao: string | null;
  anoEleicao: number;
  foto: string | null;
  fonte: string;
  votos?: number | null;
  bens?: { ano: number; total: number } | null;
  receitas?: { ano: number; total: number } | null;
};

/** Eleito sem mandato local: votos e declarações ao TSE, que o perfil mostra sem média da Casa. */
export function montarEleito(e: EntradaEleito): DadosCartao {
  const c: NumeroCartao[] = [];
  if (e.votos != null) {
    c.push({
      rotulo: `Votos recebidos em ${e.anoEleicao}`,
      valor: INTEIRO.format(e.votos),
    });
  }
  if (e.bens) {
    c.push({
      rotulo: `Bens declarados ao TSE em ${e.bens.ano}`,
      valor: formatarReaisCompacto(e.bens.total),
    });
  }
  if (e.receitas) {
    c.push({
      rotulo: `Dinheiro arrecadado na campanha de ${e.receitas.ano}`,
      valor: formatarReaisCompacto(e.receitas.total),
    });
  }
  const { principal, outros } = escolherNumeros(c);
  const onde = e.unidade ? ` (${e.unidade})` : "";
  return {
    nome: e.nome,
    contexto: juntarContexto([e.cargo, e.partido, e.uf]),
    foto: e.foto,
    principal,
    outros,
    frase: principal
      ? null
      : `${e.situacao ? `${e.situacao} em` : "Candidatura em"} ${e.anoEleicao} para ${e.cargo.toLowerCase()}${onde}.`,
    fonte: e.fonte,
  };
}

/** Quebra o nome longo (mais de 14 letras) em duas linhas; nome curto fica numa só. */
export function quebrarNome(nome: string): string[] {
  const partes = nome.trim().split(/\s+/);
  if (partes.length <= 1) return [nome.trim()];
  if (nome.trim().length <= 14) return [nome.trim()];
  const meio = partes.length === 2 ? 1 : Math.ceil(partes.length / 2);
  return [partes.slice(0, meio).join(" "), partes.slice(meio).join(" ")];
}
