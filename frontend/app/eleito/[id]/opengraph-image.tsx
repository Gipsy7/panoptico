import { getEleito, urlFotoTse } from "@/lib/api";
import { formatarReais } from "@/lib/formato";
import { type NumeroOg, cartaoPessoa, imagemPadrao, rodapeFonte } from "@/lib/og";

export const alt = "Resumo do eleito no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await getEleito(id);
  if (!r.ok) return imagemPadrao();
  const e = r.dados;

  const numeros: NumeroOg[] = [];
  if (e.votos != null) {
    numeros.push({ rotulo: `Votos recebidos em ${e.ano_eleicao}`, valor: e.votos.toLocaleString("pt-BR") });
  }
  if (e.bens) {
    numeros.push({
      rotulo: `Bens declarados ao TSE em ${e.bens.candidatura.ano}`,
      valor: formatarReais(e.bens.total, true),
    });
  }

  return cartaoPessoa({
    foto: e.foto ? urlFotoTse(e.id) : null,
    nome: e.nome_urna,
    contexto: [e.cargo, e.unidade, e.partido].filter(Boolean).join(" · "),
    numeros,
    rodape: rodapeFonte("TSE", e.atualizado_em),
  });
}
