import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import { type PartidoNaLista, getPartidos } from "@/lib/api";
import { formatarReais } from "@/lib/formato";

export const metadata: Metadata = {
  title: "Dinheiro dos partidos",
  description:
    "Quanto cada partido recebeu do Fundo Partidário e do fundo eleitoral, quanto arrecadou, gastou e repassou a candidaturas, segundo a prestação de contas entregue ao TSE.",
};

type Coluna = "sigla" | keyof Omit<PartidoNaLista, "sigla">;

const COLUNAS: { id: Coluna; rotulo: string }[] = [
  { id: "sigla", rotulo: "Partido" },
  { id: "cota_fundo_partidario", rotulo: "Fundo Partidário" },
  { id: "cota_fefc", rotulo: "Fundo eleitoral (FEFC)" },
  { id: "receita_total", rotulo: "Receita total" },
  { id: "gasto", rotulo: "Gasto" },
  { id: "repasse_candidatos", rotulo: "Repassado a candidaturas" },
];

const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);

export default function PartidosPage({ searchParams }: PageProps<"/partidos">) {
  return (
    <div className="flex flex-col gap-6" data-largura="larga">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl tracking-tight">Dinheiro dos partidos</h1>
        <p className="text-muted-foreground">
          Valores que os próprios partidos declararam ao Tribunal Superior Eleitoral (TSE) na
          prestação de contas anual: de onde veio o dinheiro e para onde foi. Toque no título de
          uma coluna para ordenar.
        </p>
      </header>
      <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => (
          <Tabela ano={texto(sp.ano)} ordenar={texto(sp.ordenar)} ordem={texto(sp.ordem)} />
        ))}
      </Revelacao>
    </div>
  );
}

function href(ano: number, ordenar: Coluna, ordem: "asc" | "desc") {
  return `/partidos?ano=${ano}&ordenar=${ordenar}&ordem=${ordem}`;
}

async function Tabela({ ano, ordenar, ordem }: { ano?: string; ordenar?: string; ordem?: string }) {
  const resultado = await getPartidos(ano);
  if (!resultado.ok) {
    return <AvisoErro titulo="Não deu para carregar as contas dos partidos" mensagem={resultado.mensagem} />;
  }
  const dados = resultado.dados;
  const coluna: Coluna = COLUNAS.some((c) => c.id === ordenar) ? (ordenar as Coluna) : "sigla";
  const sentido: "asc" | "desc" = ordem === "asc" || ordem === "desc" ? ordem : coluna === "sigla" ? "asc" : "desc";
  const fator = sentido === "asc" ? 1 : -1;
  const linhas = [...dados.partidos].sort((a, b) =>
    coluna === "sigla" ? fator * a.sigla.localeCompare(b.sigla, "pt-BR") : fator * (a[coluna] - b[coluna]),
  );

  return (
    <>
      <nav aria-label="Ano da prestação de contas" className="flex flex-wrap items-center gap-2 text-sm">
        <span className="text-muted-foreground">Contas de</span>
        {dados.anos_disponiveis.map((a) => (
          <Link
            key={a}
            href={href(a, coluna, sentido)}
            aria-current={a === dados.ano ? "page" : undefined}
            className={a === dados.ano ? "font-semibold underline underline-offset-4" : "underline-offset-4 hover:underline"}
          >
            {a}
          </Link>
        ))}
      </nav>

      <section aria-labelledby="partidos-titulo" className="revelar flex flex-col gap-3">
        <h2 id="partidos-titulo" className="text-xl">
          {linhas.length} partidos em {dados.ano}
        </h2>
        <div className="-mx-4 overflow-x-auto px-4">
          <table className="w-full min-w-[44rem] border-collapse text-sm">
            <caption className="sr-only">
              Contas dos partidos em {dados.ano}, em reais, ordenáveis por coluna
            </caption>
            <thead>
              <tr className="border-b border-border text-left">
                {COLUNAS.map((c) => {
                  const ativa = c.id === coluna;
                  const proximo = ativa ? (sentido === "asc" ? "desc" : "asc") : c.id === "sigla" ? "asc" : "desc";
                  return (
                    <th
                      key={c.id}
                      scope="col"
                      aria-sort={ativa ? (sentido === "asc" ? "ascending" : "descending") : undefined}
                      className={`py-2 pr-3 align-bottom font-medium ${c.id === "sigla" ? "" : "text-right"}`}
                    >
                      <Link href={href(dados.ano, c.id, proximo)} className="underline-offset-4 hover:underline">
                        {c.rotulo}
                        {ativa && <span aria-hidden> {sentido === "asc" ? "↑" : "↓"}</span>}
                      </Link>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {linhas.map((p) => (
                <tr key={p.sigla} className="border-b border-border/70">
                  <th scope="row" className="py-2 pr-3 text-left font-medium">
                    <Link href={`/partidos/${encodeURIComponent(p.sigla)}?ano=${dados.ano}`} className="underline underline-offset-4">
                      {p.sigla}
                    </Link>
                  </th>
                  {COLUNAS.slice(1).map((c) => (
                    <td key={c.id} className="py-2 pr-3 text-right tabular-nums">
                      {formatarReais(p[c.id as keyof Omit<PartidoNaLista, "sigla">], true)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="nota flex flex-col gap-2 text-sm text-muted-foreground">
        <p>
          São valores declarados pelos partidos, somando o diretório nacional, os estaduais e os
          municipais. Os dois fundos são dinheiro público: o Fundo Partidário e o Fundo Especial de
          Financiamento de Campanha (FEFC), cuja cota só é paga em ano de eleição.
        </p>
        <p>
          Para não contar o mesmo dinheiro duas vezes, o <strong>gasto</strong> não inclui o que um
          diretório mandou para outro nem o que foi repassado a candidaturas: o repasse aparece
          numa coluna própria. Já a <strong>receita total</strong> inclui o que o diretório recebeu
          de outros diretórios do mesmo partido e de candidaturas; os detalhes estão na página de
          cada partido.
        </p>
      </div>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </>
  );
}
