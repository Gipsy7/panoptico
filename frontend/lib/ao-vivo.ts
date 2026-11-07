/** O Plenário agora (selo do cabeçalho e gaveta): tipos da rota /ao-vivo e textos de data e hora. */

export type SituacaoCasa = "agora" | "proxima" | "sem";

export type CasaAoVivo = {
  casa: "camara" | "senado";
  situacao: SituacaoCasa;
  titulo: string | null;
  /** "2026-11-10T14:06", horário de Brasília. */
  inicio: string | null;
  itens: { rotulo: string; descricao: string }[];
  total_itens: number;
  url_video: string | null;
  rotulo_video: string;
  proxima: { inicio: string; titulo: string } | null;
  /** A fonte não respondeu e não havia resposta anterior. */
  indisponivel: boolean;
  conferido_em: string | null;
};

export type AoVivo = {
  conferido_em: string | null;
  fonte_nome: string;
  fonte_url: string;
  casas: CasaAoVivo[];
};

export const NOME_CASA: Record<CasaAoVivo["casa"], string> = { camara: "Câmara", senado: "Senado" };
export const NOME_PLENARIO: Record<CasaAoVivo["casa"], string> = {
  camara: "Plenário da Câmara",
  senado: "Plenário do Senado",
};

const DIAS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"];

function partes(local: string): { dia: string; mes: string; ano: string; h: string; m: string } | null {
  const r = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(local);
  return r ? { ano: r[1], mes: r[2], dia: r[3], h: r[4], m: r[5] } : null;
}

/** "2026-11-10T14:06" -> "14h06"; hora cheia sai "14h". */
export function horaLocal(local: string): string {
  const p = partes(local);
  if (!p) return "";
  return p.m === "00" ? `${Number(p.h)}h` : `${Number(p.h)}h${p.m}`;
}

/** "2026-11-10T14:06" -> "10/11". */
export function diaCurto(local: string): string {
  const p = partes(local);
  return p ? `${p.dia}/${p.mes}` : "";
}

/** "2026-11-10T14:06" -> "terça, 10/11, às 14h06". */
export function diaEHora(local: string): string {
  const p = partes(local);
  if (!p) return "";
  const semana = DIAS[new Date(Date.UTC(Number(p.ano), Number(p.mes) - 1, Number(p.dia))).getUTCDay()];
  return `${semana}, ${p.dia}/${p.mes}, às ${horaLocal(local)}`;
}

/** Instante ISO (UTC) -> "10/11/2026, às 15h42", no horário de Brasília. */
export function conferidoEm(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const fmt = (o: Intl.DateTimeFormatOptions) => d.toLocaleString("pt-BR", { timeZone: "America/Sao_Paulo", ...o });
  const h = Number(fmt({ hour: "2-digit", hour12: false }).slice(0, 2));
  const m = fmt({ minute: "2-digit" }).padStart(2, "0");
  return `${fmt({ day: "2-digit", month: "2-digit", year: "numeric" })}, às ${m === "00" ? `${h}h` : `${h}h${m}`}`;
}

export type Selo = { tipo: "agora" | "proxima"; rotulo: string; leitor: string };

/** Texto do selo: "Ao vivo" quando há sessão; senão a data da próxima; nada se não houver o que dizer. */
export function seloDe(dados: AoVivo | null): Selo | null {
  if (!dados) return null;
  const agora = dados.casas.filter((c) => c.situacao === "agora");
  if (agora.length) {
    const nomes = agora.map((c) => NOME_CASA[c.casa]).join(" e ");
    return { tipo: "agora", rotulo: "Ao vivo", leitor: `Ao vivo: sessão no Plenário (${nomes})` };
  }
  const proximas = dados.casas
    .map((c) => c.proxima?.inicio)
    .filter((i): i is string => !!i)
    .sort();
  if (!proximas.length) return null;
  const dia = diaCurto(proximas[0]);
  return { tipo: "proxima", rotulo: `Próx. ${dia}`, leitor: `Sem sessão no Plenário agora; próxima em ${dia}` };
}
