import type { NextRequest } from "next/server";

import { type ParlamentarNaLista, type ParlamentarResumo, getComparacao, getComparacaoN } from "@/lib/api";
import { CASA_CURTA, formatarReais } from "@/lib/formato";
import { COR, imagemPadrao, moldura } from "@/lib/og";

// Imagem de pré-visualização do comparador. É uma rota própria (e não opengraph-image)
// porque depende dos parâmetros da URL, que o opengraph-image não recebe.
// Formas aceitas: ?ids=1,2,3,4 (2 a 4 pessoas) e ?a=&b= (links antigos, imagem inalterada).

export async function GET(request: NextRequest) {
  const idsParam = request.nextUrl.searchParams.get("ids");
  if (idsParam) {
    const ids = idsParam.split(",").map((x) => x.trim());
    const valido = ids.length >= 2 && ids.length <= 4 && ids.every((x) => /^\d+$/.test(x));
    const r = valido ? await getComparacaoN(ids) : null;
    return r?.ok ? imagemN(r.dados.pessoas, r.dados.numeros) : imagemPadrao();
  }

  const a = request.nextUrl.searchParams.get("a");
  const b = request.nextUrl.searchParams.get("b");
  const resultado = a && b ? await getComparacao(a, b) : null;

  if (!resultado?.ok) return imagemPadrao();

  const d = resultado.dados;
  const destaque = d.convergencia?.votacoes_em_comum
    ? `Votaram igual em ${d.convergencia.iguais} de ${d.convergencia.votacoes_em_comum} votações em ${d.ano}`
    : "Gastos, presença e projetos lado a lado";

  return moldura(
    <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center" }}>
      <Lado p={d.a} />
      <div style={{ fontSize: 56, color: COR.suave }}>×</div>
      <Lado p={d.b} />
    </div>,
    destaque,
  );
}

function imagemN(pessoas: ParlamentarResumo[], numeros: (ParlamentarNaLista | null)[]) {
  const n = pessoas.length;
  // Largura útil: 1200 - 2*64 = 1072; com 4 colunas sobram ~255 px cada.
  const largura = Math.floor(1072 / n) - 16;
  const fonteNome = n === 2 ? 36 : n === 3 ? 34 : 28;
  const fonteMenor = n === 4 ? 22 : 26;
  const foto = n === 4 ? { w: 105, h: 140 } : { w: 120, h: 160 };
  return moldura(
    <div style={{ display: "flex", justifyContent: "space-around", alignItems: "flex-start" }}>
      {pessoas.map((p, i) => {
        const num = numeros[i];
        const nome = p.nome_parlamentar.length > 30 ? `${p.nome_parlamentar.slice(0, 29)}…` : p.nome_parlamentar;
        return (
          <div
            key={p.id}
            style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, width: largura }}
          >
            {p.foto_url && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={p.foto_url} alt="" width={foto.w} height={foto.h} style={{ borderRadius: 20, objectFit: "cover" }} />
            )}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                width: "100%",
                fontSize: fonteNome,
                fontWeight: 700,
                textAlign: "center",
                lineHeight: 1.1,
                height: Math.round(fonteNome * 2.2),
                overflow: "hidden",
              }}
            >
              {nome}
            </div>
            <div style={{ display: "flex", fontSize: fonteMenor, color: COR.suave }}>
              {[CASA_CURTA[p.casa], [p.partido, p.uf].filter(Boolean).join("-")].filter(Boolean).join(" · ")}
            </div>
            {num && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", fontSize: fonteMenor }}>
                <div style={{ display: "flex" }}>{`Gastos ${formatarReais(num.gastos, true)}`}</div>
                {num.presenca != null && <div style={{ display: "flex" }}>{`Presença ${Math.round(num.presenca)}%`}</div>}
              </div>
            )}
          </div>
        );
      })}
    </div>,
    `Comparação de ${n} parlamentares: gastos, presença e projetos`,
    34,
  );
}

function Lado({ p }: { p: ParlamentarResumo }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, width: 420 }}>
      {p.foto_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={p.foto_url} alt="" width={150} height={200} style={{ borderRadius: 20, objectFit: "cover" }} />
      )}
      <div style={{ fontSize: 40, fontWeight: 700, textAlign: "center" }}>{p.nome_parlamentar}</div>
      <div style={{ fontSize: 28, color: COR.suave }}>
        {[CASA_CURTA[p.casa], p.partido, p.uf].filter(Boolean).join(" · ")}
      </div>
    </div>
  );
}

