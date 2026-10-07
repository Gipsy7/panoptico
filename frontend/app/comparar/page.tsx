import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { BuscaParlamentar } from "@/components/busca-parlamentar";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { Foto } from "@/components/parlamentar-card";
import {
  type Comparacao,
  type ParlamentarNaLista,
  type ParlamentarResumo,
  getComparacao,
  getParlamentar,
} from "@/lib/api";
import { CASA_CURTA, NOME_CASA, formatarData, formatarReais } from "@/lib/formato";

type Busca = { a?: string; b?: string; ano?: string };

const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);

export async function generateMetadata({
  searchParams,
}: PageProps<"/comparar">): Promise<Metadata> {
  const sp = await searchParams;
  const a = texto(sp.a);
  const b = texto(sp.b);
  if (!a || !b) return { title: "Comparar parlamentares" };
  const resultado = await getComparacao(a, b);
  if (!resultado.ok) return { title: "Comparar parlamentares" };
  const { a: pa, b: pb } = resultado.dados;
  const titulo = `${pa.nome_parlamentar} × ${pb.nome_parlamentar}`;
  return {
    title: titulo,
    description: `Gastos, presença, projetos e votos de ${pa.nome_parlamentar} e ${pb.nome_parlamentar}, lado a lado, com dados oficiais.`,
    openGraph: {
      title: titulo,
      images: [{ url: `/comparar/imagem?a=${a}&b=${b}`, width: 1200, height: 630 }],
    },
  };
}

export default function CompararPage({ searchParams }: PageProps<"/comparar">) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-bold tracking-tight">Comparar parlamentares</h1>
        <p className="text-muted-foreground">
          Dois parlamentares lado a lado: números, temas dos projetos e, se forem da mesma Casa,
          em quantas votações votaram igual.
        </p>
      </header>
      <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => (
          <Conteudo a={texto(sp.a)} b={texto(sp.b)} ano={texto(sp.ano)} />
        ))}
      </Revelacao>
    </div>
  );
}

async function Conteudo({ a, b, ano }: Busca) {
  if (!a) {
    return <BuscaParlamentar hrefBase="/comparar?a=" rotulo="Escolha o primeiro parlamentar" />;
  }
  if (!b) {
    const primeiro = await getParlamentar(a);
    if (!primeiro.ok) return <AvisoErro titulo="Parlamentar não encontrado" mensagem={primeiro.mensagem} />;
    return (
      <div className="flex flex-col gap-4">
        <Pessoa p={primeiro.dados} />
        <BuscaParlamentar
          hrefBase={`/comparar?a=${a}&b=`}
          rotulo="Com quem você quer comparar?"
          ignorarId={primeiro.dados.id}
        />
      </div>
    );
  }
  const resultado = await getComparacao(a, b, ano);
  if (!resultado.ok) {
    return <AvisoErro titulo="Não deu para comparar" mensagem={resultado.mensagem} />;
  }
  return <Resultado dados={resultado.dados} />;
}

function Pessoa({ p }: { p: ParlamentarResumo }) {
  return (
    <Link
      href={`/parlamentar/${p.id}`}
      className="flex min-w-0 flex-col items-center gap-2 rounded-xl bg-card p-3 text-center border border-border/80 hover:bg-accent"
    >
      <Foto parlamentar={p} largura={64} />
      <span className="font-semibold leading-tight">{p.nome_parlamentar}</span>
      <span className="text-xs text-muted-foreground">
        {CASA_CURTA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
      </span>
    </Link>
  );
}

const PCT = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

function linhasDeNumeros(n: ParlamentarNaLista | null): Record<string, string> {
  if (!n) return {};
  return {
    gastos: formatarReais(n.gastos, true),
    presenca: n.presenca === null ? "—" : `${n.presenca_votou} de ${n.presenca_total} (${PCT(n.presenca)})`,
    projetos: String(n.projetos),
    normas: String(n.normas),
    emendas: formatarReais(n.emendas, true),
    governo: n.governo === null ? "—" : `${n.governo_iguais} de ${n.governo_total} (${PCT(n.governo)})`,
  };
}

function Resultado({ dados }: { dados: Comparacao }) {
  const { a, b, convergencia } = dados;
  const na = linhasDeNumeros(dados.numeros_a);
  const nb = linhasDeNumeros(dados.numeros_b);
  const criterios = dados.criterios.filter(
    (c) => c.id !== "nome",
  );

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        <Pessoa p={a} />
        <Pessoa p={b} />
      </div>
      <p className="text-sm">
        <Link href={`/comparar?a=${a.id}`} className="underline underline-offset-4">
          Trocar o segundo parlamentar
        </Link>
      </p>

      <CompartilharWhatsApp
        caminho={`/comparar?a=${a.id}&b=${b.id}`}
        texto={`Compare ${a.nome_parlamentar} e ${b.nome_parlamentar}, com dados oficiais:`}
      />

      <section aria-labelledby="numeros-titulo" className="revelar flex flex-col gap-3">
        <h2 id="numeros-titulo" className="text-xl font-semibold">
          Números de {dados.ano}
        </h2>
        <div className="overflow-x-auto rounded-xl bg-card border border-border/80">
          <table className="w-full text-left text-sm">
            <thead className="text-muted-foreground">
              <tr>
                <th scope="col" className="p-3 font-normal">
                  <span className="sr-only">Critério</span>
                </th>
                <th scope="col" className="p-3 font-medium text-foreground">{a.nome_parlamentar}</th>
                <th scope="col" className="p-3 font-medium text-foreground">{b.nome_parlamentar}</th>
              </tr>
            </thead>
            <tbody>
              {criterios.map((c) => (
                <tr key={c.id} className="border-t align-top">
                  <th scope="row" className="p-3 font-normal">
                    <span className="block">{c.nome}</span>
                    <span className="block text-xs text-muted-foreground">{mediaTexto(dados, c.id)}</span>
                  </th>
                  <td className="p-3 tabular-nums">{na[c.id] ?? "—"}</td>
                  <td className="p-3 tabular-nums">{nb[c.id] ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-sm text-muted-foreground">
          Projetos contam só os de autor principal, sem homenagens e datas comemorativas.{" "}
          <Link href="/sobre-as-fontes" className="underline underline-offset-2">
            Como calculamos
          </Link>
        </p>
      </section>

      {convergencia ? (
        <section aria-labelledby="votos-titulo" className="revelar flex flex-col gap-3">
          <h2 id="votos-titulo" className="text-xl font-semibold">
            Votos em comum
          </h2>
          {convergencia.votacoes_em_comum === 0 ? (
            <p className="text-muted-foreground">
              Os dois não votaram nas mesmas votações nominais em {dados.ano}.
            </p>
          ) : (
            <>
              <div className="rounded-xl bg-card p-4 border border-border/80">
                <p className="text-sm text-muted-foreground">Votaram igual em</p>
                <p className="text-2xl font-bold tabular-nums">
                  {convergencia.iguais} de {convergencia.votacoes_em_comum} votações
                </p>
                <p className="text-sm text-muted-foreground tabular-nums">
                  {PCT(convergencia.percentual ?? 0)} das votações nominais do Plenário em{" "}
                  {dados.ano} em que os dois votaram
                </p>
                <div
                  role="meter"
                  aria-label="Votações em que votaram igual"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={convergencia.percentual ?? 0}
                  className="mt-3 h-2 w-full rounded-full bg-muted"
                >
                  <div
                    className="h-2 rounded-full bg-chart-1"
                    style={{ width: `${convergencia.percentual ?? 0}%` }}
                  />
                </div>
              </div>

              {convergencia.por_tema.length > 0 && (
                <details className="rounded-xl bg-card p-4 border border-border/80">
                  <summary className="cursor-pointer font-medium">Votos iguais por tema</summary>
                  <table className="mt-3 w-full text-left text-sm">
                    <tbody>
                      {convergencia.por_tema.map((t) => (
                        <tr key={t.tema} className="border-t">
                          <th scope="row" className="py-2 pr-3 font-normal">{t.tema}</th>
                          <td className="py-2 text-right whitespace-nowrap tabular-nums">
                            {t.iguais} de {t.total}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </details>
              )}

              {convergencia.divergencias.length > 0 && (
                <details className="rounded-xl bg-card p-4 border border-border/80">
                  <summary className="cursor-pointer font-medium">
                    Onde votaram diferente (mais recentes)
                  </summary>
                  <ul className="mt-3 flex flex-col divide-y">
                    {convergencia.divergencias.map((d, i) => (
                      <li key={i} className="flex flex-col gap-1 py-3">
                        <span className="text-xs text-muted-foreground">{formatarData(d.data)}</span>
                        {d.proposicao &&
                          (d.url ? (
                            <a href={d.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                              {d.proposicao}
                            </a>
                          ) : (
                            <span className="font-medium">{d.proposicao}</span>
                          ))}
                        {d.proposicao_ementa && <p className="line-clamp-3 text-sm">{d.proposicao_ementa}</p>}
                        <p className="line-clamp-2 text-xs text-muted-foreground">{d.descricao}</p>
                        <dl className="grid grid-cols-2 gap-2 text-xs">
                          <div>
                            <dt className="text-muted-foreground">{a.nome_parlamentar}</dt>
                            <dd className="font-semibold">{d.voto_a}</dd>
                          </div>
                          <div>
                            <dt className="text-muted-foreground">{b.nome_parlamentar}</dt>
                            <dd className="font-semibold">{d.voto_b}</dd>
                          </div>
                        </dl>
                      </li>
                    ))}
                  </ul>
                </details>
              )}
            </>
          )}
        </section>
      ) : (
        <p className="rounded-xl bg-muted p-4 text-sm text-muted-foreground">
          {NOME_CASA[a.casa]} e {NOME_CASA[b.casa]} votam em votações diferentes, então não dá para
          comparar votos. Os números acima são comparáveis.
        </p>
      )}

      {dados.temas.length > 0 && (
        <section aria-labelledby="temas-titulo" className="revelar flex flex-col gap-3">
          <h2 id="temas-titulo" className="text-xl font-semibold">
            Projetos por tema
          </h2>
          <div className="overflow-x-auto rounded-xl bg-card border border-border/80">
            <table className="w-full text-left text-sm">
              <thead className="text-muted-foreground">
                <tr>
                  <th scope="col" className="p-3 font-normal">Tema (classificação oficial)</th>
                  <th scope="col" className="p-3 text-right font-normal">{primeiroNome(a)}</th>
                  <th scope="col" className="p-3 text-right font-normal">{primeiroNome(b)}</th>
                </tr>
              </thead>
              <tbody>
                {dados.temas.map((t) => (
                  <tr key={t.tema} className="border-t">
                    <th scope="row" className="p-3 font-normal">{t.tema}</th>
                    <td className="p-3 text-right tabular-nums">{t.a}</td>
                    <td className="p-3 text-right tabular-nums">{t.b}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-sm text-muted-foreground">
            Projetos como autor principal. Um projeto pode ter mais de um tema.
            {a.casa !== b.casa
              ? " Câmara e Senado usam classificações diferentes, então os nomes dos temas não coincidem."
              : ""}
          </p>
        </section>
      )}

      {dados.coautorias.total > 0 && (
        <section aria-labelledby="juntos-titulo" className="revelar flex flex-col gap-3">
          <h2 id="juntos-titulo" className="text-xl font-semibold">
            Projetos assinados juntos ({dados.coautorias.total})
          </h2>
          <ul className="flex flex-col divide-y rounded-xl bg-card px-4 border border-border/80">
            {dados.coautorias.itens.map((p) => (
              <li key={`${p.sigla_tipo}-${p.numero}-${p.ano}`} className="flex flex-col gap-1 py-3">
                <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                  {p.sigla_tipo} {p.numero}/{p.ano}
                </a>
                <p className="text-sm">{p.ementa}</p>
                <p className="text-xs text-muted-foreground">
                  {formatarData(p.data_apresentacao)} · {p.situacao ?? "Situação não informada"}
                </p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <FonteRodape fonte="Câmara, Senado e Portal da Transparência" url="/sobre-as-fontes" atualizadoEm={dados.atualizado_em} />
    </>
  );
}

function primeiroNome(p: ParlamentarResumo) {
  return p.nome_parlamentar.split(" ").slice(0, 2).join(" ");
}

function mediaTexto(dados: Comparacao, criterio: string): string {
  const casas = Array.from(new Set([dados.a.casa, dados.b.casa]));
  const partes = casas
    .map((casa) => {
      const valor = dados.medias[casa]?.[criterio];
      if (valor == null) return null;
      const formatado =
        criterio === "gastos" || criterio === "emendas"
          ? formatarReais(valor, true)
          : criterio === "presenca" || criterio === "governo"
            ? PCT(valor)
            : valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
      return `média ${CASA_CURTA[casa]} ${formatado}`;
    })
    .filter(Boolean);
  return partes.join(" · ");
}
