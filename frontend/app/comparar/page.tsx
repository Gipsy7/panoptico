import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { BuscaParlamentar } from "@/components/busca-parlamentar";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { ComparadorMatriz, type ParMatriz } from "@/components/comparador-matriz";
import {
  type CelulaTabela,
  ComparadorTabela,
  type GrupoTabela,
  type LinhaTabela,
} from "@/components/comparador-tabela";
import { FonteRodape } from "@/components/fonte-rodape";
import { Foto } from "@/components/parlamentar-card";
import { Revelacao } from "@/components/revelacao";
import {
  type ComparacaoN,
  type ParlamentarNaLista,
  type ParlamentarResumo,
  getComparacaoN,
  getParlamentar,
} from "@/lib/api";
import { CASA_CURTA, formatarData, formatarGastos, formatarReais } from "@/lib/formato";

const MAXIMO = 4;
const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);
const PCT = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

type Params = { ids: number[]; ano?: string; diferencas: boolean; adicionar: boolean; antigo: boolean };

/** Lê `ids=1,2,3` (ou os links antigos `a=` e `b=`), sem repetidos e até quatro. */
function lerParametros(sp: Record<string, string | string[] | undefined>): Params {
  const bruto = texto(sp.ids) ?? [texto(sp.a), texto(sp.b)].filter(Boolean).join(",");
  const ids: number[] = [];
  for (const parte of bruto.split(",")) {
    const n = Number(parte.trim());
    if (Number.isInteger(n) && n > 0 && !ids.includes(n)) ids.push(n);
  }
  return {
    ids: ids.slice(0, MAXIMO),
    ano: texto(sp.ano),
    diferencas: texto(sp.diferencas) === "1",
    adicionar: texto(sp.adicionar) === "1",
    antigo: !texto(sp.ids) && !!(texto(sp.a) || texto(sp.b)),
  };
}

function endereco(ids: number[], ano?: string | number, extras: Record<string, string> = {}) {
  const partes = [`ids=${ids.join(",")}`];
  if (ano) partes.push(`ano=${ano}`);
  for (const [k, v] of Object.entries(extras)) partes.push(`${k}=${v}`);
  return `/comparar?${partes.join("&")}`;
}

export async function generateMetadata({ searchParams }: PageProps<"/comparar">): Promise<Metadata> {
  const sp = await searchParams;
  const p = lerParametros(sp);
  if (p.ids.length < 2) return { title: "Comparar parlamentares" };
  const resultado = await getComparacaoN(p.ids, p.ano);
  if (!resultado.ok) return { title: "Comparar parlamentares" };
  const nomes = resultado.dados.pessoas.map((x) => x.nome_parlamentar);
  const lista = nomes.length > 2 ? `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}` : nomes.join(" e ");
  const titulo = nomes.join(" × ");
  // Links antigos (a e b) mantêm a imagem de sempre; os novos usam ids.
  const imagem = p.antigo ? `/comparar/imagem?a=${p.ids[0]}&b=${p.ids[1]}` : `/comparar/imagem?ids=${p.ids.join(",")}`;
  return {
    title: titulo,
    description: `Gastos, presença, projetos e votos de ${lista}, lado a lado, com dados oficiais.`,
    openGraph: { title: titulo, images: [{ url: imagem, width: 1200, height: 630 }] },
  };
}

export default function CompararPage({ searchParams }: PageProps<"/comparar">) {
  return (
    <div data-largura="larga" className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl tracking-tight">Comparar parlamentares</h1>
        <p className="text-muted-foreground">
          De duas a quatro pessoas lado a lado: números, temas dos projetos e, se forem da mesma Casa, em quantas
          votações votaram igual.
        </p>
      </header>
      <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => (
          <Conteudo {...lerParametros(sp)} />
        ))}
      </Revelacao>
    </div>
  );
}

async function Conteudo({ ids, ano, diferencas, adicionar, antigo }: Params) {
  // Link antigo (?a=&b=): leva para o endereço novo.
  if (antigo && ids.length > 0) redirect(endereco(ids, ano));

  if (ids.length === 0) {
    return <BuscaParlamentar hrefBase="/comparar?ids=" rotulo="Escolha o primeiro parlamentar" />;
  }
  if (ids.length === 1) {
    const primeiro = await getParlamentar(String(ids[0]));
    if (!primeiro.ok) return <AvisoErro titulo="Parlamentar não encontrado" mensagem={primeiro.mensagem} />;
    return (
      <div className="flex flex-col gap-4">
        <Pessoa p={primeiro.dados} />
        <BuscaParlamentar
          hrefBase={`/comparar?ids=${ids[0]},`}
          rotulo="Com quem você quer comparar?"
          ignorarId={primeiro.dados.id}
        />
      </div>
    );
  }
  const resultado = await getComparacaoN(ids, ano);
  if (!resultado.ok) return <AvisoErro titulo="Não deu para comparar" mensagem={resultado.mensagem} />;
  return <Resultado dados={resultado.dados} ids={ids} diferencas={diferencas} adicionar={adicionar} />;
}

function Pessoa({ p }: { p: ParlamentarResumo }) {
  return (
    <Link
      href={`/parlamentar/${p.id}`}
      className="flex min-w-0 flex-col items-center gap-2 text-center transition-opacity hover:opacity-80"
    >
      <Foto parlamentar={p} largura={64} />
      <span className="font-semibold leading-tight">{p.nome_parlamentar}</span>
      <span className="text-sm text-muted-foreground">
        {CASA_CURTA[p.casa]} · {[p.partido, p.uf].filter(Boolean).join(" · ")}
      </span>
    </Link>
  );
}

const PERCENTUAIS = new Set(["presenca", "governo"]);

function textoDe(n: ParlamentarNaLista | null, criterio: string): string {
  if (!n) return "—";
  switch (criterio) {
    case "gastos":
      return formatarGastos(n.gastos, true);
    case "presenca":
      return n.presenca === null ? "—" : `${n.presenca_votou} de ${n.presenca_total} (${PCT(n.presenca)})`;
    case "projetos":
      return String(n.projetos);
    case "normas":
      return String(n.normas);
    case "emendas":
      return formatarReais(n.emendas, true);
    case "governo":
      return n.governo === null ? "—" : `${n.governo_iguais} de ${n.governo_total} (${PCT(n.governo)})`;
    default:
      return "—";
  }
}

function valorDe(n: ParlamentarNaLista | null, criterio: string): number | null {
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

function mediaFormatada(criterio: string, valor: number): string {
  if (criterio === "gastos" || criterio === "emendas") return formatarReais(valor, true);
  if (PERCENTUAIS.has(criterio)) return PCT(valor);
  return valor.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
}

function Resultado({
  dados,
  ids,
  diferencas,
  adicionar,
}: {
  dados: ComparacaoN;
  ids: number[];
  diferencas: boolean;
  adicionar: boolean;
}) {
  const { pessoas } = dados;
  const idsAtuais = pessoas.map((p) => p.id);
  const extrasDif: Record<string, string> = diferencas ? { diferencas: "1" } : {};
  const base = (extras: Record<string, string> = {}) => endereco(idsAtuais, dados.ano, extras);

  const colunas = pessoas.map((p) => ({
    id: p.id,
    nome: p.nome_parlamentar,
    sub: `${CASA_CURTA[p.casa]} · ${[p.partido, p.uf].filter(Boolean).join(" · ")}`,
    href: `/parlamentar/${p.id}`,
    foto: <Foto parlamentar={p} largura={40} />,
    remover: endereco(
      idsAtuais.filter((i) => i !== p.id),
      dados.ano,
    ),
  }));

  const numeros: LinhaTabela[] = dados.criterios
    .filter((c) => c.id !== "nome")
    .map((c) => {
      const valores = dados.numeros.map((n) => valorDe(n, c.id));
      const medias = pessoas.map((p) => dados.medias[p.casa]?.[c.id] ?? null);
      const escala = PERCENTUAIS.has(c.id)
        ? 100
        : Math.max(0, ...valores.filter((v): v is number => v !== null), ...medias.filter((m): m is number => m !== null));
      return {
        id: c.id,
        rotulo: c.nome,
        celulas: pessoas.map((p, i): CelulaTabela => ({
          texto: textoDe(dados.numeros[i], c.id),
          barra: { valor: valores[i], escala, media: medias[i] },
          media: medias[i] === null ? undefined : `média ${CASA_CURTA[p.casa]} ${mediaFormatada(c.id, medias[i])}`,
        })),
      };
    });

  const temas: LinhaTabela[] = dados.temas.map((t) => {
    const escala = Math.max(0, ...t.valores);
    return {
      id: `tema-${t.tema}`,
      rotulo: t.tema,
      celulas: t.valores.map((v) => ({ texto: String(v), barra: { valor: v, escala, media: null } })),
    };
  });

  const filtrar = (linhas: LinhaTabela[]) =>
    diferencas ? linhas.filter((l) => new Set(l.celulas.map((c) => c.texto)).size > 1) : linhas;

  const grupos: GrupoTabela[] = [{ id: "numeros", titulo: `Números de ${dados.ano}`, linhas: filtrar(numeros) }];
  if (temas.length > 0) grupos.push({ id: "temas", titulo: "Projetos por tema", linhas: filtrar(temas) });

  const pares: ParMatriz[] = dados.convergencia.map((c) => ({
    i: c.i,
    j: c.j,
    mesmaCasa: c.mesma_casa && c.convergencia !== null,
    total: c.convergencia?.votacoes_em_comum ?? 0,
    iguais: c.convergencia?.iguais ?? 0,
    porTema: c.convergencia?.por_tema.map((t) => ({ tema: t.tema, iguais: t.iguais, total: t.total })) ?? [],
    divergencias:
      c.convergencia?.divergencias.map((d) => ({
        data: d.data,
        titulo: d.proposicao,
        ementa: d.proposicao_ementa,
        descricao: d.descricao,
        resultado: null,
        url: d.url,
        voto_i: d.voto_a,
        voto_j: d.voto_b,
      })) ?? [],
  }));
  const coautorias = dados.coautorias.filter((c) => c.total > 0);
  const nomes = pessoas.map((p) => p.nome_parlamentar);
  const sobrenome = (i: number) => pessoas[i].nome_parlamentar;

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
          <nav aria-label="Ano" className="flex flex-wrap items-center gap-1">
            <span className="mr-1 text-muted-foreground">Ano</span>
            {dados.anos_disponiveis.map((a) => (
              <Link
                key={a}
                href={endereco(idsAtuais, a, diferencas ? { diferencas: "1" } : {})}
                aria-current={a === dados.ano ? "page" : undefined}
                className={`inline-flex min-h-11 min-w-11 items-center justify-center px-2 underline-offset-4 ${
                  a === dados.ano ? "font-semibold underline decoration-bronze decoration-2" : "hover:underline"
                }`}
              >
                {a}
              </Link>
            ))}
          </nav>
          <Link
            href={diferencas ? base() : base({ diferencas: "1" })}
            className="inline-flex min-h-11 items-center underline underline-offset-4"
          >
            {diferencas ? "Mostrar todas as linhas" : "Mostrar só as diferenças"}
          </Link>
        </div>
        <CompartilharWhatsApp
          caminho={`/comparar?ids=${idsAtuais.join(",")}`}
          texto={`Compare ${nomes.join(", ")}, com dados oficiais:`}
        />
      </div>

      {adicionar && ids.length < MAXIMO && (
        <div className="painel flex flex-col gap-2">
          <BuscaParlamentar
            hrefBase={`/comparar?ano=${dados.ano}${diferencas ? "&diferencas=1" : ""}&ids=${idsAtuais.join(",")},`}
            rotulo="Quem você quer acrescentar?"
          />
          <Link href={base(diferencas ? { diferencas: "1" } : {})} className="inline-flex min-h-11 items-center text-sm underline underline-offset-4">
            Cancelar
          </Link>
        </div>
      )}

      <ComparadorTabela
        colunas={colunas}
        grupos={grupos}
        adicionar={idsAtuais.length < MAXIMO ? base({ adicionar: "1", ...extrasDif }) : null}
        legenda={`Comparação · ${dados.ano}`}
      />
      <p className="text-sm text-muted-foreground">
        A barra mostra o valor de cada pessoa e a marca vertical, a média da Casa (parlamentares em exercício). Projetos
        contam só os de autor principal, sem homenagens e datas comemorativas.{" "}
        <Link href="/sobre-as-fontes" className="underline underline-offset-2">
          Como calculamos
        </Link>
        {dados.mesma_casa
          ? ""
          : ". Câmara e Senado usam classificações diferentes de tema, então os nomes dos temas não coincidem."}
      </p>

      <section aria-labelledby="votos-titulo" className="revelar flex flex-col gap-3">
        <h2 id="votos-titulo" className="text-2xl">
          Votos em comum
        </h2>
        <ComparadorMatriz nomes={nomes} pares={pares} periodo={`votações nominais do Plenário em ${dados.ano}`} />
      </section>

      {coautorias.length > 0 && (
        <section aria-labelledby="juntos-titulo" className="revelar flex flex-col gap-3">
          <h2 id="juntos-titulo" className="text-2xl">
            Projetos assinados juntos
          </h2>
          {coautorias.map((c) => (
            <details key={`${c.i}-${c.j}`} className="painel" open={coautorias.length === 1}>
              <summary className="flex min-h-11 cursor-pointer items-center font-medium">
                {sobrenome(c.i)} e {sobrenome(c.j)} ({c.total})
              </summary>
              <ul className="lista-fios mt-2 flex flex-col">
                {c.itens.map((p) => (
                  <li key={`${p.sigla_tipo}-${p.numero}-${p.ano}`} className="flex flex-col gap-1 py-3">
                    <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                      {p.sigla_tipo} {p.numero}/{p.ano}
                    </a>
                    <p className="text-sm">{p.ementa}</p>
                    <p className="text-[13px] text-muted-foreground">
                      {formatarData(p.data_apresentacao)} · {p.situacao ?? "Situação não informada"}
                    </p>
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </section>
      )}

      <FonteRodape fonte="Câmara, Senado e Portal da Transparência" url="/sobre-as-fontes" atualizadoEm={dados.atualizado_em} />
    </>
  );
}
