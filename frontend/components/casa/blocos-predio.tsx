import { Bancada } from "@/components/casa/bancada";
import { Cadeiras } from "@/components/casa/cadeiras";
import { getBancadaMunicipio, getBancadasEstado, getComposicaoCongresso } from "@/lib/api";

/**
 * Blocos de servidor que entram no painel do prédio (components/predios-representantes.tsx):
 * a bancada da casa (partidos, só em texto e barra neutra) e, para Senado e Câmara, as cadeiras
 * do Congresso inteiro. Se a rota falhar, o bloco some e o resto do painel continua.
 */
export async function BancadaDoPredio({
  predio,
  uf,
  ibge,
  nomeEstado,
}: {
  predio: "senado" | "camara" | "assembleia" | "camaramun";
  uf: string;
  ibge: string | null;
  nomeEstado: string;
}) {
  if (predio === "camaramun") {
    if (!ibge) return null;
    const r = await getBancadaMunicipio(ibge);
    if (!r.ok) return null;
    const b = r.dados;
    return (
      <Bancada
        titulo="Bancada da câmara da cidade"
        itens={b.itens}
        total={b.total}
        fonte={b.fonte_nome}
        fonteUrl={b.fonte_url}
        atualizadoEm={b.atualizado_em}
      />
    );
  }
  const r = await getBancadasEstado(uf);
  if (!r.ok) return null;
  const b = predio === "senado" ? r.dados.senado_uf : predio === "camara" ? r.dados.camara_uf : r.dados.assembleia;
  const titulo =
    predio === "assembleia"
      ? "Bancada da Assembleia"
      : predio === "senado"
        ? `Senadores de ${nomeEstado} por partido`
        : `Deputados federais de ${nomeEstado} por partido`;
  return <Bancada titulo={titulo} itens={b.itens} total={b.total} fonte={b.fonte_nome} fonteUrl={b.fonte_url} atualizadoEm={b.atualizado_em} />;
}

export async function CadeirasDoPredio({ casa }: { casa: "camara" | "senado" }) {
  const r = await getComposicaoCongresso(casa);
  if (!r.ok) return null;
  const c = r.dados;
  return (
    <Cadeiras
      nome={casa === "camara" ? "Câmara dos Deputados" : "Senado"}
      titulo={casa === "camara" ? "Cadeiras da Câmara, no país todo" : "Cadeiras do Senado, no país todo"}
      hoje={c.hoje}
      depois={c.a_partir_2027}
      fonte={{ nome: c.fonte_nome, url: c.fonte_url, atualizadoEm: c.atualizado_em }}
      fonteDepois={
        c.fonte_2027_nome ? { nome: c.fonte_2027_nome, url: c.fonte_2027_url ?? undefined, atualizadoEm: c.atualizado_2027_em } : null
      }
    />
  );
}
