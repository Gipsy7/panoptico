import { getGastos, getParlamentar, getPresenca, getProjetos } from "@/lib/api";
import { NOME_CASA, formatarReais } from "@/lib/formato";
import { type NumeroOg, cartaoPessoa, imagemPadrao, rodapeFonte } from "@/lib/og";

export const alt = "Resumo do parlamentar no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const [parlamentar, gastos, presenca, projetos] = await Promise.all([
    getParlamentar(id),
    getGastos(id),
    getPresenca(id),
    getProjetos(id),
  ]);

  if (!parlamentar.ok) return imagemPadrao();

  const p = parlamentar.dados;
  const numeros: NumeroOg[] = [];
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
    numeros.push({ rotulo: "Projetos como autor principal", valor: String(projetos.dados.primeiro_autor) });
  }

  return cartaoPessoa({
    foto: p.foto_url,
    nome: p.nome_parlamentar,
    contexto: [NOME_CASA[p.casa], p.partido, p.uf].filter(Boolean).join(" · "),
    numeros,
    rodape: rodapeFonte(NOME_CASA[p.casa], gastos.ok ? gastos.dados.atualizado_em : p.atualizado_em),
  });
}
