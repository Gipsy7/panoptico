"use client";

// Texto do painel lateral (folha de baixo no celular), por nível: Brasil, estado e cidade.

import Link from "next/link";
import { type ReactNode, useEffect, useState } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import type {
  DinheiroFederalEstado,
  DinheiroFederalFonte,
  DinheiroFederalMunicipio,
  DinheiroFederalPainel,
  DinheiroFederalTotais,
  DinheiroFederalUF,
} from "@/lib/api";

import { painelDoAno } from "./cache";
import {
  BLOCOS,
  arrHab,
  notaPopulacao,
  numero,
  percentual,
  por100,
  porHab,
  reais,
  reaisA100,
  repHab,
  textoSemDado,
} from "./formatos";
import { Barras, Figura, Secao } from "./pecas";

const Num = ({ children }: { children: ReactNode }) => (
  <b className="font-heading text-[1.2em] font-medium tabular-nums">{children}</b>
);

const FALTA =
  "aposentadorias e pensões do INSS, Bolsa Família e BPC (pagos direto às pessoas) e gastos da própria União no estado, como obras e salários de servidores federais";

function ComoLer() {
  return (
    <div className="flex flex-col gap-2 text-sm">
      <p>
        <b>Arrecadação</b> é o que pessoas e empresas pagaram de impostos e contribuições federais. A Receita registra
        o estado da sede de quem paga: empresa com sede em São Paulo paga lá, mesmo vendendo no país todo.
      </p>
      <p>
        <b>Repasse</b> é o dinheiro que a União passou ao governo do estado e às prefeituras: fundos de participação
        (FPE e FPM), parte federal do Fundeb, saúde, convênios e royalties.
      </p>
      <p>
        <b>Fica de fora:</b> {FALTA}. Ainda não há arquivo público com esses gastos por estado.
      </p>
    </div>
  );
}

export function Avisos({ avisos }: { avisos: string[] }) {
  if (!avisos.length) return null;
  return (
    <div className="flex flex-col gap-1.5 border-l-2 border-bronze pl-3 text-sm text-muted-foreground">
      {avisos.map((a) => (
        <p key={a}>{a}</p>
      ))}
    </div>
  );
}

export function Fontes({ fontes }: { fontes: DinheiroFederalFonte[] }) {
  return (
    <div className="flex flex-col gap-1.5">
      {fontes.map((f) => (
        <FonteRodape key={f.nome} fonte={f.nome} url={f.url} atualizadoEm={f.atualizado_em} />
      ))}
      <p className="text-sm text-muted-foreground">
        Valores em reais da época, sem correção pela inflação. <b>O que ficou de fora:</b> {FALTA}.
      </p>
    </div>
  );
}

function SemDado({ t, ano }: { t: DinheiroFederalTotais; ano: number }) {
  const texto = textoSemDado(t, ano);
  return texto ? <p className="text-sm text-muted-foreground">{texto}</p> : null;
}

function Blocos({ t }: { t: DinheiroFederalTotais }) {
  return (
    <>
      <Barras
        rotulo="De onde vem o repasse"
        itens={BLOCOS.filter((b) => t.blocos[b.chave] != null && t.blocos[b.chave] !== 0).map((b) => ({
          nome: b.nome,
          oficial: b.oficial,
          valor: t.blocos[b.chave],
          extra: reais(t.blocos[b.chave]),
        }))}
      />
    </>
  );
}

/** Cabeçalho do painel: o que fica visível com a folha recolhida (celular). */
export function CabecalhoPainel({
  sobre,
  titulo,
  chave,
  apoio,
}: {
  sobre: string;
  titulo: string;
  chave: ReactNode;
  apoio?: string;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-sm text-muted-foreground">{sobre}</span>
      <h2 className="text-[1.4rem] leading-tight lg:text-[1.75rem]">{titulo}</h2>
      <span className="text-sm text-muted-foreground tabular-nums lg:hidden [&_b]:font-semibold [&_b]:text-foreground">
        {chave}
      </span>
      {apoio && <span className="text-sm text-muted-foreground">{apoio}</span>}
    </div>
  );
}

export function CabecalhoBrasil({ painel }: { painel: DinheiroFederalPainel }) {
  const b = painel.brasil;
  return (
    <CabecalhoPainel
      sobre={`Brasil · ${painel.ano}`}
      titulo="Todos os estados"
      chave={
        <>
          Arrecadou <b>{reais(b.arrecadacao)}</b> · repassou <b>{reais(b.repasse)}</b>
        </>
      }
    />
  );
}

export function CorpoBrasil({ painel }: { painel: DinheiroFederalPainel }) {
  const b = painel.brasil;
  const nota = notaPopulacao(b, painel.ano);
  return (
    <>
      <p className="text-[17px] leading-normal">
        A União arrecadou <Num>{reais(b.arrecadacao)}</Num> no país em {painel.ano} e repassou{" "}
        <Num>{reais(b.repasse)}</Num> a governos de estado e prefeituras.
      </p>
      <Avisos avisos={painel.avisos} />
      <SemDado t={b} ano={painel.ano} />
      <div className="grid grid-cols-2 gap-3">
        <Figura rotulo="Arrecadação por habitante" valor={porHab(arrHab(b))} />
        <Figura rotulo="Repasse por habitante" valor={porHab(repHab(b))} />
      </div>
      {nota && <p className="text-sm text-muted-foreground">Por habitante: {nota}.</p>}
      {b.sem_estado != null && b.sem_estado > 0 && (
        <p className="text-sm text-muted-foreground">
          Inclui {reais(b.sem_estado)} sem estado definido na fonte (Portal da Transparência).
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        Toque ou clique num estado do mapa para ver o número dele e as cidades.
      </p>
      <Secao titulo="De onde vem o repasse">
        <Blocos t={b} />
      </Secao>
      <Secao titulo="Como ler estes números">
        <ComoLer />
      </Secao>
    </>
  );
}

export function CabecalhoEstado({ uf, ano }: { uf: DinheiroFederalUF; ano: number }) {
  return (
    <CabecalhoPainel
      sobre={`${uf.regiao} · ${ano}`}
      titulo={uf.nome}
      chave={
        <>
          Arrecadou <b>{reais(uf.arrecadacao)}</b> · repassou <b>{reais(uf.repasse)}</b>
        </>
      }
    />
  );
}

function SerieEstado({ uf, anos, ano }: { uf: string; anos: number[]; ano: number }) {
  const [linhas, setLinhas] = useState<{ ano: number; arrecadacao: number | null; repasse: number | null }[] | null>(
    null,
  );
  useEffect(() => {
    let vivo = true;
    Promise.all(anos.map((a) => painelDoAno(a))).then((rs) => {
      if (!vivo) return;
      setLinhas(
        anos.map((a, i) => {
          const r = rs[i];
          const u = r.ok ? r.dados.ufs.find((x) => x.uf === uf) : undefined;
          return { ano: a, arrecadacao: u?.arrecadacao ?? null, repasse: u?.repasse ?? null };
        }),
      );
    });
    return () => {
      vivo = false;
    };
  }, [uf, anos]);
  if (!linhas) return <p className="text-sm text-muted-foreground">Carregando os anos…</p>;
  const rot = (a: number) => (a === ano ? `${a} (ano mostrado)` : String(a));
  return (
    <>
      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">Arrecadação</p>
        <Barras
          rotulo="Arrecadação por ano"
          itens={linhas.map((l) => ({
            nome: rot(l.ano),
            valor: l.arrecadacao,
            extra: reais(l.arrecadacao),
            destaque: l.ano === ano,
          }))}
        />
      </div>
      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">Repasses</p>
        <Barras
          rotulo="Repasses por ano"
          itens={linhas.map((l) => ({
            nome: rot(l.ano),
            valor: l.repasse,
            extra: reais(l.repasse),
            destaque: l.ano === ano,
          }))}
        />
      </div>
      <p className="text-sm text-muted-foreground">
        Valores da época, sem correção pela inflação. O ano em curso soma só os meses já publicados.
      </p>
    </>
  );
}

export function CorpoEstado({
  uf,
  painel,
  estado,
  anos,
}: {
  uf: DinheiroFederalUF;
  painel: DinheiroFederalPainel;
  estado: DinheiroFederalEstado | null;
  anos: number[];
}) {
  const b = painel.brasil;
  const ano = painel.ano;
  const nota = notaPopulacao(uf, ano);
  const rep = repHab(uf);
  const mediaBr = repHab(b);
  return (
    <>
      <p className="text-[17px] leading-normal">
        A União arrecadou <Num>{reais(uf.arrecadacao)}</Num> aqui em {ano} e repassou <Num>{reais(uf.repasse)}</Num> ao
        governo do estado e às prefeituras: {reaisA100(por100(uf))} a cada R$ 100.
      </p>
      <Avisos avisos={painel.avisos} />
      <SemDado t={uf} ano={ano} />
      <div className="grid grid-cols-2 gap-3">
        <Figura rotulo="Repasse por habitante" valor={porHab(rep)} apoio={`Brasil: ${porHab(mediaBr)}`} />
        <Figura rotulo="Arrecadação por habitante" valor={porHab(arrHab(uf))} apoio={`Brasil: ${porHab(arrHab(b))}`} />
      </div>
      {rep != null && mediaBr != null && (
        <div className="flex flex-col gap-1">
          <BarraComparacao
            pessoa={{ rotulo: uf.nome, valor: rep }}
            media={{ rotulo: "Média do Brasil", valor: mediaBr }}
            formato="reais"
          />
          <p className="text-sm text-muted-foreground">Repasse por habitante{nota ? `; ${nota}` : ""}.</p>
        </div>
      )}
      {uf.uf === "DF" && (
        <p className="text-sm text-muted-foreground">
          A União também paga polícia, saúde e educação do DF por um fundo próprio (Fundo Constitucional do DF), que não
          entra nesta conta.
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        {estado
          ? `Toque ou clique numa das ${estado.cidades.length.toLocaleString("pt-BR")} cidades no mapa para ver quanto a prefeitura recebeu.`
          : "Carregando as cidades do estado…"}
      </p>
      <Secao titulo="De onde vem o repasse">
        <Blocos t={uf} />
      </Secao>
      <Secao titulo="Ano a ano" preguicosa>
        <SerieEstado uf={uf.uf} anos={anos} ano={ano} />
      </Secao>
      <Secao titulo="Como ler estes números">
        <ComoLer />
      </Secao>
      <div className="flex flex-col gap-2">
        <Link href={`/representantes?uf=${uf.uf}`} className="botao-linha">
          Quem representa o estado
        </Link>
        <Link href={`/parlamentares?uf=${uf.uf}`} className="botao-linha">
          Deputados e senadores
        </Link>
        <Link href={`/segundo-turno?uf=${uf.uf}`} className="botao-linha">
          Segundo turno no estado
        </Link>
      </div>
    </>
  );
}

export function CabecalhoCidade({
  nome,
  ufNome,
  ano,
  repasse,
  porMorador,
  populacao,
  nota,
}: {
  nome: string;
  ufNome: string;
  ano: number;
  repasse: number | null;
  porMorador: number | null;
  populacao: number | null;
  nota: string;
}) {
  return (
    <CabecalhoPainel
      sobre={`${ufNome} · ${ano}`}
      titulo={nome}
      chave={
        repasse == null ? (
          <>Sem repasses registrados em {ano}</>
        ) : (
          <>
            Recebeu <b>{reais(repasse)}</b> · <b>{porHab(porMorador)}</b> por morador
          </>
        )
      }
      apoio={populacao != null ? `${numero(populacao)} moradores${nota ? ` (${nota})` : ""}` : undefined}
    />
  );
}

function ContasPrefeitura({ mun }: { mun: DinheiroFederalMunicipio }) {
  const c = mun.contas;
  if (!c) {
    return (
      <p className="text-sm text-muted-foreground">Não há balanço anual da prefeitura na fonte (Tesouro Nacional).</p>
    );
  }
  return (
    <>
      <Barras
        rotulo={`Contas da prefeitura em ${c.ano}`}
        itens={[
          { nome: "Receita total", valor: c.receita_total, extra: reais(c.receita_total), destaque: true },
          {
            nome: "Veio da União",
            oficial: c.parte_uniao != null ? `${percentual(c.parte_uniao)} da receita` : undefined,
            valor: c.transf_uniao,
            extra: reais(c.transf_uniao),
          },
          {
            nome: "Impostos da própria cidade",
            oficial: `IPTU, ISS e taxas${c.parte_propria != null ? ` · ${percentual(c.parte_propria)} da receita` : ""}`,
            valor: c.receita_propria,
            extra: reais(c.receita_propria),
          },
        ]}
      />
      <p className="text-sm text-muted-foreground">
        O resto vem do estado (ICMS, IPVA) e de outras receitas. Balanço de {c.ano}, o mais recente disponível.
      </p>
    </>
  );
}

export function CorpoCidade({
  ibge,
  uf,
  ano,
  mun,
  populacaoNota,
}: {
  ibge: string;
  uf: string;
  ano: number;
  mun: DinheiroFederalMunicipio;
  populacaoNota: string;
}) {
  const s = mun.serie.find((x) => x.ano === ano);
  return (
    <>
      {s ? (
        <>
          <p className="text-[17px] leading-normal">
            A União repassou <Num>{reais(s.repasse)}</Num> à prefeitura em {ano}
            {s.por_habitante != null && (
              <>
                : <Num>{porHab(s.por_habitante)}</Num> por morador
              </>
            )}
            .
          </p>
          {s.por_habitante != null && s.media_estado_por_habitante != null && (
            <div className="flex flex-col gap-1">
              <BarraComparacao
                pessoa={{ rotulo: mun.municipio.nome, valor: s.por_habitante }}
                media={{ rotulo: `Média das cidades de ${uf}`, valor: s.media_estado_por_habitante }}
                formato="reais"
              />
              <p className="text-sm text-muted-foreground">
                Repasse por morador{populacaoNota ? `; ${populacaoNota}` : ""}.
              </p>
            </div>
          )}
          <Secao titulo="De onde vem o repasse">
            <Barras
              rotulo="De onde vem o repasse"
              itens={[
                {
                  nome: "Fundo das prefeituras",
                  oficial: "FPM, Fundo de Participação dos Municípios",
                  valor: s.fpm,
                  extra: reais(s.fpm),
                },
                {
                  nome: "Saúde, convênios e outros repasses",
                  oficial: "Transferências legais, voluntárias e específicas",
                  valor: s.outros,
                  extra: reais(s.outros),
                },
              ].filter((i) => i.valor)}
            />
          </Secao>
        </>
      ) : (
        <p className="text-[17px] leading-normal">Não há repasses registrados para esta cidade em {ano}.</p>
      )}
      <Secao titulo={`Contas da prefeitura${mun.contas ? ` em ${mun.contas.ano}` : ""}`}>
        <ContasPrefeitura mun={mun} />
      </Secao>
      <Secao titulo="Ano a ano">
        <Barras
          rotulo="Repasses à prefeitura por ano"
          itens={mun.serie.map((x) => ({
            nome: x.ano === ano ? `${x.ano} (ano mostrado)` : String(x.ano),
            valor: x.repasse,
            extra: reais(x.repasse),
            destaque: x.ano === ano,
            oficial:
              x.por_habitante != null
                ? `${porHab(x.por_habitante)} por morador${x.media_estado_por_habitante != null ? ` · média do estado ${porHab(x.media_estado_por_habitante)}` : ""}`
                : undefined,
          }))}
        />
        <p className="text-sm text-muted-foreground">Valores da época, sem correção pela inflação.</p>
      </Secao>
      <p className="text-sm text-muted-foreground">
        A Receita Federal não publica arrecadação por cidade; por isso aqui só aparece o que a União mandou.
      </p>
      <div className="flex flex-col gap-2">
        <Link href={`/cidade/${ibge}`} className="botao-linha">
          Para onde foi o dinheiro da cidade
        </Link>
        <Link href={`/representantes?municipio=${ibge}`} className="botao-linha">
          Quem representa a cidade
        </Link>
        <Link href={`/cidade/${ibge}#emendas-titulo`} className="botao-linha">
          Emendas de deputados e senadores
        </Link>
      </div>
    </>
  );
}
