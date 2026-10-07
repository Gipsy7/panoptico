import { ImageResponse } from "next/og";

import { getGastos, getParlamentar, getPresenca, getProjetos } from "@/lib/api";
import { NOME_CASA, formatarReais } from "@/lib/formato";
import { COR_MARCA, COR_PAPEL, COR_SUAVE, COR_TINTA, LINHAS_MARCA } from "@/lib/marca-svg";

export const alt = "Resumo do parlamentar no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Tokens da paleta (globals.css) em hex, porque o gerador de imagem não lê CSS.
const COR = {
  fundo: COR_PAPEL,
  texto: COR_TINTA,
  suave: COR_SUAVE,
  primaria: COR_MARCA,
  cartao: "#f8f6f0",
  borda: "#d9d3c7",
};

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [parlamentar, gastos, presenca, projetos] = await Promise.all([
    getParlamentar(id),
    getGastos(id),
    getPresenca(id),
    getProjetos(id),
  ]);

  if (!parlamentar.ok) {
    return new ImageResponse(
      <div
        style={{
          ...centro,
          background: COR.fundo,
          color: COR.primaria,
          fontSize: 72,
          fontWeight: 700,
        }}
      >
        Panóptico
      </div>,
      size,
    );
  }

  const p = parlamentar.dados;
  const numeros: { rotulo: string; valor: string }[] = [];
  if (gastos.ok) {
    numeros.push({
      rotulo: `Gastos do gabinete em ${gastos.dados.ano}`,
      valor: formatarReais(gastos.dados.total, true),
    });
  }
  if (presenca.ok && presenca.dados.percentual !== null) {
    numeros.push({
      rotulo: `Votou em ${presenca.dados.ano}`,
      valor: `${presenca.dados.votou} de ${presenca.dados.total_votacoes} votações`,
    });
  }
  if (projetos.ok) {
    numeros.push({
      rotulo: "Projetos como autor principal",
      valor: String(projetos.dados.primeiro_autor),
    });
  }

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
      <div style={{ display: "flex", gap: 48, alignItems: "center" }}>
        {p.foto_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={p.foto_url}
            alt=""
            width={180}
            height={240}
            style={{ borderRadius: 24, objectFit: "cover" }}
          />
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ fontSize: 64, fontWeight: 700 }}>{p.nome_parlamentar}</div>
          <div style={{ fontSize: 34, color: COR.suave }}>
            {[NOME_CASA[p.casa], p.partido, p.uf].filter(Boolean).join(" · ")}
          </div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24 }}>
        {numeros.map((n) => (
          <div
            key={n.rotulo}
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: 8,
              background: COR.cartao,
              border: `2px solid ${COR.borda}`,
              borderRadius: 24,
              padding: 28,
            }}
          >
            <div style={{ fontSize: 24, color: COR.suave }}>{n.rotulo}</div>
            <div style={{ fontSize: 40, fontWeight: 700 }}>{n.valor}</div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <svg width={40} height={40} viewBox="0 0 64 64" fill="none" stroke={COR.primaria} strokeLinecap="round">
            {LINHAS_MARCA.map((l, i) => (
              <line key={i} {...l} strokeWidth={3.6} />
            ))}
            <circle cx={32} cy={32} r={7.5} strokeWidth={3} />
          </svg>
          <div style={{ display: "flex", alignItems: "baseline", color: COR.texto, fontWeight: 700 }}>
            Panóptico<span style={{ color: COR.primaria, fontWeight: 500 }}>.social</span>
          </div>
        </div>
        <div style={{ color: COR.suave }}>Quem te representa, às claras · dados oficiais</div>
      </div>
    </div>,
    size,
  );
}

const centro = {
  width: "100%",
  height: "100%",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
} as const;
