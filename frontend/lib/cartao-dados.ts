import {
  getEleito,
  getGastos,
  getParlamentar,
  getPresenca,
  getProjetos,
  getVereador,
  getVotos,
  urlFotoDe,
  urlFotoTse,
} from "@/lib/api";
import {
  type DadosCartao,
  montarEleito,
  montarFederal,
  montarLocal,
} from "@/lib/cartao";
import { NOME_CASA } from "@/lib/formato";
import { rodapeFonte } from "@/lib/og";

/** Busca os dados na API (os mesmos dos cartões do perfil) e monta o cartão. Null = não achou. */
function maisRecente(datas: (string | null | undefined)[]): string | null {
  const ok = datas.filter((d): d is string => !!d);
  return ok.length ? ok.reduce((a, b) => (a > b ? a : b)) : null;
}

export async function dadosFederal(id: string): Promise<DadosCartao | null> {
  const [parlamentar, presenca, gastos, projetos, votos] = await Promise.all([
    getParlamentar(id),
    getPresenca(id),
    getGastos(id),
    getProjetos(id),
    getVotos(id, {}),
  ]);
  if (!parlamentar.ok) return null;
  const p = parlamentar.dados;
  const gov =
    votos.ok && votos.dados.governo && votos.dados.governo.total > 0
      ? votos.dados.governo
      : null;
  const usados = [
    presenca.ok && presenca.dados.total_votacoes > 0 ? presenca.dados : null,
    gastos.ok ? gastos.dados : null,
    projetos.ok ? projetos.dados : null,
    gov && votos.ok ? votos.dados : null,
  ].filter((d) => d !== null);
  return montarFederal({
    nome: p.nome_parlamentar,
    casa: p.casa,
    cargo: p.casa === "camara" ? "Deputado federal" : "Senador",
    partido: p.partido,
    uf: p.uf,
    foto: p.foto_url,
    fonte: rodapeFonte(
      NOME_CASA[p.casa],
      maisRecente(usados.map((d) => d.atualizado_em)) ?? p.atualizado_em,
    ),
    presenca: presenca.ok ? presenca.dados : null,
    gastos: gastos.ok ? gastos.dados : null,
    projetos: projetos.ok ? projetos.dados : null,
    governo:
      gov && votos.ok
        ? {
            iguais: gov.iguais,
            total: gov.total,
            media_percentual: votos.dados.media_governo,
          }
        : null,
  });
}

export async function dadosLocal(id: string): Promise<DadosCartao | null> {
  const r = await getVereador(id);
  if (!r.ok) return null;
  const v = r.dados;
  const camara = v.casa === "camara";
  return montarLocal({
    nome: v.nome,
    casa: v.casa,
    cargo: camara
      ? "Vereador"
      : v.uf === "DF"
        ? "Deputado distrital"
        : "Deputado estadual",
    partido: v.partido,
    uf: v.uf,
    municipio: camara ? (v.municipio_nome ?? null) : null,
    foto:
      v.foto_tse && v.candidatura_id
        ? urlFotoTse(v.candidatura_id)
        : v.foto_url,
    fonte: rodapeFonte(
      v.fonte_nome,
      maisRecente([v.atualizado_em, v.gastos?.atualizado_em]),
    ),
    presenca: v.presenca,
    gastos: v.gastos,
    projetos: v.projetos,
    proposicoes: v.proposicoes,
    subsidio: v.subsidio?.valor ?? null,
  });
}

export async function dadosEleito(id: string): Promise<DadosCartao | null> {
  const r = await getEleito(id);
  if (!r.ok) return null;
  const e = r.dados;
  // Quem já tem mandato na Assembleia ou na Câmara Municipal ganha o cartão do mandato (com média).
  if (e.mandato_local) {
    const local = await dadosLocal(String(e.mandato_local.id));
    if (local) return local;
  }
  return montarEleito({
    nome: e.nome_urna,
    cargo: e.cargo,
    unidade: e.unidade,
    partido: e.partido,
    uf: e.uf,
    situacao: e.situacao,
    anoEleicao: e.ano_eleicao,
    foto: e.foto ? urlFotoDe(e) : null,
    fonte: rodapeFonte("TSE", e.atualizado_em),
    votos: e.votos,
    bens: e.bens ? { ano: e.bens.candidatura.ano, total: e.bens.total } : null,
    receitas: e.campanha
      ? { ano: e.campanha.candidatura.ano, total: e.campanha.receitas_total }
      : null,
  });
}
