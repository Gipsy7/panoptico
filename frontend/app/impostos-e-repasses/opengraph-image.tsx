import { ANO_PADRAO, reais } from "@/components/dinheiro-federal/formatos";
import { getDinheiroFederal } from "@/lib/api";
import { COR, imagemPadrao, moldura, rodapeFonte } from "@/lib/og";

export const alt = "Impostos e repasses no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

// Cartão único para /impostos-e-repasses e suas páginas de estado e cidade (o Next não aceita
// imagem própria dentro de rota com [[...lugar]]).
export default async function Image() {
  const p = await getDinheiroFederal(ANO_PADRAO);
  if (!p.ok) return imagemPadrao();
  const linhas = [
    { rotulo: `A União arrecadou em ${ANO_PADRAO}`, valor: reais(p.dados.brasil.arrecadacao) },
    { rotulo: "e repassou a estados e prefeituras", valor: reais(p.dados.brasil.repasse) },
  ];
  const datas = p.dados.fontes.map((f) => f.atualizado_em).filter((d): d is string => Boolean(d)).sort();
  return moldura(
    <div style={{ display: "flex", flexDirection: "column", gap: 32 }}>
      <div style={{ display: "flex", fontSize: 56, fontWeight: 700 }}>Impostos e repasses</div>
      {linhas.map((l) => (
        <div key={l.rotulo} style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex", fontSize: 28, color: COR.suave }}>{l.rotulo}</div>
          <div style={{ display: "flex", fontSize: 76, fontWeight: 700 }}>{l.valor}</div>
        </div>
      ))}
    </div>,
    null,
    40,
    rodapeFonte("Receita Federal e Tesouro Nacional", datas.at(-1)),
  );
}
