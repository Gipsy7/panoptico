import type { NextRequest } from "next/server";

import { RESULTADO } from "@/components/votacao-explicador";
import { getRepresentantes, getVotacao } from "@/lib/api";
import { formatoDe } from "@/lib/cartao-cidade";
import { LIMITE_FOTOS, gruposDoEstado, tituloCartao, totalDosGrupos, ufValida } from "@/lib/cartao-votacao";
import { embutirFoto } from "@/lib/embutir-foto";
import { CASA_CURTA, formatarData } from "@/lib/formato";
import { cortar, imagemPadrao, rodapeFonte } from "@/lib/og";
import { cartaoVotacao } from "@/lib/og-votacao";

// GET /votacao/{casa}/{id}/cartao/{uf}?formato=feed|stories -> image/png.
// Como votaram os deputados (ou senadores) de um estado numa votação nominal. Os votos vêm da
// mesma rota da página da votação; as fotos, da lista de representantes do estado.

const CACHE = "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ casa: string; id: string; uf: string }> },
) {
  const { casa, id, uf: ufBruta } = await params;
  const formato = formatoDe(request.nextUrl.searchParams.get("formato"));
  const padrao = () => {
    const r = imagemPadrao();
    r.headers.set("Cache-Control", "public, max-age=300");
    return r;
  };
  const uf = ufValida(ufBruta);
  if (!uf || (casa !== "camara" && casa !== "senado")) return padrao();

  const r = await getVotacao(casa, id);
  // Votação secreta não tem voto por pessoa: não há o que mostrar.
  if (!r.ok || r.dados.secreta) return padrao();
  const d = r.dados;
  const grupos = gruposDoEstado(d.parlamentares, uf);
  const total = totalDosGrupos(grupos);
  if (total === 0) return padrao();

  const comFotos = total <= LIMITE_FOTOS;
  const fotos = new Map<number, string | null>();
  if (comFotos) {
    const rep = await getRepresentantes({ uf });
    const lista = rep.ok ? (casa === "senado" ? rep.dados.senadores : rep.dados.deputados) : [];
    const url = new Map(lista.map((p) => [p.id, p.foto_url]));
    const ids = grupos.flatMap((g) => g.pessoas.map((p) => p.parlamentar_id));
    const embutidas = await Promise.all(ids.map((i) => embutirFoto(url.get(i))));
    ids.forEach((i, n) => fotos.set(i, embutidas[n]));
  }

  const resposta = await cartaoVotacao({
    formato,
    titulo: tituloCartao(casa, uf),
    proposicao: d.proposicao,
    resultado: d.resultado ? RESULTADO[d.resultado] : null,
    ementa: d.proposicao_ementa ? cortar(d.proposicao_ementa, formato === "stories" ? 200 : 120) : null,
    casa: CASA_CURTA[d.casa],
    data: formatarData(d.data),
    grupos: grupos.map((g) => ({
      ...g,
      pessoas: g.pessoas.map((p) => ({
        parlamentar_id: p.parlamentar_id,
        nome: p.nome,
        foto: fotos.get(p.parlamentar_id) ?? null,
      })),
    })),
    comFotos,
    rodape: rodapeFonte(d.fonte_nome, d.atualizado_em),
    nota: d.casa === "camara" ? "A Câmara só publica quem registrou voto ou presença." : null,
    link: `panoptico.social.br/votacao/${d.casa}/${d.id_externo}`,
  });
  resposta.headers.set("Cache-Control", CACHE);
  return resposta;
}
