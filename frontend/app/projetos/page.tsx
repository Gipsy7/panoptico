import type { Metadata } from "next";
import Form from "next/form";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { PlacarCompacto } from "@/components/barra-placar";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import { CampoSelect, CampoTexto, type FiltroAtivo, PilulasAtivas, SemResultados } from "@/components/ui/campos-filtro";
import { CamposUfCidade } from "@/components/ui/campos-filtro-cliente";
import { PainelFiltros } from "@/components/ui/painel-filtros";
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
import { anosParaFiltro, caminhoInterno, enderecoProjetos, lerFiltrosProjetos, recortar, situacaoSimples } from "@/lib/projetos";
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
  const ativos = filtrosAtivos(filtros, cidades);
  // A pauta só aparece na lista sem busca nem filtro: com filtro, o resultado vem logo abaixo.
  const semFiltro = ativos.length === 0 && !filtros.q;

  return (
    <>
      <BarraDeBusca filtros={filtros} cidades={cidades} temas={temas} ativos={ativos} />
      {primeiraPagina && semFiltro && <NaPauta />}
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

const CASAS: Record<string, string> = {
  camara: "Câmara dos Deputados",
  senado: "Senado",
  assembleia: "Assembleias",
  camara_municipal: "Câmaras municipais",
};

/** Filtros ativos (sem a busca por texto, que tem o seu campo), cada um com o endereço sem ele. */
function filtrosAtivos(filtros: FiltrosProjetos, cidades: Municipio[]): FiltroAtivo[] {
  const nomeUf = filtros.uf ? (UFS.find((u) => u.sigla === filtros.uf)?.nome ?? filtros.uf) : null;
  const nomeCidade = filtros.municipio ? (cidades.find((c) => c.ibge === filtros.municipio)?.nome ?? filtros.municipio) : null;
  const sem = (m: Partial<FiltrosProjetos>) => enderecoProjetos(filtros, m);
  const ativos: (FiltroAtivo | null)[] = [
    filtros.esfera ? { rotulo: ESFERAS.find((e) => e.valor === filtros.esfera)?.rotulo ?? filtros.esfera, href: sem({ esfera: "" }) } : null,
    filtros.casa ? { rotulo: `Casa: ${CASAS[filtros.casa] ?? filtros.casa}`, href: sem({ casa: "" }) } : null,
    nomeUf ? { rotulo: `Estado: ${nomeUf}`, href: sem({ uf: "", municipio: "" }) } : null,
    nomeCidade ? { rotulo: `Cidade: ${nomeCidade}`, href: sem({ municipio: "" }) } : null,
    filtros.tema ? { rotulo: `Tema: ${filtros.tema}`, href: sem({ tema: "" }) } : null,
    filtros.ano ? { rotulo: `Ano: ${filtros.ano}`, href: sem({ ano: "" }) } : null,
    filtros.votacao
      ? { rotulo: filtros.votacao === "com" ? "Teve votação nominal" : "Não teve votação nominal", href: sem({ votacao: "" }) }
      : null,
  ];
  return ativos.filter((a): a is FiltroAtivo => a !== null);
}

function BarraDeBusca({
  filtros,
  cidades,
  temas,
  ativos,
}: {
  filtros: FiltrosProjetos;
  cidades: Municipio[];
  temas: string[] | null;
  ativos: FiltroAtivo[];
}) {
  const nomeUf = filtros.uf ? UFS.find((u) => u.sigla === filtros.uf)?.nome : null;
  // Volta a ter só a busca por texto (ou nada).
  const limparHref = filtros.q ? enderecoProjetos({ q: filtros.q }, {}) : "/projetos";
  const chave = enderecoProjetos(filtros, { pagina: filtros.pagina ?? "" });
  const pilulas: FiltroAtivo[] = filtros.q
    ? [{ rotulo: `Busca: ${filtros.q}`, href: enderecoProjetos(filtros, { q: "" }) }, ...ativos]
    : ativos;

  return (
    <section aria-labelledby="busca-titulo" className="flex flex-col gap-[var(--esp-4)]">
      <h2 id="busca-titulo" className="sr-only">
        Buscar projetos
      </h2>
      <Form key={`q-${chave}`} action="/projetos" role="search" className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-1 text-sm font-medium">
          Número ou assunto
          <input
            type="search"
            name="q"
            defaultValue={filtros.q}
            placeholder="Ex.: PL 2338/2023 ou saúde mental"
            className="campo text-base font-normal"
            enterKeyHint="search"
          />
        </label>
        {/* Os demais filtros acompanham a busca em campos ocultos; o painel abaixo os muda. */}
        {(["esfera", "casa", "uf", "municipio", "tema", "ano", "votacao"] as const).map(
          (c) => filtros[c] && <input key={c} type="hidden" name={c} value={filtros[c]} />,
        )}
        <button type="submit" className="botao sm:w-auto">
          Buscar
        </button>
      </Form>

      <PainelFiltros
        key={chave}
        action="/projetos"
        ativos={ativos.length}
        limparHref={limparHref}
        ocultos={{ q: filtros.q, casa: filtros.casa }}
        titulo="Filtrar projetos"
      >
        <CampoSelect rotulo="Onde" name="esfera" defaultValue={filtros.esfera} opcoes={ESFERAS} />
        <CamposUfCidade
          ufs={UFS.map((u) => ({ valor: u.sigla, rotulo: u.nome }))}
          uf={filtros.uf}
          municipio={filtros.municipio}
          cidades={cidades.map((c) => ({ ibge: c.ibge, nome: c.nome }))}
        />
        {temas ? (
          <CampoSelect
            rotulo="Tema"
            name="tema"
            defaultValue={filtros.tema}
            ajuda="Só os projetos do Congresso têm tema."
            opcoes={[
              { valor: "", rotulo: "Todos os temas" },
              ...(filtros.tema && !temas.includes(filtros.tema) ? [filtros.tema, ...temas] : temas).map((t) => ({ valor: t, rotulo: t })),
            ]}
          />
        ) : (
          <CampoTexto rotulo="Tema (só do Congresso)" name="tema" defaultValue={filtros.tema} placeholder="Ex.: Saúde" />
        )}
        <CampoSelect
          rotulo="Ano do projeto"
          name="ano"
          defaultValue={filtros.ano}
          opcoes={[{ valor: "", rotulo: "Todos os anos" }, ...anosParaFiltro(new Date().getFullYear()).map((a) => ({ valor: String(a), rotulo: String(a) }))]}
        />
        <CampoSelect
          rotulo="Votação nominal (cada voto registrado)"
          name="votacao"
          defaultValue={filtros.votacao}
          opcoes={[
            { valor: "", rotulo: "Com ou sem votação" },
            { valor: "com", rotulo: "Teve votação nominal" },
            { valor: "sem", rotulo: "Não teve votação nominal" },
          ]}
        />
      </PainelFiltros>

      <PilulasAtivas itens={pilulas} limparHref={pilulas.length > 1 ? "/projetos" : undefined} />

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
  if (!filtrando) return <p className="text-muted-foreground">Ainda não há projetos carregados.</p>;
  return (
    <SemResultados
      mensagem={q ? `Nenhum projeto encontrado para "${q}".` : "Nenhum projeto com esses filtros."}
      limparHref="/projetos"
      rotuloLimpar={q ? "Limpar a busca e os filtros" : undefined}
    >
      <p className="text-sm">Confira o número (ex.: PL 2338/2023), tente uma palavra só do assunto ou tire um filtro acima. Algumas buscas:</p>
      <ul className="flex flex-wrap gap-2">
        {["saúde", "educação", "transporte", "segurança"].map((t) => (
          <li key={t}>
            <Link href={enderecoProjetos({}, { q: t })} className="botao-linha px-[var(--esp-4)]">
              {t}
            </Link>
          </li>
        ))}
      </ul>
    </SemResultados>
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
      {i.tipo === "proposicao" && v?.descricao && <p className="text-xs text-muted-foreground">Votação: {recortar(v.descricao, 140)}</p>}
    </Link>
  );
}

function LinkPagina({ href, ativo, children }: { href: string; ativo: boolean; children: React.ReactNode }) {
  if (!ativo) return <span aria-hidden className="invisible">{children}</span>;
  return (
    <Link href={href} className="alvo-link px-1 font-medium underline underline-offset-4">
      {children}
    </Link>
  );
}
