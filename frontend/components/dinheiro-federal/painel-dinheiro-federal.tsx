"use client";

// Painel de dinheiro federal: mapa Brasil > estado > cidade, barra de ferramentas e painel
// lateral (folha de baixo no celular). O lugar e o ano vivem neste componente e a URL acompanha
// por history.pushState; assim a navegação é suave e o link continua compartilhável.

import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";

import { MapaBrasil, type MapaControle } from "@/components/mapa/mapa-brasil";
import estilosMapa from "@/components/mapa/mapa-brasil.module.css";
import { Migalhas } from "@/components/ui/migalhas";
import type {
  DinheiroFederalCidade,
  DinheiroFederalEstado,
  DinheiroFederalMunicipio,
  DinheiroFederalPainel,
  DinheiroFederalUF,
} from "@/lib/api";
import { type ClasseMapa, type Lugar, type NivelMapa, classe, quantis } from "@/lib/mapa";

import { BuscaCidade } from "./busca-cidade";
import { estadoDoAno, municipioPorIbge, painelDoAno, semear } from "./cache";
import {
  Avisos,
  CabecalhoBrasil,
  CabecalhoCidade,
  CabecalhoEstado,
  CabecalhoPainel,
  CorpoBrasil,
  CorpoCidade,
  CorpoEstado,
  Fontes,
} from "./conteudo-painel";
import {
  ANO_PADRAO,
  type Indicador,
  NOME_INDICADOR,
  formatarIndicador,
  notaPopulacao,
  numero,
  porHab,
  reais,
  reaisA100,
  repHab,
  rotuloAno,
  valorIndicador,
} from "./formatos";
import { type LinhaLista, ListaLugares } from "./lista-lugares";
import estilos from "./painel-dinheiro-federal.module.css";
import { Secao } from "./pecas";

export type EstadoInicial = {
  uf: string | null;
  ibge: string | null;
  ano: number;
  painel: DinheiroFederalPainel;
  estado: DinheiroFederalEstado | null;
  municipio: DinheiroFederalMunicipio | null;
};

const INDICADORES = Object.keys(NOME_INDICADOR) as Indicador[];

function urlDe(uf: string | null, ibge: string | null, ano: number) {
  return `/dinheiro-federal${uf ? `/${uf}` : ""}${uf && ibge ? `/${ibge}` : ""}${ano !== ANO_PADRAO ? `?ano=${ano}` : ""}`;
}

/** Lê /dinheiro-federal/SC/4205407?ano=2024 da barra de endereço (botão voltar do navegador). */
function lerEndereco() {
  const partes = location.pathname.split("/").filter(Boolean).slice(1);
  const ano = Number(new URLSearchParams(location.search).get("ano"));
  return {
    uf: partes[0] ? partes[0].toUpperCase() : null,
    ibge: partes[0] && partes[1] ? partes[1] : null,
    ano: Number.isInteger(ano) && ano > 2000 ? ano : ANO_PADRAO,
  };
}

const valorCidade = (c: DinheiroFederalCidade | undefined) =>
  c && c.repasse != null && c.populacao ? c.repasse / c.populacao : null;

export function PainelDinheiroFederal({ inicial }: { inicial: EstadoInicial }) {
  const [uf, setUf] = useState(inicial.uf);
  const [ibge, setIbge] = useState(inicial.ibge);
  const [ano, setAno] = useState(inicial.ano);
  const [ind, setInd] = useState<Indicador>("repHab");
  const [vista, setVista] = useState<"mapa" | "lista">("mapa");
  const [aberta, setAberta] = useState(false);
  const [painel, setPainel] = useState(inicial.painel);
  const [estado, setEstado] = useState(inicial.estado);
  const [municipio, setMunicipio] = useState(inicial.municipio);
  const [erro, setErro] = useState<string | null>(null);

  const raizRef = useRef<HTMLDivElement>(null);
  const topoFolhaRef = useRef<HTMLDivElement>(null);
  const controle = useRef<MapaControle>(null);

  // Veio outra renderização do servidor (ex.: botão voltar): acompanha o endereço novo.
  const chaveInicial = `${inicial.uf}|${inicial.ibge}|${inicial.ano}`;
  const [chaveVista, setChaveVista] = useState(chaveInicial);
  if (chaveVista !== chaveInicial) {
    setChaveVista(chaveInicial);
    setUf(inicial.uf);
    setIbge(inicial.ibge);
    setAno(inicial.ano);
    setPainel(inicial.painel);
    setEstado(inicial.estado);
    setMunicipio(inicial.municipio);
  }

  useEffect(() => {
    semear(inicial.painel, inicial.estado, inicial.municipio);
  }, [inicial]);

  useEffect(() => {
    const aoVoltar = () => {
      const e = lerEndereco();
      setUf(e.uf);
      setIbge(e.ibge);
      setAno(e.ano);
      setAberta(false);
    };
    addEventListener("popstate", aoVoltar);
    return () => removeEventListener("popstate", aoVoltar);
  }, []);

  // Marca a página como "tela de app" (celular sem rolagem) enquanto ela está aberta.
  useEffect(() => {
    document.documentElement.dataset.appMapa = "1";
    return () => {
      delete document.documentElement.dataset.appMapa;
    };
  }, []);

  // ---- carga sob demanda (cache em memória) ----
  useEffect(() => {
    if (painel.ano === ano) return;
    let vivo = true;
    painelDoAno(ano).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setPainel(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [ano, painel.ano]);

  useEffect(() => {
    if (!uf || (estado?.uf === uf && estado.ano === ano)) return;
    let vivo = true;
    estadoDoAno(uf, ano).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setEstado(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [uf, ano, estado]);

  useEffect(() => {
    if (!ibge || municipio?.municipio.ibge === ibge) return;
    let vivo = true;
    municipioPorIbge(ibge).then((r) => {
      if (!vivo) return;
      if (r.ok) {
        setMunicipio(r.dados);
        setErro(null);
      } else setErro(r.mensagem);
    });
    return () => {
      vivo = false;
    };
  }, [ibge, municipio]);

  // ---- navegação ----
  const navegar = useCallback(
    (lugar: Lugar) => {
      const novoUf = lugar.uf ?? null;
      const novoIbge = novoUf ? (lugar.municipio ?? null) : null;
      setUf(novoUf);
      setIbge(novoIbge);
      setAberta(false);
      setErro(null);
      history.pushState(null, "", urlDe(novoUf, novoIbge, ano));
    },
    [ano],
  );

  function trocarAno(novo: number) {
    setAno(novo);
    history.replaceState(null, "", urlDe(uf, ibge, novo));
  }

  // ---- dados derivados ----
  const anoMostrado = painel.ano;
  const ufLinha: DinheiroFederalUF | null = uf ? (painel.ufs.find((u) => u.uf === uf) ?? null) : null;
  const estadoOk = estado && estado.uf === uf && estado.ano === anoMostrado ? estado : null;
  const cidades = useMemo(() => estadoOk?.cidades ?? [], [estadoOk]);
  const porIbge = useMemo(() => new Map(cidades.map((c) => [c.ibge, c])), [cidades]);
  const mediaBrasil = repHab(painel.brasil);

  // Dentro do estado só existe repasse por habitante (a Receita não publica arrecadação por cidade).
  const cortesUf = useMemo(() => quantis(painel.ufs.map((u) => valorIndicador(u, ind))), [painel, ind]);
  const cortesMun = useMemo(() => quantis(cidades.map(valorCidade)), [cidades]);

  const classeMapa = (nivel: NivelMapa, id: string): ClasseMapa => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      return u ? classe(valorIndicador(u, ind), cortesUf) : 0;
    }
    return classe(valorCidade(porIbge.get(id)), cortesMun);
  };

  const rotuloMapa = (nivel: NivelMapa, id: string) => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      return u
        ? `${u.nome}: a União arrecadou ${reais(u.arrecadacao)} e repassou ${reais(u.repasse)} em ${anoMostrado}`
        : id;
    }
    const c = porIbge.get(id);
    return c ? `${c.nome}: a União repassou ${reais(c.repasse)} à prefeitura em ${anoMostrado}` : id;
  };

  const resumoMapa = (nivel: NivelMapa, id: string) => {
    if (nivel === "uf") {
      const u = painel.ufs.find((x) => x.uf === id);
      if (!u) return id;
      return (
        <div className="flex flex-col gap-0.5 text-sm">
          <strong>{u.nome}</strong>
          <span>Arrecadou {reais(u.arrecadacao)}</span>
          <span>Repassou {reais(u.repasse)}</span>
          <span>A cada R$ 100: {reaisA100(valorIndicador(u, "por100"))}</span>
          <span>Por habitante: {porHab(repHab(u))}</span>
          <span>Média do Brasil: {porHab(mediaBrasil)}</span>
        </div>
      );
    }
    const c = porIbge.get(id);
    if (!c) return id;
    return (
      <div className="flex flex-col gap-0.5 text-sm">
        <strong>{c.nome}</strong>
        <span>Repasse à prefeitura: {reais(c.repasse)}</span>
        <span>Por morador: {porHab(valorCidade(c))}</span>
        <span>Média do estado: {porHab(estadoOk?.media_estado_por_habitante)}</span>
        <span>Moradores: {numero(c.populacao)}</span>
      </div>
    );
  };

  // ---- legenda ----
  const nivelMun = Boolean(uf);
  const indEfetivo: Indicador = nivelMun ? "repHab" : ind;
  const valoresLegenda = (
    nivelMun ? cidades.map(valorCidade) : painel.ufs.map((u) => valorIndicador(u, indEfetivo))
  ).filter((v): v is number => v != null);
  const cortesLegenda = nivelMun ? cortesMun : cortesUf;
  const minimo = valoresLegenda.length ? Math.min(...valoresLegenda) : null;
  const maximo = valoresLegenda.length ? Math.max(...valoresLegenda) : null;
  const rotulosLegenda = [minimo, cortesLegenda[1] ?? null, cortesLegenda[3] ?? null, maximo]
    .map((v) => formatarIndicador(indEfetivo, v))
    .filter((t, i, todos) => i === 0 || t !== todos[i - 1]);
  const valorUnico = rotulosLegenda.length === 1;
  const cidadesComValor = cidades.filter((c) => valorCidade(c) != null);
  const nomeUnico = nivelMun && cidadesComValor.length === 1 ? cidadesComValor[0].nome : null;
  const unidadeLegenda = indEfetivo === "por100" ? "a cada R$ 100" : "por habitante";

  // ---- lista ----
  const linhas: LinhaLista[] = nivelMun
    ? cidades.map((c) => ({ id: c.ibge, nome: c.nome, c1: c.populacao, c2: c.repasse, c3: valorCidade(c), c4: null }))
    : painel.ufs.map((u) => ({
        id: u.uf,
        nome: u.nome,
        c1: u.arrecadacao,
        c2: u.repasse,
        c3: repHab(u),
        c4: valorIndicador(u, "por100"),
      }));

  // ---- painel ----
  const munOk = municipio && municipio.municipio.ibge === ibge ? municipio : null;
  const ufNome = ufLinha?.nome ?? uf ?? "";
  const nomeCidade = munOk?.municipio.nome ?? (ibge ? porIbge.get(ibge)?.nome : undefined) ?? "Cidade";
  const serieAno = munOk?.serie.find((s) => s.ano === anoMostrado);
  const notaPop = ufLinha ? notaPopulacao(ufLinha, anoMostrado) : "";
  const anos = painel.anos_disponiveis;
  const fontes = ibge && munOk ? munOk.fontes : (estadoOk?.fontes ?? painel.fontes);
  const carregando = painel.ano !== ano || (Boolean(uf) && !estadoOk) || (Boolean(ibge) && !munOk);
  const avisoAnoEmCurso = painel.avisos.filter((a) => a.startsWith("Ano em curso"));

  // Altura da parte sempre visível da folha (celular): alça + cabeçalho.
  const chaveCabecalho = `${uf}|${ibge}|${anoMostrado}|${Boolean(munOk)}`;
  useLayoutEffect(() => {
    const topo = topoFolhaRef.current;
    const raiz = raizRef.current;
    if (!topo || !raiz) return;
    const medir = () => raiz.style.setProperty("--espia", `${Math.min(topo.offsetHeight + 20, 280)}px`);
    medir();
    const ro = new ResizeObserver(medir);
    ro.observe(topo);
    return () => ro.disconnect();
  }, [chaveCabecalho]);

  // Voltando para a aba Mapa, reenquadra (o mapa escondido não tem tamanho).
  useEffect(() => {
    if (vista !== "mapa") return;
    const id = requestAnimationFrame(() => controle.current?.reenquadrar());
    return () => cancelAnimationFrame(id);
  }, [vista]);

  const migalhas = [
    { rotulo: "Início", href: "/" },
    { rotulo: "Dinheiro federal" },
  ];

  let cabecalho;
  let corpo;
  if (ibge) {
    cabecalho = (
      <CabecalhoCidade
        nome={nomeCidade}
        ufNome={ufNome}
        ano={anoMostrado}
        repasse={serieAno?.repasse ?? null}
        porMorador={serieAno?.por_habitante ?? null}
        populacao={serieAno?.populacao ?? porIbge.get(ibge)?.populacao ?? null}
        nota={notaPop}
      />
    );
    corpo = munOk ? (
      <>
        <Avisos avisos={avisoAnoEmCurso} />
        <CorpoCidade ibge={ibge} uf={uf ?? ""} ano={anoMostrado} mun={munOk} populacaoNota={notaPop} />
      </>
    ) : (
      <p className="text-sm text-muted-foreground">Carregando os repasses da cidade…</p>
    );
  } else if (uf && ufLinha) {
    cabecalho = <CabecalhoEstado uf={ufLinha} ano={anoMostrado} />;
    corpo = <CorpoEstado uf={ufLinha} painel={painel} estado={estadoOk} anos={anos} />;
  } else {
    cabecalho = <CabecalhoBrasil painel={painel} />;
    corpo = <CorpoBrasil painel={painel} />;
  }
  if (!cabecalho) cabecalho = <CabecalhoPainel sobre="Brasil" titulo="Todos os estados" chave="" />;

  const resumoOnde = (
    <>
      <button
        type="button"
        className={estilos.voltar}
        onClick={() => navegar(ibge ? { uf: uf ?? undefined } : {})}
      >
        <span aria-hidden>‹</span> {ibge ? ufNome : "Brasil"}
      </button>
      <span className={estilos.onde}>
        {ibge ? (
          <>
            {ufNome} › <b>{nomeCidade}</b>
          </>
        ) : (
          <b>{ufNome}</b>
        )}
      </span>
    </>
  );

  const tituloMapa = uf
    ? `Mapa das cidades de ${ufNome}, colorido pelo repasse da União por habitante`
    : `Mapa do Brasil por estado, colorido por: ${NOME_INDICADOR[ind].toLowerCase()}`;

  return (
    <div ref={raizRef} data-largura="larga" data-app-mapa className={estilos.raiz}>
      <header className={estilos.topo}>
        <Migalhas itens={migalhas} />
        <h1 className={`${estilos.h1} font-heading`}>
          <span className={estilos.longo}>Quanto a União arrecada e quanto repassa em cada estado</span>
          <span className={estilos.curto}>Imposto federal: o que sai e o que volta</span>
        </h1>
      </header>

      <div className={estilos.barra}>
        <div className={estilos.abas} role="tablist" aria-label="Forma de ver">
          <button type="button" role="tab" aria-selected={vista === "mapa"} onClick={() => setVista("mapa")}>
            Mapa
          </button>
          <button type="button" role="tab" aria-selected={vista === "lista"} onClick={() => setVista("lista")}>
            Lista
          </button>
        </div>
        <div className={estilos.chips} role="group" aria-label="O que as cores mostram">
          {INDICADORES.map((k) => (
            <button key={k} type="button" aria-pressed={ind === k} onClick={() => setInd(k)}>
              {NOME_INDICADOR[k]}
            </button>
          ))}
        </div>
        <label className={estilos.indCel}>
          <span>Cores:</span>
          <select
            className={estilos.seletor}
            aria-label="O que as cores mostram"
            value={ind}
            onChange={(e) => setInd(e.target.value as Indicador)}
          >
            {INDICADORES.map((k) => (
              <option key={k} value={k}>
                {NOME_INDICADOR[k]}
              </option>
            ))}
          </select>
        </label>
        <select
          className={estilos.seletor}
          aria-label="Ano"
          value={ano}
          onChange={(e) => trocarAno(Number(e.target.value))}
        >
          {[...anos].reverse().map((a) => (
            <option key={a} value={a}>
              {rotuloAno(a, a === anos[anos.length - 1] && painel.ano_em_curso)}
            </option>
          ))}
        </select>
        <BuscaCidade
          classe={estilos.busca}
          onEscolher={(u, i) => {
            setVista("mapa");
            navegar({ uf: u, municipio: i });
          }}
        />
      </div>

      <div className={estilos.grade} aria-busy={carregando}>
        <div className={estilos.palco}>
          <div className={estilos.mapaCaixa} hidden={vista !== "mapa"}>
            <div className={estilos.mapaInterno}>
              <MapaBrasil
                niveis="municipio"
                uf={uf ?? undefined}
                municipio={ibge ?? undefined}
                onNavegar={navegar}
                classe={classeMapa}
                rotulo={rotuloMapa}
                resumo={resumoMapa}
                controle={controle}
                titulo={tituloMapa}
                className="h-full w-full"
              />
            </div>
            {uf && <div className={estilos.sobre}>{resumoOnde}</div>}
            {uf && !ibge && (
              <div className={estilos.zoom}>
                <button type="button" aria-label="Aproximar" onClick={() => controle.current?.zoom(1.5)}>
                  +
                </button>
                <button type="button" aria-label="Afastar" onClick={() => controle.current?.zoom(1 / 1.5)}>
                  −
                </button>
              </div>
            )}
          </div>
          <div className={`${estilosMapa.caixa} ${estilos.legenda}`} hidden={vista !== "mapa" || Boolean(ibge)}>
            {valoresLegenda.length > 0 && minimo != null && maximo != null ? (
              <>
                <span>
                  {NOME_INDICADOR[indEfetivo]}, {anoMostrado}
                  {nivelMun ? `, cidades de ${ufNome}` : ""}
                </span>
                {valorUnico ? (
                  <>
                    <div className={estilos.faixa} aria-hidden style={{ gridTemplateColumns: "1fr" }}>
                      <i style={{ background: "var(--mapa-3)" }} />
                    </div>
                    <div className={estilos.rotulos}>
                      <span>
                        {`${nomeUnico ?? (nivelMun ? "Todas as cidades" : "Todos os estados")}: `}
                        {rotulosLegenda[0]} {unidadeLegenda}
                      </span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className={estilos.faixa} aria-hidden>
                      {[1, 2, 3, 4, 5].map((i) => (
                        <i key={i} style={{ background: `var(--mapa-${i})` }} />
                      ))}
                    </div>
                    <div className={estilos.rotulos}>
                      {rotulosLegenda.map((t, i) => (
                        <span key={`${i}-${t}`}>{t}</span>
                      ))}
                    </div>
                  </>
                )}
                <span className={estilos.legendaTexto}>
                  {valorUnico ? "" : `Cada cor reúne um quinto dos ${nivelMun ? "municípios" : "estados"}. `}Cinza: sem dado.
                  {nivelMun && ind !== "repHab"
                    ? " Nas cidades o mapa mostra o repasse por habitante: a Receita Federal não publica arrecadação por cidade."
                    : ""}
                </span>
              </>
            ) : (
              <span>
                {nivelMun && !estadoOk ? "Carregando as cidades…" : `Sem dado de ${NOME_INDICADOR[indEfetivo].toLowerCase()} em ${anoMostrado}.`}
              </span>
            )}
          </div>
          {vista === "lista" && (
            <ListaLugares
              nivel={nivelMun ? "mun" : "uf"}
              linhas={linhas}
              legenda={
                nivelMun
                  ? `As ${linhas.length.toLocaleString("pt-BR")} cidades de ${ufNome}, ${anoMostrado}.`
                  : `Os ${linhas.length} estados, ${anoMostrado}.`
              }
              onEscolher={(id) => {
                setVista("mapa");
                navegar(nivelMun && uf ? { uf, municipio: id } : { uf: id });
              }}
            />
          )}
        </div>

        <aside
          className={`${estilos.painel} ${aberta ? estilos.aberta : ""}`}
          aria-label="Números do lugar escolhido"
          aria-live="polite"
        >
          <div ref={topoFolhaRef}>
            <button
              type="button"
              className={estilos.alca}
              aria-expanded={aberta}
              aria-controls="corpo-painel-dinheiro"
              onClick={() => setAberta((a) => !a)}
            >
              <i />
              <span>{aberta ? "Fechar" : "Puxe para ver mais"}</span>
            </button>
            <div className={estilos.cabFolha}>{cabecalho}</div>
          </div>
          <div id="corpo-painel-dinheiro" className={estilos.corpo}>
            {erro && (
              <p role="alert" className="text-sm text-muted-foreground">
                Não foi possível carregar esses números agora: {erro}
              </p>
            )}
            {corpo}
            <div className={estilos.soMobile}>
              <Secao titulo="Fontes e notas">
                <Fontes fontes={fontes} />
              </Secao>
            </div>
          </div>
        </aside>
      </div>

      <footer className={`${estilos.soDesk} max-w-3xl`}>
        <Fontes fontes={fontes} />
      </footer>
    </div>
  );
}
