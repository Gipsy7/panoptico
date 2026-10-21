import type { Metadata } from "next";
import Link from "next/link";

import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { TabelaRolavel } from "@/components/ui/tabela-rolavel";
import { AvisoErro } from "@/components/aviso-erro";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import { CampoSelect, type FiltroAtivo, PilulasAtivas } from "@/components/ui/campos-filtro";
import { CamposOrdenacao } from "@/components/ui/campos-filtro-cliente";
import { PainelFiltros } from "@/components/ui/painel-filtros";
import { Resumo2x2 } from "@/components/ui/resumo-2x2";
import { type PartidoNaLista, getPartidos } from "@/lib/api";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

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
    <div className="pagina-secoes" data-largura="larga">
      <CabecalhoPagina
        sobretitulo="Partidos"
        titulo="Dinheiro dos partidos"
        subtitulo="Valores que os próprios partidos declararam ao Tribunal Superior Eleitoral (TSE) na prestação de contas anual: de onde veio o dinheiro e para onde foi. Toque no título de uma coluna para ordenar."
      />
      <Revelacao fallback={<EsqueletoSecao rotulo="Carregando as contas dos partidos…" secoes={2} />}>
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

  const soma = (campo: keyof Omit<PartidoNaLista, "sigla">) => dados.partidos.reduce((t, p) => t + p[campo], 0);
  const gastoMedio = dados.partidos.length ? soma("gasto") / dados.partidos.length : 0;
  const anoPadrao = Math.max(...dados.anos_disponiveis);
  const nomeColuna = COLUNAS.find((c) => c.id === coluna)!.rotulo;
  const ativos: FiltroAtivo[] = [
    ...(dados.ano !== anoPadrao ? [{ rotulo: `Contas de ${dados.ano}`, href: href(anoPadrao, coluna, sentido) }] : []),
    ...(coluna !== "sigla" || sentido !== "asc"
      ? [
          {
            rotulo: `Ordem: ${nomeColuna.toLowerCase()} (${
              coluna === "sigla" ? "de Z a A" : sentido === "desc" ? "maior primeiro" : "menor primeiro"
            })`,
            href: href(dados.ano, "sigla", "asc"),
          },
        ]
      : []),
  ];

  return (
    <>
      <Resumo2x2
        titulo={`Resumo das contas dos partidos em ${dados.ano}`}
        itens={[
          { rotulo: `Partidos com contas em ${dados.ano}`, valor: dados.partidos.length.toLocaleString("pt-BR") },
          { rotulo: "Recebido do Fundo Partidário", valor: formatarReaisCompacto(soma("cota_fundo_partidario")) },
          { rotulo: "Recebido do fundo eleitoral", valor: formatarReaisCompacto(soma("cota_fefc")) },
          {
            rotulo: "Gasto médio por partido",
            valor: formatarReaisCompacto(gastoMedio),
            apoio: `Total: ${formatarReaisCompacto(soma("gasto"))}`,
          },
        ]}
      />
      <section aria-label="Filtros da tabela" className="flex flex-col gap-[var(--esp-4)]">
        <PainelFiltros
          key={`${dados.ano}-${coluna}-${sentido}`}
          action="/partidos"
          ativos={ativos.length}
          limparHref="/partidos"
          padroes={{ ano: String(anoPadrao), ordenar: "sigla" }}
          titulo="Ano e ordem da tabela"
        >
          <CampoSelect
            rotulo="Contas do ano"
            name="ano"
            defaultValue={String(dados.ano)}
            opcoes={dados.anos_disponiveis.map((a) => ({ valor: String(a), rotulo: a === anoPadrao ? `${a} (mais recente)` : String(a) }))}
          />
          <CamposOrdenacao
            criterios={COLUNAS.map((c) => ({ valor: c.id, rotulo: c.rotulo }))}
            ordenar={coluna}
            ordem={sentido}
            textuais={["sigla"]}
          />
        </PainelFiltros>
        <PilulasAtivas itens={ativos} limparHref="/partidos" />
      </section>

      <section aria-labelledby="partidos-titulo" className="revelar flex flex-col gap-3">
        <h2 id="partidos-titulo" className="text-xl">
          {linhas.length} partidos em {dados.ano}
        </h2>
        <TabelaRolavel larguraMinima="44rem" primeiraColunaFixa>
          <table className="w-full border-collapse text-sm">
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
                      <Link href={href(dados.ano, c.id, proximo)} scroll={false} className="alvo-link underline-offset-4 hover:underline">
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
                  <th scope="row" className="py-3 pr-3 text-left font-medium">
                    <Link href={`/partidos/${encodeURIComponent(p.sigla)}?ano=${dados.ano}`} className="underline underline-offset-4">
                      {p.sigla}
                    </Link>
                  </th>
                  {COLUNAS.slice(1).map((c) => (
                    <td key={c.id} className="py-3 pr-3 text-right tabular-nums">
                      {formatarReais(p[c.id as keyof Omit<PartidoNaLista, "sigla">], true)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </TabelaRolavel>
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
