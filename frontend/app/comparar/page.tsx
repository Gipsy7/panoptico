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
import { CASA_CURTA, NOME_CASA, formatarData, formatarGastos, formatarReais } from "@/lib/formato";

type Busca = { a?: string; b?: string; ano?: string; diferencas?: boolean };

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
        <h1 className="text-3xl tracking-tight">Comparar parlamentares</h1>
        <p className="text-muted-foreground">
          Dois parlamentares lado a lado: números, temas dos projetos e, se forem da mesma Casa,
          em quantas votações votaram igual.
        </p>
      </header>
      <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => (
          <Conteudo a={texto(sp.a)} b={texto(sp.b)} ano={texto(sp.ano)} diferencas={texto(sp.diferencas) === "1"} />
        ))}
      </Revelacao>
    </div>
  );
}

async function Conteudo({ a, b, ano, diferencas = false }: Busca) {
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
  return <Resultado dados={resultado.dados} diferencas={diferencas} />;
}

function Pessoa({ p }: { p: ParlamentarResumo }) {
  return (
    <Link
      href={`/parlamentar/${p.id}`}
      className="flex min-w-0 flex-col items-center gap-2 text-center transition-opacity hover:opacity-80"
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
    gastos: formatarGastos(n.gastos, true),
    presenca: n.presenca === null ? "—" : `${n.presenca_votou} de ${n.presenca_total} (${PCT(n.presenca)})`,
    projetos: String(n.projetos),
    normas: String(n.normas),
    emendas: formatarReais(n.emendas, true),
    governo: n.governo === null ? "—" : `${n.governo_iguais} de ${n.governo_total} (${PCT(n.governo)})`,
  };
}

function Resultado({ dados, diferencas }: { dados: Comparacao; diferencas: boolean }) {
  const { a, b, convergencia } = dados;
  const na = linhasDeNumeros(dados.numeros_a);
  const nb = linhasDeNumeros(dados.numeros_b);
  const base = `/comparar?a=${a.id}&b=${b.id}&ano=${dados.ano}`;

  const numeros: Linha[] = dados.criterios
    .filter((c) => c.id !== "nome")
    .map((c) => ({
      id: c.id,
      rotulo: c.nome,
      detalhe: mediaTexto(dados, c.id),
      a: na[c.id] ?? "—",
      b: nb[c.id] ?? "—",
      va: valorNumerico(dados.numeros_a, c.id),
      vb: valorNumerico(dados.numeros_b, c.id),
    }));
  const votosPorTema: Linha[] =
    convergencia && convergencia.votacoes_em_comum > 0
      ? convergencia.por_tema.map((t) => ({
          id: `voto-${t.tema}`,
          rotulo: t.tema,
          inteira: `votaram igual em ${t.iguais} de ${t.total}`,
          a: "",
          b: "",
          va: null,
          vb: null,
        }))
      : [];
  const temas: Linha[] = dados.temas.map((t) => ({
    id: `tema-${t.tema}`,
    rotulo: t.tema,
    a: String(t.a),
    b: String(t.b),
    va: t.a,
    vb: t.b,
  }));
  const visiveis = (linhas: Linha[]) =>
    diferencas ? linhas.filter((l) => l.inteira !== undefined || l.a !== l.b) : linhas;

  return (
    <>
      <div className="sticky top-14 z-30 -mx-4 border-b border-foreground bg-background/95 px-4 py-3 backdrop-blur-md">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-[minmax(0,1.1fr)_1fr_1fr]">
          <div className="hidden flex-col justify-end md:flex">
            <span className="sobretitulo">Comparação · {dados.ano}</span>
          </div>
          <Coluna p={a} trocar={`/comparar?a=${b.id}`} />
          <Coluna p={b} trocar={`/comparar?a=${a.id}`} />
        </div>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm">
          {diferencas ? (
            <Link href={base} className="underline underline-offset-4">
              Mostrar todas as linhas
            </Link>
          ) : (
            <Link href={`${base}&diferencas=1`} className="underline underline-offset-4">
              Mostrar só as diferenças
            </Link>
          )}
        </p>
        <CompartilharWhatsApp
          caminho={`/comparar?a=${a.id}&b=${b.id}`}
          texto={`Compare ${a.nome_parlamentar} e ${b.nome_parlamentar}, com dados oficiais:`}
        />
      </div>

      <Grupo titulo={`Números de ${dados.ano}`} id="numeros-titulo" a={a} b={b} linhas={visiveis(numeros)}>
        Projetos contam só os de autor principal, sem homenagens e datas comemorativas.{" "}
        <Link href="/sobre-as-fontes" className="underline underline-offset-2">
          Como calculamos
        </Link>
      </Grupo>

      {convergencia ? (
        <section aria-labelledby="votos-titulo" className="revelar flex flex-col gap-3">
          <h2 id="votos-titulo" className="text-2xl">
            Votos em comum
          </h2>
          {convergencia.votacoes_em_comum === 0 ? (
            <p className="text-muted-foreground">
              Os dois não votaram nas mesmas votações nominais em {dados.ano}.
            </p>
          ) : (
            <>
              <div className="figura">
                <p className="text-sm text-muted-foreground">Votaram igual em</p>
                <p className="numero text-3xl">
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
              {votosPorTema.length > 0 && (
                <details className="painel">
                  <summary className="cursor-pointer font-medium">Votos iguais por tema</summary>
                  <div className="mt-3">
                    <Linhas linhas={votosPorTema} a={a} b={b} />
                  </div>
                </details>
              )}
              {convergencia.divergencias.length > 0 && (
                <details className="painel">
                  <summary className="cursor-pointer font-medium">
                    Onde votaram diferente (mais recentes)
                  </summary>
                  <ul className="mt-3 lista-fios flex flex-col">
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
        <p className="nota text-sm text-muted-foreground">
          {NOME_CASA[a.casa]} e {NOME_CASA[b.casa]} votam em votações diferentes, então não dá para
          comparar votos. Os números acima são comparáveis.
        </p>
      )}

      {temas.length > 0 && (
        <Grupo titulo="Projetos por tema" id="temas-titulo" a={a} b={b} linhas={visiveis(temas)}>
          Projetos como autor principal, pela classificação oficial. Um projeto pode ter mais de um
          tema.
          {a.casa !== b.casa
            ? " Câmara e Senado usam classificações diferentes, então os nomes dos temas não coincidem."
            : ""}
        </Grupo>
      )}

      {dados.coautorias.total > 0 && (
        <section aria-labelledby="juntos-titulo" className="revelar flex flex-col gap-3">
          <h2 id="juntos-titulo" className="text-2xl">
            Projetos assinados juntos ({dados.coautorias.total})
          </h2>
          <ul className="lista-fios flex flex-col">
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

type Linha = {
  id: string;
  rotulo: string;
  detalhe?: string;
  /** Texto que ocupa as duas colunas (ex.: votos iguais por tema, um dado do par). */
  inteira?: string;
  a: string;
  b: string;
  va: number | null;
  vb: number | null;
};

function Coluna({ p, trocar }: { p: ParlamentarResumo; trocar: string }) {
  return (
    <div className="flex min-w-0 items-center gap-3">
      <Link href={`/parlamentar/${p.id}`} className="shrink-0 hover:opacity-80">
        <Foto parlamentar={p} largura={40} />
      </Link>
      <div className="flex min-w-0 flex-col gap-1">
        <Link href={`/parlamentar/${p.id}`} className="truncate font-semibold leading-tight hover:underline">
          {p.nome_parlamentar}
        </Link>
        <span className="flex flex-wrap items-center gap-1">
          {p.partido && <span className="pilula">{p.partido}</span>}
          <span className="pilula">
            {CASA_CURTA[p.casa]} · {p.uf}
          </span>
          <Link href={trocar} className="ml-1 text-xs text-muted-foreground underline underline-offset-2">
            trocar
          </Link>
        </span>
      </div>
    </div>
  );
}

function Grupo({
  titulo,
  id,
  a,
  b,
  linhas,
  children,
}: {
  titulo: string;
  id: string;
  a: ParlamentarResumo;
  b: ParlamentarResumo;
  linhas: Linha[];
  children?: React.ReactNode;
}) {
  return (
    <section aria-labelledby={id} className="revelar flex flex-col gap-3">
      <h2 id={id} className="text-2xl">
        {titulo}
      </h2>
      {linhas.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nenhuma diferença neste grupo.</p>
      ) : (
        <Linhas linhas={linhas} a={a} b={b} />
      )}
      {children && <p className="text-sm text-muted-foreground">{children}</p>}
    </section>
  );
}

function Linhas({ linhas, a, b }: { linhas: Linha[]; a: ParlamentarResumo; b: ParlamentarResumo }) {
  return (
    <ul className="lista-fios flex flex-col">
      {linhas.map((l) => {
        const maior = Math.max(l.va ?? 0, l.vb ?? 0);
        return (
          <li key={l.id} className="grid grid-cols-2 gap-x-4 gap-y-1.5 py-3 md:grid-cols-[minmax(0,1.1fr)_1fr_1fr]">
            <div className="col-span-2 md:col-span-1">
              <span className="block text-sm">{l.rotulo}</span>
              {l.detalhe && <span className="block text-xs text-muted-foreground">{l.detalhe}</span>}
            </div>
            {l.inteira !== undefined ? (
              <span className="col-span-2 text-sm tabular-nums">{l.inteira}</span>
            ) : (
              <>
                <Valor nome={a.nome_parlamentar} texto={l.a} valor={l.va} maior={maior} />
                <Valor nome={b.nome_parlamentar} texto={l.b} valor={l.vb} maior={maior} />
              </>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function Valor({ nome, texto, valor, maior }: { nome: string; texto: string; valor: number | null; maior: number }) {
  // Barra neutra, proporcional ao maior dos dois: mostra a diferença sem eleger um "melhor".
  const largura = valor !== null && maior > 0 ? Math.max(2, (valor / maior) * 100) : 0;
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="text-sm tabular-nums">
        <span className="sr-only">{nome}: </span>
        {texto}
      </span>
      {valor !== null && (
        <span aria-hidden className="h-1 w-full rounded-full bg-muted">
          <span className="block h-1 rounded-full bg-chart-1" style={{ width: `${largura}%` }} />
        </span>
      )}
    </div>
  );
}

function valorNumerico(n: ParlamentarNaLista | null, criterio: string): number | null {
  if (!n) return null;
  switch (criterio) {
    case "gastos":
      return n.gastos;
    case "presenca":
      return n.presenca;
    case "projetos":
      return n.projetos;
    case "normas":
      return n.normas;
    case "emendas":
      return n.emendas;
    case "governo":
      return n.governo;
    default:
      return null;
  }
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
