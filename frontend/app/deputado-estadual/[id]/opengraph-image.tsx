import { getVereador, urlFotoTse } from "@/lib/api";
import { formatarReais } from "@/lib/formato";
import { type NumeroOg, cartaoPessoa, imagemPadrao, rodapeFonte } from "@/lib/og";

export const alt = "Resumo do mandato no Panóptico";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const r = await getVereador(id);
  if (!r.ok) return imagemPadrao();
  const v = r.dados;
  const camara = v.casa === "camara";
  const cargo = camara ? "Vereador" : v.uf === "DF" ? "Deputado distrital" : "Deputado estadual";

  const numeros: NumeroOg[] = [];
  if (v.gastos) {
    numeros.push({
      rotulo: `Gastos do gabinete em ${v.gastos.ano}`,
      valor: formatarReais(v.gastos.total, true),
    });
  }
  numeros.push({ rotulo: "Projetos (ano atual e anterior)", valor: String(v.projetos) });
  if (v.presenca) {
    numeros.push({ rotulo: "Presença nas sessões", valor: `${v.presenca.presencas} de ${v.presenca.sessoes}` });
  }

  return cartaoPessoa({
    foto: v.foto_tse && v.candidatura_id ? urlFotoTse(v.candidatura_id) : v.foto_url,
    nome: v.nome,
    contexto: [cargo, v.partido, v.uf].filter(Boolean).join(" · "),
    numeros: numeros.slice(0, 3),
    rodape: rodapeFonte(v.fonte_nome, v.atualizado_em),
  });
}
