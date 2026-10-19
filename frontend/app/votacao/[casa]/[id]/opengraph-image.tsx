import { RESULTADO, placarPrincipal } from "@/components/votacao-explicador";
import { getVotacao } from "@/lib/api";
import { CASA_CURTA, formatarData } from "@/lib/formato";
import { COR, cortar, imagemPadrao, moldura, rodapeFonte } from "@/lib/og";

export const alt = "Placar de uma votação no Plenário, no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INTEIRO = new Intl.NumberFormat("pt-BR");

export default async function Image({ params }: { params: Promise<{ casa: string; id: string }> }) {
  const { casa, id } = await params;
  const r = await getVotacao(casa, id);
  if (!r.ok) return imagemPadrao();
  const d = r.dados;
  const p = placarPrincipal(d);
  const total = p.sim + p.nao;

  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>
        {`Plenário ${d.casa === "camara" ? "da Câmara" : "do Senado"} · ${formatarData(d.data)}`}
      </div>
      <div style={{ display: "flex", fontSize: 60, fontWeight: 700 }}>
        {cortar(`${d.proposicao ?? "Votação"}${d.resultado ? `: ${RESULTADO[d.resultado].toLowerCase()}` : ""}`, 34)}
      </div>
      {d.proposicao_ementa && (
        <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>{cortar(d.proposicao_ementa, 120)}</div>
      )}
      <div style={{ display: "flex", alignItems: "baseline", gap: 18, fontSize: 84, fontWeight: 700 }}>
        {INTEIRO.format(p.sim)}
        <span style={{ fontSize: 36, color: COR.suave }}>Sim</span>
        <span style={{ fontSize: 48, color: COR.suave }}>×</span>
        {INTEIRO.format(p.nao)}
        <span style={{ fontSize: 36, color: COR.suave }}>Não</span>
      </div>
      {total > 0 && (
        <div style={{ display: "flex", height: 16, width: "100%", gap: 2 }}>
          <div style={{ display: "flex", flexGrow: p.sim, background: COR.primaria }} />
          <div style={{ display: "flex", flexGrow: p.nao, background: COR.borda }} />
        </div>
      )}
    </div>,
    null,
    40,
    rodapeFonte(`Dados Abertos ${d.casa === "camara" ? "da" : "do"} ${CASA_CURTA[d.casa]}`, d.atualizado_em),
  );
}
