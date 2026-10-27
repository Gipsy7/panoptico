import { getProjetoFederal } from "@/lib/api";
import { CASA_CURTA, NOME_CASA, formatarData } from "@/lib/formato";
import { COR, cortar, imagemPadrao, moldura, rodapeFonte } from "@/lib/og";
import { placarDaVotacao } from "@/lib/projetos";

export const alt = "Projeto no Congresso e seu último placar, no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

const INTEIRO = new Intl.NumberFormat("pt-BR");

export default async function Image({ params }: { params: Promise<{ casa: string; id: string }> }) {
  const { casa, id } = await params;
  const r = await getProjetoFederal(casa, id);
  if (!r.ok) return imagemPadrao();
  const d = r.dados;
  const ultima = d.votacoes.itens[0];
  const p = ultima ? placarDaVotacao(ultima) : null;

  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>{`Projeto no Congresso · ${NOME_CASA[d.casa]}`}</div>
      <div style={{ display: "flex", fontSize: 64, fontWeight: 700 }}>{cortar(d.rotulo, 30)}</div>
      {d.ementa && <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>{cortar(d.ementa, 170)}</div>}
      {p && ultima ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", fontSize: 26, color: COR.suave }}>
            {`Última votação nominal · ${formatarData(ultima.data)}`}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 18, fontSize: 72, fontWeight: 700 }}>
            {INTEIRO.format(p.sim)}
            <span style={{ fontSize: 32, color: COR.suave }}>Sim</span>
            <span style={{ fontSize: 40, color: COR.suave }}>×</span>
            {INTEIRO.format(p.nao)}
            <span style={{ fontSize: 32, color: COR.suave }}>Não</span>
          </div>
          {p.sim + p.nao > 0 && (
            <div style={{ display: "flex", height: 16, width: "100%", gap: 2 }}>
              <div style={{ display: "flex", flexGrow: p.sim, background: COR.primaria }} />
              <div style={{ display: "flex", flexGrow: p.nao, background: COR.borda }} />
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: "flex", fontSize: 36, color: COR.suave }}>Sem votação nominal no Plenário até agora</div>
      )}
    </div>,
    null,
    40,
    rodapeFonte(`Dados Abertos ${d.casa === "camara" ? "da" : "do"} ${CASA_CURTA[d.casa]}`, d.ficha.atualizado_em),
  );
}
