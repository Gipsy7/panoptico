import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { PlacarCompacto } from "@/components/barra-placar";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import { BarraFiltros } from "@/components/ui/barra-filtros";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import {
  type BuscaProjetos,
  type FiltrosProjetos,
  type ItemProjeto,
  type Municipio,
  getMunicipios,
  getTemasProjetos,
  getPauta,
  buscarProjetos,
} from "@/lib/api";
import { CASA_PROJETO_CURTA, formatarData, lugarDoProjeto, textoResultado } from "@/lib/formato";
import { anosParaFiltro, caminhoInterno, enderecoProjetos, lerFiltrosProjetos, situacaoSimples } from "@/lib/projetos";
import { UFS } from "@/lib/ufs";

export const metadata: Metadata = {
  title: "Projetos e votações",
  description:
    "Procure um projeto de lei pelo número ou por uma palavra: o que ele diz, em que pé está, quem votou e o que disseram. Congresso, assembleias e câmaras municipais, com dado oficial.",
};

const DIAS_PAUTA = 14;

export default function ProjetosPage({ searchParams }: PageProps<"/projetos">) {
  return (
    <div className="pagina-secoes">
      <CabecalhoPagina
        sobretitulo="Projetos e votações"
        titulo="O que está sendo votado"
        subtitulo="Procure um projeto de lei pelo número (PL 2338/2023) ou por uma palavra do assunto. Cada página mostra o que ele diz, em que pé está, quem votou e o que disseram."
      />
      <Revelacao fallback={<EsqueletoSecao rotulo="Carregando projetos…" secoes={2} />}>
        {searchParams.then((sp) => (
          <Conteudo filtros={lerFiltrosProjetos(sp)} />
        ))}
      </Revelacao>
    </div>
  );
}

async function Conteudo({ filtros }: { filtros: FiltrosProjetos }) {
  // Cidades do estado escolhido, para o seletor de cidade (sem JavaScript: aparece depois de filtrar por estado).
  // No Congresso o estado não filtra a lista (vale para o país todo); fica no endereço dos cartões, para
  // a página do projeto abrir já com "quem votou" do estado.
  const consulta: FiltrosProjetos = filtros.esfera === "federal" ? { ...filtros, uf: undefined, municipio: undefined } : filtros;
  const [resultado, municipios, listaTemas] = await Promise.all([
    buscarProjetos(consulta),
    filtros.uf ? getMunicipios(filtros.uf) : null,
    getTemasProjetos(filtros.casa),
  ]);
  const cidades = municipios?.ok ? municipios.dados : [];
  // null se a rota falhar: o filtro volta a ser um campo de texto.
  const temas = listaTemas.ok ? listaTemas.dados.temas : null;
  const primeiraPagina = !filtros.pagina || filtros.pagina === "1";

  return (
    <>
      <BarraDeBusca filtros={filtros} cidades={cidades} temas={temas} />
      {primeiraPagina && <NaPauta />}
      {resultado.ok ? (
        <Lista filtros={filtros} dados={resultado.dados} />
      ) : (
        <AvisoErro titulo="Não deu para carregar a lista" mensagem={resultado.mensagem} />
      )}
    </>
  );
}

// ---- Busca e filtros ----

const ESFERAS = [
  { valor: "", rotulo: "Tudo" },
  { valor: "federal", rotulo: "Congresso" },
  { valor: "estadual", rotulo: "Assembleia de um estado" },
  { valor: "municipal", rotulo: "Câmara de uma cidade" },
];

function BarraDeBusca({ filtros, cidades, temas }: { filtros: FiltrosProjetos; cidades: Municipio[]; temas: string[] | null }) {
  const nomeUf = filtros.uf ? UFS.find((u) => u.sigla === filtros.uf)?.nome : null;
  const nomeCidade = filtros.municipio ? cidades.find((c) => c.ibge === filtros.municipio)?.nome : null;
  const ativos = [
    filtros.esfera && { rotulo: ESFERAS.find((e) => e.valor === filtros.esfera)?.rotulo ?? filtros.esfera, campo: "esfera" as const },
    nomeUf && { rotulo: `Estado: ${nomeUf}`, campo: "uf" as const },
    filtros.municipio && { rotulo: `Cidade: ${nomeCidade ?? filtros.municipio}`, campo: "municipio" as const },
    filtros.tema && { rotulo: `Tema: ${filtros.tema}`, campo: "tema" as const },
    filtros.ano && { rotulo: `Ano: ${filtros.ano}`, campo: "ano" as const },
    filtros.votacao && {
      rotulo: filtros.votacao === "com" ? "Com votação nominal" : "Sem votação nominal",
      campo: "votacao" as const,
    },
  ].filter((a): a is { rotulo: string; campo: "esfera" | "uf" | "municipio" | "tema" | "ano" | "votacao" } => Boolean(a));

  return (
    <section aria-labelledby="busca-titulo" className="flex flex-col gap-3">
      <h2 id="busca-titulo" className="sr-only">
        Buscar projetos
      </h2>
      <Form action="/projetos" className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm">
          Número ou assunto
          <input
            type="search"
            name="q"
            defaultValue={filtros.q}
            placeholder="Ex.: PL 2338/2023 ou saúde mental"
            className="campo"
            enterKeyHint="search"
          />
        </label>
        {/* Os demais filtros acompanham a busca em campos ocultos; o painel abaixo os muda. */}
        {(["esfera", "uf", "municipio", "tema", "ano", "votacao"] as const).map(
          (c) => filtros[c] && <input key={c} type="hidden" name={c} value={filtros[c]} />,
        )}
        <button type="submit" className="botao sm:w-auto">
          Buscar
        </button>
      </Form>

      <BarraFiltros
        contador={ativos.length}
        limparHref={filtros.q ? enderecoProjetos({ q: filtros.q }, {}) : "/projetos"}
        painel={<PainelFiltros filtros={filtros} cidades={cidades} temas={temas} />}
        grupos={[
          ...(ativos.length
            ? [
                {
                  itens: ativos.map((a) => ({
                    rotulo: a.rotulo,
                    href: enderecoProjetos(filtros, a.campo === "uf" ? { uf: "", municipio: "" } : { [a.campo]: "" }),
                    remover: true,
                  })),
                },
              ]
            : []),
          {
            titulo: "Onde",
            itens: ESFERAS.map((e) => ({
              rotulo: e.rotulo,
              href: enderecoProjetos(filtros, { esfera: e.valor }),
              ativa: (filtros.esfera ?? "") === e.valor,
            })),
          },
          {
            titulo: "Votação nominal",
            itens: [
              { rotulo: "Todos", href: enderecoProjetos(filtros, { votacao: "" }), ativa: !filtros.votacao },
              { rotulo: "Teve", href: enderecoProjetos(filtros, { votacao: "com" }), ativa: filtros.votacao === "com" },
              { rotulo: "Não teve", href: enderecoProjetos(filtros, { votacao: "sem" }), ativa: filtros.votacao === "sem" },
            ],
          },
        ]}
      />
      {(filtros.uf || filtros.municipio) && !filtros.esfera && (
        <p className="text-sm text-muted-foreground">
          Com estado ou cidade escolhidos, a lista mostra projetos da assembleia e das câmaras municipais. Os do Congresso
          valem para o país todo:{" "}
          <Link href={enderecoProjetos(filtros, { esfera: "federal", municipio: "" })} className="font-medium underline underline-offset-4">
            ver os do Congresso
          </Link>
          {filtros.uf ? `, já com a votação de quem representa ${nomeUf ?? filtros.uf}` : ""}.
        </p>
      )}
    </section>
  );
}

function PainelFiltros({ filtros, cidades, temas }: { filtros: FiltrosProjetos; cidades: Municipio[]; temas: string[] | null }) {
  const ano = new Date().getFullYear();
  return (
    <Form action="/projetos" className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {filtros.q && <input type="hidden" name="q" value={filtros.q} />}
      <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-1">
        Onde
        <select name="esfera" defaultValue={filtros.esfera ?? ""} className="seletor w-full">
          {ESFERAS.map((e) => (
            <option key={e.valor} value={e.valor}>
              {e.rotulo}
            </option>
          ))}
        </select>
      </label>
      <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-1">
        Estado
        <select name="uf" defaultValue={filtros.uf ?? ""} className="seletor w-full">
          <option value="">Todos</option>
          {UFS.map((u) => (
            <option key={u.sigla} value={u.sigla}>
              {u.nome}
            </option>
          ))}
        </select>
      </label>
      {filtros.uf && cidades.length > 0 ? (
        <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-1">
          Cidade
          <select name="municipio" defaultValue={filtros.municipio ?? ""} className="seletor w-full">
            <option value="">Todas</option>
            {cidades.map((c) => (
              <option key={c.ibge} value={c.ibge}>
                {c.nome}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <p className="col-span-2 self-end text-sm text-muted-foreground sm:col-span-1">Escolha um estado e aplique para listar as cidades.</p>
      )}
      <label className="col-span-2 flex flex-col gap-1 text-sm sm:col-span-1">
        Tema (só do Congresso)
        {temas ? (
          <select name="tema" defaultValue={filtros.tema ?? ""} className="seletor w-full">
            <option value="">Todos</option>
            {(filtros.tema && !temas.includes(filtros.tema) ? [filtros.tema, ...temas] : temas).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        ) : (
          <input name="tema" defaultValue={filtros.tema} placeholder="Ex.: Saúde" className="seletor w-full" />
        )}
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Ano do projeto
        <select name="ano" defaultValue={filtros.ano ?? ""} className="seletor w-full">
          <option value="">Todos</option>
          {anosParaFiltro(ano).map((a) => (
            <option key={a} value={a}>
              {a}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-sm">
        Votação nominal
        <select name="votacao" defaultValue={filtros.votacao ?? ""} className="seletor w-full">
          <option value="">Todos</option>
          <option value="com">Teve votação nominal</option>
          <option value="sem">Não teve</option>
        </select>
      </label>
      <button type="submit" className="botao col-span-2 sm:col-span-3">
        Aplicar
      </button>
    </Form>
  );
}

// ---- Na pauta ----

async function NaPauta() {
  const r = await getPauta(DIAS_PAUTA);
  if (!r.ok) return null;
  const p = r.dados;
  const itens = p.itens.slice(0, 6);
  return (
    <section aria-labelledby="pauta-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="pauta-titulo" className="text-2xl">
          Na pauta do Plenário
        </h2>
        <p className="text-sm text-muted-foreground">Projetos marcados para sessão de votação nos próximos {DIAS_PAUTA} dias.</p>
      </div>
      {itens.length === 0 ? (
        <p className="nota text-sm">{p.aviso ?? `Não há sessão de votação marcada nos próximos ${DIAS_PAUTA} dias.`}</p>
      ) : (
        <>
          <ul className="lista-fios">
            {itens.map((i) => {
              const conteudo = (
                <>
                  <span className="text-sm text-muted-foreground tabular-nums">
                    {formatarData(i.data)} · {CASA_PROJETO_CURTA[i.casa]} · {i.sessao}
                  </span>
                  <span className="font-semibold">{i.proposicao ?? "Item sem identificação"}</span>
                  {i.ementa && <span className="line-clamp-2 text-sm text-muted-foreground">{i.ementa}</span>}
                </>
              );
              return (
                <li key={`${i.casa}-${i.data}-${i.sessao}-${i.ordem}-${i.proposicao}`}>
                  {i.link ? (
                    <Link href={caminhoInterno(i.link)} className="flex min-h-11 flex-col gap-0.5 py-3 hover:bg-accent/50">
                      {conteudo}
                    </Link>
                  ) : i.url_oficial ? (
                    <a href={i.url_oficial} target="_blank" rel="noopener noreferrer" className="flex min-h-11 flex-col gap-0.5 py-3 hover:bg-accent/50">
                      {conteudo}
                    </a>
                  ) : (
                    <div className="flex min-h-11 flex-col gap-0.5 py-3">{conteudo}</div>
                  )}
                </li>
              );
            })}
          </ul>
          {p.itens.length > itens.length && (
            <p className="text-sm text-muted-foreground">
              E mais {p.itens.length - itens.length} {p.itens.length - itens.length === 1 ? "item" : "itens"} na pauta, nas páginas oficiais.
            </p>
          )}
        </>
      )}
      <FonteRodape fonte={p.fonte_nome} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </section>
  );
}

// ---- Lista ----

function Lista({ filtros, dados }: { filtros: FiltrosProjetos; dados: BuscaProjetos }) {
  const paginas = Math.max(1, Math.ceil(dados.total / dados.por_pagina));
  const filtrando = Object.keys(filtros).some((k) => k !== "pagina");
  return (
    <section aria-labelledby="lista-titulo" className="flex flex-col gap-3">
      <div className="nota flex flex-col gap-1 text-sm">
        <h2 id="lista-titulo" className="font-semibold">
          {dados.total.toLocaleString("pt-BR")} {dados.total === 1 ? "resultado" : "resultados"}
          {filtros.q && <> para &quot;{filtros.q}&quot;</>}
        </h2>
        <p className="text-muted-foreground">
          Ordem: primeiro o que está na pauta, depois o que teve votação ou andamento mais recente. Não é ranking nem destaque.
        </p>
      </div>

      {dados.itens.length === 0 ? (
        <Vazio filtrando={filtrando} q={filtros.q} />
      ) : (
        <ul className="grid border-t border-border">
          {dados.itens.map((i) => (
            <li key={`${i.tipo}-${i.link}`} className="border-b border-border">
              <Cartao item={i} uf={filtros.esfera === "federal" ? filtros.uf : undefined} />
            </li>
          ))}
        </ul>
      )}

      {paginas > 1 && (
        <nav aria-label="Páginas" className="flex items-center justify-between gap-2 text-sm">
          <LinkPagina href={enderecoProjetos(filtros, { pagina: String(dados.pagina - 1) })} ativo={dados.pagina > 1}>
            ← Anteriores
          </LinkPagina>
          <span className="text-muted-foreground tabular-nums">
            Página {dados.pagina} de {paginas.toLocaleString("pt-BR")}
          </span>
          <LinkPagina href={enderecoProjetos(filtros, { pagina: String(dados.pagina + 1) })} ativo={dados.pagina < paginas}>
            Próximos →
          </LinkPagina>
        </nav>
      )}

      <div className="flex flex-col gap-1">
        {dados.fontes.map((f) => (
          <FonteRodape key={f.fonte_nome} fonte={f.fonte_nome} url={f.fonte_url} atualizadoEm={f.atualizado_em} />
        ))}
      </div>
    </section>
  );
}

function Vazio({ filtrando, q }: { filtrando: boolean; q?: string }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-muted-foreground">
        {q ? `Nenhum projeto encontrado para "${q}".` : filtrando ? "Nenhum projeto encontrado com esses filtros." : "Ainda não há projetos carregados."}
      </p>
      {filtrando && (
        <>
          <p className="text-sm">Algumas ideias: confira o número (ex.: PL 2338/2023), tente uma palavra só do assunto ou tire algum filtro.</p>
          <ul className="flex flex-wrap gap-2">
            {["saúde", "educação", "transporte", "segurança"].map((t) => (
              <li key={t}>
                <Link href={enderecoProjetos({}, { q: t })} className="pilula inline-flex min-h-11 items-center">
                  {t}
                </Link>
              </li>
            ))}
          </ul>
          <Link href="/projetos" className="alvo-link self-start text-sm font-medium underline underline-offset-4">
            Limpar a busca
          </Link>
        </>
      )}
    </div>
  );
}

const TIPO: Record<ItemProjeto["tipo"], string> = {
  proposicao: "Projeto",
  projeto_local: "Projeto",
  votacao_local: "Votação",
};

function Cartao({ item: i, uf }: { item: ItemProjeto; uf?: string }) {
  const lugar = lugarDoProjeto(i.casa, i.uf, i.municipio);
  const sit = i.tipo === "proposicao" ? situacaoSimples(i.situacao, i.virou_lei) : { rotulo: null, oficial: i.situacao };
  const v = i.ultima_votacao;
  const resultado = textoResultado(v?.resultado ?? null);
  return (
    <Link
      href={uf && i.esfera === "federal" ? `${caminhoInterno(i.link)}?uf=${uf}` : caminhoInterno(i.link)}
      className="flex flex-col gap-2 py-4 transition-colors duration-300 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
    >
      <p className="text-sm text-muted-foreground">
        {TIPO[i.tipo]} · {lugar}
      </p>
      <p className="text-lg leading-snug font-semibold">{i.rotulo}</p>
      {i.ementa && <p className="line-clamp-3 text-sm leading-relaxed">{i.ementa}</p>}
      {(sit.rotulo || sit.oficial) && (
        <p className="text-sm">
          {sit.rotulo ? (
            <>
              <span className="font-medium">{sit.rotulo}</span>
              {sit.oficial && <span className="block text-xs text-muted-foreground">Texto oficial: {sit.oficial}</span>}
            </>
          ) : (
            <span className="text-muted-foreground">{i.tipo === "votacao_local" ? `Resultado: ${sit.oficial}` : sit.oficial}</span>
          )}
        </p>
      )}
      {i.na_pauta && <p className="text-sm font-medium tabular-nums">Na pauta em {formatarData(i.na_pauta)}</p>}
      {v && v.sim != null && v.nao != null ? (
        <div className="flex flex-col gap-1">
          <PlacarCompacto sim={v.sim} nao={v.nao} />
          <p className="text-xs text-muted-foreground tabular-nums">
            Última votação nominal{v.data ? ` em ${formatarData(v.data)}` : ""}
            {resultado && ` · ${resultado}`}
          </p>
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">
          {v ? `Votação nominal${v.data ? ` em ${formatarData(v.data)}` : ""}${resultado ? ` · ${resultado}` : ""}` : "Sem votação nominal registrada"}
        </p>
      )}
    </Link>
  );
}

function LinkPagina({ href, ativo, children }: { href: string; ativo: boolean; children: React.ReactNode }) {
  if (!ativo) return <span className="inline-flex min-h-11 items-center text-muted-foreground/50">{children}</span>;
  return (
    <Link href={href} className="alvo-link font-medium underline underline-offset-4">
      {children}
    </Link>
  );
}
