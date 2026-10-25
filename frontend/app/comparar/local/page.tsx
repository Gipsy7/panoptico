import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { FotoVereador } from "@/components/camara-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { ComparadorMatriz, type ParMatriz } from "@/components/comparador-matriz";
import { type CelulaTabela, ComparadorTabela, type GrupoTabela, type LinhaTabela } from "@/components/comparador-tabela";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import {
  type ComparacaoLocalN,
  type LadoLocal,
  getAssembleia,
  getCamara,
  getComparacaoLocalN,
  getVereador,
} from "@/lib/api";

const MAXIMO = 4;
const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);

type Params = { ids: number[]; diferencas: boolean; adicionar: boolean; antigo: boolean };

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
    diferencas: texto(sp.diferencas) === "1",
    adicionar: texto(sp.adicionar) === "1",
    antigo: !texto(sp.ids) && !!(texto(sp.a) || texto(sp.b)),
  };
}

function endereco(ids: number[], extras: Record<string, string> = {}) {
  const partes = [`ids=${ids.join(",")}`];
  for (const [k, v] of Object.entries(extras)) partes.push(`${k}=${v}`);
  return `/comparar/local?${partes.join("&")}`;
}

export async function generateMetadata({ searchParams }: PageProps<"/comparar/local">): Promise<Metadata> {
  const p = lerParametros(await searchParams);
  const padrao = { title: "Comparar vereadores e deputados estaduais" };
  if (p.ids.length < 2) return padrao;
  const resultado = await getComparacaoLocalN(p.ids);
  if (!resultado.ok) return padrao;
  const nomes = resultado.dados.pessoas.map((x) => x.nome);
  const lista = nomes.length > 2 ? `${nomes.slice(0, -1).join(", ")} e ${nomes[nomes.length - 1]}` : nomes.join(" e ");
  return {
    title: nomes.join(" × "),
    description: `Projetos, presença e votos de ${lista}, lado a lado, com dados da própria casa.`,
  };
}

export default function CompararLocalPage({ searchParams }: PageProps<"/comparar/local">) {
  return (
    <div data-largura="larga" className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl tracking-tight">Comparar na mesma casa</h1>
        <p className="text-muted-foreground">
          De dois a quatro vereadores da mesma câmara, ou deputados da mesma assembleia, lado a lado. Só na mesma casa,
          porque é onde a pauta e as votações são as mesmas.
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

async function Conteudo({ ids, diferencas, adicionar, antigo }: Params) {
  if (antigo && ids.length > 0) redirect(endereco(ids));
  if (ids.length === 0) {
    return (
      <p className="text-muted-foreground">
        Abra o perfil de um vereador ou deputado estadual e use &quot;Comparar com outro desta casa&quot;. Você encontra
        os perfis pela{" "}
        <Link href="/" className="underline underline-offset-2">
          busca por CEP ou por nome
        </Link>
        .
      </p>
    );
  }
  if (ids.length === 1) return <Escolher ids={ids} />;
  const resultado = await getComparacaoLocalN(ids);
  if (!resultado.ok) return <AvisoErro titulo="Não deu para comparar" mensagem={resultado.mensagem} />;
  return (
    <>
      {adicionar && ids.length < MAXIMO && (
        <div className="flex flex-col gap-2">
          <Escolher ids={ids} />
          <Link
            href={endereco(ids, diferencas ? { diferencas: "1" } : {})}
            className="inline-flex min-h-11 items-center text-sm underline underline-offset-4"
          >
            Cancelar
          </Link>
        </div>
      )}
      <Resultado dados={resultado.dados} diferencas={diferencas} />
    </>
  );
}

/** Com alguém escolhido, a lista dos colegas da mesma casa que ainda não estão na comparação. */
async function Escolher({ ids }: { ids: number[] }) {
  const primeiro = await getVereador(String(ids[0]));
  if (!primeiro.ok) return <AvisoErro titulo="Não encontrado" mensagem={primeiro.mensagem} />;
  const v = primeiro.dados;
  const casa =
    v.casa === "camara" && v.municipio_ibge ? await getCamara(v.municipio_ibge) : await getAssembleia(v.uf);
  const colegas = casa.ok ? casa.dados.itens.filter((c) => !ids.includes(c.id)) : [];
  return (
    <div className="flex flex-col gap-4">
      {ids.length === 1 && (
        <div className="flex items-center gap-3">
          <FotoVereador vereador={v} tamanho={48} decorativa />
          <div>
            <p className="font-semibold">{v.nome}</p>
            <p className="text-sm text-muted-foreground">{v.partido}</p>
          </div>
        </div>
      )}
      <h2 className="text-xl">{ids.length === 1 ? "Com quem você quer comparar?" : "Quem você quer acrescentar?"}</h2>
      <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
        {colegas.map((c) => (
          <li key={c.id} className="border-b border-border">
            <Link
              href={endereco([...ids, c.id])}
              className="flex min-h-11 items-center gap-3 py-2 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              <FotoVereador vereador={c} tamanho={36} decorativa />
              <span className="min-w-0">
                <span className="block truncate font-medium">{c.nome}</span>
                <span className="text-sm text-muted-foreground">
                  {[c.partido, c.titular ? null : "suplente"].filter(Boolean).join(" · ")}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function linhas(ps: LadoLocal[]): LinhaTabela[] {
  const contagem = (id: string, rotulo: string, f: (l: LadoLocal) => number): LinhaTabela => {
    const valores = ps.map(f);
    const escala = Math.max(0, ...valores);
    return {
      id,
      rotulo,
      celulas: valores.map((v): CelulaTabela => ({ texto: String(v), barra: { valor: v, escala, media: null } })),
    };
  };
  const simples = (id: string, rotulo: string, f: (l: LadoLocal) => string): LinhaTabela => ({
    id,
    rotulo,
    celulas: ps.map((l) => ({ texto: f(l) })),
  });
  return [
    contagem("projetos", "Projetos", (l) => l.projetos),
    contagem("proposicoes", "Proposições", (l) => l.proposicoes),
    {
      id: "presenca",
      rotulo: "Presença nas sessões",
      celulas: ps.map((l) => ({
        texto: l.presenca ? `${l.presenca.presencas} de ${l.presenca.sessoes}` : "—",
        barra:
          l.presenca && l.presenca.sessoes > 0
            ? { valor: l.presenca.presencas, escala: l.presenca.sessoes, media: null }
            : undefined,
      })),
    },
    contagem("votacoes", "Votações nominais em que votou", (l) => l.votacoes),
    simples("votos", "Votos recebidos na eleição", (l) => l.votos_recebidos?.toLocaleString("pt-BR") ?? "—"),
    simples("idade", "Idade", (l) => (l.pessoais?.idade != null ? `${l.pessoais.idade} anos` : "—")),
    simples("escolaridade", "Escolaridade", (l) => l.pessoais?.grau_instrucao ?? "—"),
    simples("ocupacao", "Ocupação declarada", (l) => l.pessoais?.ocupacao ?? "—"),
  ];
}

function Resultado({ dados, diferencas }: { dados: ComparacaoLocalN; diferencas: boolean }) {
  const { pessoas } = dados;
  const ids = pessoas.map((p) => p.id);
  const rota = dados.casa === "camara" ? "vereador" : "deputado-estadual";
  const nomeCasa = dados.casa === "camara" ? "câmara" : "assembleia";
  const extras: Record<string, string> = diferencas ? { diferencas: "1" } : {};

  const colunas = pessoas.map((p) => ({
    id: p.id,
    nome: p.nome,
    sub: p.partido ?? "",
    href: `/${rota}/${p.id}`,
    foto: <FotoVereador vereador={p} tamanho={40} decorativa />,
    remover: endereco(ids.filter((i) => i !== p.id)),
  }));

  const filtrar = (ls: LinhaTabela[]) =>
    diferencas ? ls.filter((l) => new Set(l.celulas.map((c) => c.texto)).size > 1) : ls;

  const tipos: LinhaTabela[] = dados.proposicoes_por_tipo.map((t) => {
    const escala = Math.max(0, ...t.valores);
    return {
      id: `tipo-${t.tipo}`,
      rotulo: t.tipo,
      celulas: t.valores.map((v) => ({ texto: String(v), barra: { valor: v, escala, media: null } })),
    };
  });
  const grupos: GrupoTabela[] = [{ id: "numeros", titulo: "Lado a lado", linhas: filtrar(linhas(pessoas)) }];
  if (tipos.length > 0) grupos.push({ id: "tipos", titulo: "Proposições por tipo", linhas: filtrar(tipos) });

  const pares: ParMatriz[] = dados.convergencia.map((c) => ({
    i: c.i,
    j: c.j,
    mesmaCasa: true,
    total: c.votacoes_em_comum,
    iguais: c.iguais,
    porTema: [],
    divergencias: c.divergencias.map((d) => ({
      data: d.data,
      titulo: d.materia,
      ementa: null,
      descricao: null,
      resultado: d.resultado,
      url: d.url,
      voto_i: d.voto_a,
      voto_j: d.voto_b,
    })),
  }));
  const nomes = pessoas.map((p) => p.nome);

  return (
    <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link
          href={endereco(ids, diferencas ? {} : { diferencas: "1" })}
          className="inline-flex min-h-11 items-center text-sm underline underline-offset-4"
        >
          {diferencas ? "Mostrar todas as linhas" : "Mostrar só as diferenças"}
        </Link>
        <CompartilharWhatsApp
          caminho={`/comparar/local?ids=${ids.join(",")}`}
          texto={`Compare ${nomes.join(", ")}, com dados da própria ${nomeCasa}:`}
        />
      </div>

      <ComparadorTabela
        colunas={colunas}
        grupos={grupos}
        adicionar={ids.length < MAXIMO ? endereco(ids, { adicionar: "1", ...extras }) : null}
        legenda="Comparação"
      />
      <p className="text-sm text-muted-foreground">
        Projetos, proposições, presença e votações: ano atual e anterior, como a {nomeCasa} publica. Dados pessoais e
        votos recebidos: declarados ao TSE.
      </p>

      <section aria-labelledby="votos-titulo" className="revelar flex flex-col gap-3">
        <h2 id="votos-titulo" className="text-2xl">
          Votos em comum
        </h2>
        <ComparadorMatriz nomes={nomes} pares={pares} periodo="votações nominais em que os dois registraram voto" />
      </section>

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </>
  );
}
