import type { NextRequest } from "next/server";

import {
  type Esfera,
  type PessoaMosaico,
  FORMATOS,
  contagens,
  dataMaisRecente,
  escolherMosaico,
  formatoDe,
  listaDeFontes,
  textoFora,
} from "@/lib/cartao-cidade";
import {
  type Chapa,
  getAssembleia,
  getCamara,
  getDeputadosEstaduais,
  getExecutivo,
  getRepresentantes,
  getVereadores,
  urlFotoDe,
} from "@/lib/api";
import { embutirFoto as embutir } from "@/lib/embutir-foto";
import { formatarData } from "@/lib/formato";
import { imagemPadrao } from "@/lib/og";
import { cartaoCidade } from "@/lib/og-cidade";

// GET /cidade/{ibge}/cartao?formato=feed|stories -> image/png (Feed 1080x1080, Stories 1080x1920).
// Contagens e pessoas vêm das mesmas rotas da página "Quem te representa".

const CACHE = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800";

function fotoChapa(c: Chapa | null | undefined): string | null {
  return c?.titular.foto ? urlFotoDe(c.titular) : null;
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ ibge: string }> }) {
  const { ibge } = await params;
  const formato = formatoDe(request.nextUrl.searchParams.get("formato"));
  const padrao = () => {
    const r = imagemPadrao();
    r.headers.set("Cache-Control", "public, max-age=300");
    return r;
  };
  if (!/^\d{7}$/.test(ibge)) return padrao();

  const local = await getRepresentantes({ municipio: ibge });
  if (!local.ok || !local.dados.localizacao.municipio) return padrao();
  const nomeCidade = local.dados.localizacao.municipio;
  const { deputados, senadores, localizacao } = local.dados;
  const distrito = localizacao.uf === "DF";

  const [executivoR, assembleiaR, estaduaisR, camaraR, vereadoresR] = await Promise.all([
    getExecutivo(localizacao.uf, ibge),
    getAssembleia(localizacao.uf),
    getDeputadosEstaduais(localizacao.uf),
    distrito ? null : getCamara(ibge),
    distrito ? null : getVereadores(ibge),
  ]);
  const executivo = executivoR.ok ? executivoR.dados : null;
  const assembleia = assembleiaR.ok ? assembleiaR.dados : null;
  const estaduais = estaduaisR.ok ? estaduaisR.dados : null;
  const camara = camaraR?.ok ? camaraR.dados : null;
  const vereadores = vereadoresR?.ok ? vereadoresR.dados : null;

  // Mesma regra da página: a casa legislativa (SAPL) primeiro; sem ela, os eleitos pelo TSE.
  const nEstaduais = assembleia?.itens.length ?? estaduais?.itens.length ?? 0;
  const nVereadores = camara?.itens.length ?? vereadores?.itens.length ?? 0;
  const c = contagens({
    presidente: executivo?.presidente ? 1 : null,
    governador: executivo?.governador ? 1 : null,
    prefeito: executivo?.prefeito ? 1 : null,
    nSenadores: senadores.length,
    nFederais: deputados.length,
    nEstaduais,
    nVereadores,
    distrito,
  });
  if (c.total === 0) return padrao();

  const fotoEleito = (id: number, foto?: boolean, fotoDe?: number | null) =>
    foto ? urlFotoDe({ id, foto_de: fotoDe }) : null;
  const pessoas: (PessoaMosaico & { url: string | null })[] = [];
  const add = (chave: string, esfera: Esfera, url: string | null) =>
    pessoas.push({ chave, esfera, foto: url, url });
  if (executivo?.presidente) add("presidente", "presidente", fotoChapa(executivo.presidente));
  if (executivo?.governador) add("governador", "governador", fotoChapa(executivo.governador));
  if (executivo?.prefeito && !distrito) add("prefeito", "prefeito", fotoChapa(executivo.prefeito));
  senadores.forEach((p) => add(`s${p.id}`, "senado", p.foto_url));
  deputados.forEach((p) => add(`f${p.id}`, "federal", p.foto_url));
  if (assembleia) {
    assembleia.itens.forEach((v) =>
      add(`e${v.id}`, "estadual", v.foto_tse && v.candidatura_id ? urlFotoDe({ id: v.candidatura_id }) : v.foto_url),
    );
  } else {
    estaduais?.itens.forEach((e) => add(`e${e.id}`, "estadual", fotoEleito(e.id, e.foto, e.foto_de)));
  }

  const { fotos } = FORMATOS[formato];
  const escolhidos = escolherMosaico(pessoas, fotos, ibge);
  // Só baixa as fotos que vão para o cartão.
  const embutidas = await Promise.all(
    escolhidos.map((p) => embutir(pessoas.find((x) => x.chave === p.chave)?.url ?? null)),
  );
  const mosaico = escolhidos.map((p, i) => ({ chave: p.chave, esfera: p.esfera, foto: embutidas[i] }));

  const fontes = listaDeFontes([
    deputados.length ? "Câmara" : "",
    senadores.length ? "Senado" : "",
    executivo || estaduais || vereadores ? "TSE" : "",
    assembleia || camara ? "casas legislativas" : "",
  ]);
  const data = dataMaisRecente([
    executivo?.atualizado_em,
    local.dados.atualizado_em,
    assembleia?.atualizado_em,
    estaduais?.atualizado_em,
    camara?.atualizado_em,
    vereadores?.atualizado_em,
  ]);

  const resposta = await cartaoCidade({
    formato,
    cidade: nomeCidade,
    uf: localizacao.uf,
    ibge,
    total: c.total,
    contagens: c.itens,
    mosaico,
    fontes,
    atualizadoEm: data ? formatarData(data) : null,
    fora: textoFora(c.fora),
  });
  resposta.headers.set("Cache-Control", CACHE);
  return resposta;
}
