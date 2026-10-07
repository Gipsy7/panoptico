import { ImageResponse } from "next/og";
import type { NextRequest } from "next/server";

import { type ParlamentarResumo, getComparacao } from "@/lib/api";
import { CASA_CURTA } from "@/lib/formato";

// Imagem de pré-visualização do comparador. É uma rota própria (e não opengraph-image)
// porque depende dos parâmetros ?a= e ?b=, que o opengraph-image não recebe.

const TAMANHO = { width: 1200, height: 630 };
const COR = { fundo: "#fbf8f3", texto: "#2f2420", suave: "#6b5d56", primaria: "#62345f" };

export async function GET(request: NextRequest) {
  const a = request.nextUrl.searchParams.get("a");
  const b = request.nextUrl.searchParams.get("b");
  const resultado = a && b ? await getComparacao(a, b) : null;

  if (!resultado?.ok) {
    return new ImageResponse(
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: COR.fundo,
          color: COR.primaria,
          fontSize: 72,
          fontWeight: 700,
        }}
      >
        Panóptico
      </div>,
      TAMANHO,
    );
  }

  const d = resultado.dados;
  const destaque = d.convergencia?.votacoes_em_comum
    ? `Votaram igual em ${d.convergencia.iguais} de ${d.convergencia.votacoes_em_comum} votações em ${d.ano}`
    : "Gastos, presença e projetos lado a lado";

  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: COR.fundo,
        color: COR.texto,
        padding: 64,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-around", alignItems: "center" }}>
        <Lado p={d.a} />
        <div style={{ fontSize: 56, color: COR.suave }}>×</div>
        <Lado p={d.b} />
      </div>
      <div style={{ fontSize: 40, textAlign: "center", display: "flex", justifyContent: "center" }}>
        {destaque}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26 }}>
        <div style={{ color: COR.primaria, fontWeight: 700 }}>Panóptico</div>
        <div style={{ color: COR.suave }}>Quem te representa, às claras · dados oficiais</div>
      </div>
    </div>,
    TAMANHO,
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
