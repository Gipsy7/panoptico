import type { NextRequest } from "next/server";

import { deEstado } from "@/components/segundo-turno";
import { getSegundoTurno } from "@/lib/api";
import { formatarData } from "@/lib/formato";
import { COR, cortar, imagemPadrao, moldura, rodapeFonte } from "@/lib/og";

// Imagem de prévia do comparador do 2º turno (?uf=SP). Rota própria porque depende do
// parâmetro da URL, que o opengraph-image não recebe. Sem fotos: o TSE serve WebP, que o
// gerador de imagens não lê; os dois lados ficam iguais, na ordem do número na urna.

export async function GET(request: NextRequest) {
  const uf = request.nextUrl.searchParams.get("uf") ?? "";
  if (!/^[A-Za-z]{2}$/.test(uf)) return imagemPadrao();
  const r = await getSegundoTurno({ uf });
  if (!r.ok || r.dados.disputas.length === 0) return imagemPadrao();
  const d = r.dados;
  const quando = d.data_segundo_turno ? formatarData(d.data_segundo_turno).slice(0, 5) : null;
  const duas = d.disputas.length > 1;

  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: duas ? 24 : 40 }}>
      <div style={{ display: "flex", fontSize: 44, fontWeight: 700 }}>
        {`${d.disputas.every((x) => x.decidida) ? "Resultado do 2º turno" : `2º turno${quando ? ` em ${quando}` : ""}`} · ${cortar(d.localizacao.estado, 24)}`}
      </div>
      {d.disputas.map((disputa) => (
        <div key={disputa.chave} style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", fontSize: 26, color: COR.suave }}>
            {disputa.chave === "presidente" ? "Presidente" : `Governador ${deEstado(disputa.unidade)}`}
          </div>
          <div style={{ display: "flex", gap: 24 }}>
            {[0, 1].map((i) => {
              const c = disputa.candidatos[i];
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    gap: 4,
                    background: COR.cartao,
                    border: `2px solid ${COR.borda}`,
                    borderRadius: 20,
                    padding: duas ? "14px 24px" : "24px 28px",
                  }}
                >
                  <div style={{ display: "flex", fontSize: duas ? 34 : 44, fontWeight: 700 }}>
                    {c ? cortar(c.nome_urna, 26) : "Dados ainda não carregados"}
                  </div>
                  {c && (
                    <div style={{ display: "flex", fontSize: 26, color: COR.suave }}>
                      {[c.numero ? `Número ${c.numero}` : null, c.partido, c.eleito ? "eleito(a)" : null]
                        .filter(Boolean)
                        .join(" · ")}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>,
    null,
    40,
    rodapeFonte("TSE", d.atualizado_em),
  );
}
