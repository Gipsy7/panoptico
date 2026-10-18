import { getContas, getEmendasMunicipio } from "@/lib/api";
import { formatarReais } from "@/lib/formato";
import { COR, cortar, imagemPadrao, moldura, rodapeFonte } from "@/lib/og";

export const alt = "Dinheiro público na cidade, no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({
  params,
}: {
  params: Promise<{ ibge: string }>;
}) {
  const { ibge } = await params;
  const [emendas, contas] = await Promise.all([
    getEmendasMunicipio(ibge),
    getContas(ibge),
  ]);
  if (!emendas.ok && !contas.ok) return imagemPadrao();

  const linhas: { rotulo: string; valor: string }[] = [];
  if (emendas.ok && emendas.dados.total > 0) {
    linhas.push({
      rotulo: `Emendas pagas para a cidade desde ${emendas.dados.desde}`,
      valor: formatarReais(emendas.dados.total, true),
    });
  }
  if (contas.ok && contas.dados.despesa_por_habitante != null) {
    linhas.push({
      rotulo: `Gasto da prefeitura por habitante em ${contas.dados.ano}`,
      valor: formatarReais(contas.dados.despesa_por_habitante, true),
    });
  }
  if (linhas.length === 0) return imagemPadrao();

  const m = emendas.ok ? emendas.dados.municipio : null;
  const usaEmendas = linhas.some((l) => l.rotulo.startsWith("Emendas"));
  const usaContas = linhas.some((l) => l.rotulo.startsWith("Gasto"));
  const datas = [
    usaEmendas && emendas.ok ? emendas.dados.atualizado_em : null,
    usaContas && contas.ok ? contas.dados.atualizado_em : null,
  ]
    .filter((d): d is string => Boolean(d))
    .sort();
  const rodape = rodapeFonte(
    [usaEmendas ? "Transparência" : null, usaContas ? "Tesouro Nacional" : null]
      .filter(Boolean)
      .join(" e "),
    datas.at(-1),
  );

  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", fontSize: 56, fontWeight: 700 }}>
        {m ? cortar(`${m.nome}-${m.uf}`, 36) : "Sua cidade"}
      </div>
      {linhas.map((l) => (
        <div
          key={l.rotulo}
          style={{ display: "flex", flexDirection: "column", gap: 4 }}
        >
          <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>
            {l.rotulo}
          </div>
          <div style={{ display: "flex", fontSize: 76, fontWeight: 700 }}>
            {l.valor}
          </div>
        </div>
      ))}
    </div>,
    null,
    40,
    rodape,
  );
}
