import type { Metadata } from "next";
import { Suspense } from "react";

import { CepForm } from "@/components/cep-form";
import { type DadosDaHistoria, HistoriaPanoptico, type PessoaDaHistoria } from "@/components/historia-panoptico";
import { getComparacaoN, getRepresentantes } from "@/lib/api";
import { CASA_CURTA, formatarGastos, formatarReais } from "@/lib/formato";

export const metadata: Metadata = {
  title: "O que é o Panóptico",
  description:
    "De onde vem o nome: a prisão imaginada por Bentham, o que Foucault viu nela e como o Panóptico.social inverte a ideia.",
};

// Os exemplos dentro da torre são os senadores do mesmo estado da página inicial (sempre há 3 em
// exercício): critério neutro e fixo, sem escolha por desempenho.
const UF_DO_EXEMPLO = "SC";

const VAZIO: DadosDaHistoria = { pessoas: [], indisponivel: false, ano: null, fonte: null };

export default function OPanopticoPage() {
  return (
    <article data-largura="larga" className="flex flex-col gap-4">
      <header className="flex flex-col gap-2 lg:pt-6">
        <p className="sobretitulo">A ideia</p>
        <h1 className="titulo-pagina">O que é o Panóptico</h1>
        <p className="text-muted-foreground">O nome vem de um projeto de prisão do século 18.</p>
      </header>

      <Suspense fallback={<HistoriaPanoptico dados={VAZIO} cep={<CepForm />} />}>
        <Historia />
      </Suspense>
    </article>
  );
}

async function Historia() {
  const dados = await carregar();
  return <HistoriaPanoptico dados={dados} cep={<CepForm />} />;
}

async function carregar(): Promise<DadosDaHistoria> {
  const representantes = await getRepresentantes({ uf: UF_DO_EXEMPLO });
  if (!representantes.ok) return { ...VAZIO, indisponivel: true };
  const escolhidos = representantes.dados.senadores.slice(0, 3);
  if (escolhidos.length < 2) return { ...VAZIO, indisponivel: true };
  const comparacao = await getComparacaoN(escolhidos.map((p) => p.id));
  if (!comparacao.ok) return { ...VAZIO, indisponivel: true };
  const { pessoas, numeros, medias, ano, atualizado_em } = comparacao.dados;
  const lista: PessoaDaHistoria[] = pessoas.map((p, i) => {
    const media = medias[p.casa]?.gastos ?? null;
    return {
      ...p,
      casaNome: CASA_CURTA[p.casa],
      gastos: numeros[i] ? formatarGastos(numeros[i].gastos, true) : "sem dado",
      media: media === null ? null : formatarReais(media, true),
    };
  });
  return {
    pessoas: lista,
    indisponivel: false,
    ano,
    fonte: {
      nome: "Cota para o Exercício da Atividade Parlamentar dos Senadores (CEAPS)",
      url: "https://www25.senado.leg.br/web/transparencia/sen/",
      atualizadoEm: atualizado_em,
    },
  };
}
