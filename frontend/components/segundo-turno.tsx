/**
 * Comparador do 2º turno: os candidatos de cada disputa lado a lado, com os MESMOS campos.
 * Neutralidade: ordem pelo número na urna (vem assim da API), as duas colunas com o mesmo
 * estilo, nenhuma cor por partido, nenhum destaque para quem teve mais votos. O que falta
 * aparece escrito ("não informado pela fonte"), nunca como zero.
 */
import Link from "next/link";
import type { ReactNode } from "react";

import { Iniciais } from "@/components/eleitos-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { type CandidatoSegundoTurno, type DisputaSegundoTurno, type SegundoTurno, legendaFoto, urlFotoDe } from "@/lib/api";
import { formatarData, formatarReais, formatarReaisCompacto } from "@/lib/formato";
import { LinkExterno } from "@/components/link-externo";

const NAO_INFORMADO = "não informado pela fonte";
const NAO_IDENTIFICADO = "não identificado na base";
const INTEIRO = new Intl.NumberFormat("pt-BR");

/** "domingo, 25 de outubro" a partir de "2026-10-25" (sem fuso: a data é civil). */
export function dataPorExtenso(iso: string): string {
  const [ano, mes, dia] = iso.split("-").map(Number);
  return new Date(Date.UTC(ano, mes - 1, dia)).toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "UTC",
  });
}

const ESTADOS_DO = new Set([
  "Acre", "Amapá", "Amazonas", "Ceará", "Distrito Federal", "Espírito Santo", "Maranhão", "Mato Grosso",
  "Mato Grosso do Sul", "Pará", "Paraná", "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul",
  "Tocantins",
]);
const ESTADOS_DA = new Set(["Bahia", "Paraíba"]);

/** "do Tocantins", "da Bahia", "de São Paulo". */
export function deEstado(nome: string): string {
  return `${ESTADOS_DO.has(nome) ? "do" : ESTADOS_DA.has(nome) ? "da" : "de"} ${nome}`;
}

/** "no Tocantins", "na Bahia", "em São Paulo". */
export function emEstado(nome: string): string {
  return `${ESTADOS_DO.has(nome) ? "no" : ESTADOS_DA.has(nome) ? "na" : "em"} ${nome}`;
}

export function tituloDisputa(d: DisputaSegundoTurno): string {
  return d.chave === "presidente" ? "Presidente da República" : `Governador ${deEstado(d.unidade)}`;
}

function Foto({
  c,
  tamanho,
}: {
  c: { id: number; nome_urna: string; foto: boolean; foto_de?: number | null; foto_ano?: number | null; foto_url?: string | null };
  tamanho: number;
}) {
  const src = c.foto ? urlFotoDe(c) : (c.foto_url ?? null);
  if (!src) return <Iniciais nome={c.nome_urna} tamanho={tamanho} />;
  const legenda = c.foto ? legendaFoto(c) : null;
  return (
    <span className="flex shrink-0 flex-col items-center gap-0.5">
      {/* eslint-disable-next-line @next/next/no-img-element -- foto do TSE ou da Casa, já pequena */}
      <img
        src={src}
        alt={`Foto de ${c.nome_urna}`}
        width={tamanho}
        height={Math.round((tamanho * 4) / 3)}
        loading="lazy"
        className="shrink-0 rounded-[2px] bg-muted object-cover"
        style={{ width: tamanho, height: Math.round((tamanho * 4) / 3) }}
      />
      {legenda && <span className="text-[0.7rem] leading-none text-muted-foreground">{legenda}</span>}
    </span>
  );
}

function Faltando() {
  return <span className="text-sm leading-snug text-muted-foreground">{NAO_INFORMADO}</span>;
}

/** Uma linha de comparação: o rótulo ocupa a largura toda e os valores ficam lado a lado. */
function Linha({
  rotulo,
  detalhe,
  valores,
}: {
  rotulo: string;
  detalhe?: string;
  valores: ReactNode[];
}) {
  return (
    <div className="border-b border-border py-3">
      <dt className="text-sm text-muted-foreground">
        {rotulo}
        {detalhe && <span className="block text-[13px]">{detalhe}</span>}
      </dt>
      <div className="mt-1 grid grid-cols-2 gap-3 sm:gap-6">
        {valores.map((v, i) => (
          <dd key={i} className="flex min-w-0 flex-col gap-0.5 break-words">
            {v}
          </dd>
        ))}
      </div>
    </div>
  );
}

function Numero({ valor, apoio }: { valor: string; apoio?: string | null }) {
  return (
    <>
      <span className="numero text-xl leading-tight">{valor}</span>
      {apoio && <span className="text-[13px] leading-snug text-muted-foreground tabular-nums">{apoio}</span>}
    </>
  );
}

function valorVotos(c: CandidatoSegundoTurno) {
  return c.votos_1turno == null ? <Faltando /> : <Numero valor={INTEIRO.format(c.votos_1turno)} apoio="votos válidos" />;
}

function valorVotos2(c: CandidatoSegundoTurno) {
  return c.votos_2turno == null ? <Faltando /> : <Numero valor={INTEIRO.format(c.votos_2turno)} apoio="votos válidos" />;
}

function valorBens(c: CandidatoSegundoTurno) {
  if (!c.bens) return <Faltando />;
  const a = c.bens.anterior;
  return (
    <Numero
      valor={formatarReaisCompacto(c.bens.total)}
      apoio={a && a.total != null ? `Em ${a.ano}: ${formatarReaisCompacto(a.total)}` : "Sem declaração anterior na base"}
    />
  );
}

function valorCampanha(c: CandidatoSegundoTurno) {
  if (!c.campanha) return <Faltando />;
  return (
    <Numero
      valor={formatarReaisCompacto(c.campanha.receitas_total)}
      apoio={`Gastou ${formatarReaisCompacto(c.campanha.despesas_total)}`}
    />
  );
}

function valorCarreira(c: CandidatoSegundoTurno) {
  if (c.carreira === null) return <span className="text-sm leading-snug text-muted-foreground">{NAO_IDENTIFICADO}</span>;
  const eleito = c.carreira.filter((x) => x.eleito).length;
  if (c.carreira.length === 0) return <Numero valor="Nenhuma" apoio="na base do TSE" />;
  return (
    <Numero
      valor={String(c.carreira.length)}
      apoio={eleito === 0 ? "Não foi eleito(a) nelas" : `Eleito(a) em ${eleito}`}
    />
  );
}

function valorSancoes(c: CandidatoSegundoTurno) {
  if (c.sancoes === null) return <span className="text-sm leading-snug text-muted-foreground">{NAO_IDENTIFICADO}</span>;
  return <Numero valor={c.sancoes.length === 0 ? "Nenhum" : String(c.sancoes.length)} apoio={c.sancoes.length === 1 ? "registro" : c.sancoes.length > 1 ? "registros" : null} />;
}

function valorVice(c: CandidatoSegundoTurno) {
  if (!c.vice) return <Faltando />;
  return (
    <>
      <span className="text-sm font-medium leading-snug">{c.vice.nome_urna}</span>
      {c.vice.partido && <span className="text-[13px] text-muted-foreground">{c.vice.partido}</span>}
    </>
  );
}

/** Cabeçalho de cada lado: foto, nome de urna, número e partido. Mesmo estilo nos dois. */
function Cabecalho({ c }: { c: CandidatoSegundoTurno }) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <Foto c={c} tamanho={72} />
      <p className="text-base font-semibold leading-tight break-words">{c.nome_urna}</p>
      <p className="flex flex-wrap gap-1">
        {c.numero && <span className="pilula tabular-nums">Número {c.numero}</span>}
        {c.partido && <span className="pilula">{c.partido}</span>}
      </p>
      {c.eleito !== null && (
        <p className="text-sm font-medium">{c.eleito ? "Eleito(a) no 2º turno" : "Não eleito(a)"}</p>
      )}
    </div>
  );
}

function Lacuna({ faltam }: { faltam: number }) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <span aria-hidden className="block h-24 w-[72px] rounded-[2px] border border-dashed border-border" />
      <p className="text-sm leading-snug text-muted-foreground">
        {faltam === 2 ? "Dados dos candidatos" : "Dados do outro candidato"} ainda não carregados.
      </p>
    </div>
  );
}

/** Duas colunas sempre: se a base ainda não tem um dos candidatos, a coluna dele avisa. */
function colunas<T>(d: DisputaSegundoTurno, f: (c: CandidatoSegundoTurno) => T, vazio: T): T[] {
  const valores = d.candidatos.map(f);
  while (valores.length < 2) valores.push(vazio);
  return valores;
}

export function DisputaLadoALado({ d, dados }: { d: DisputaSegundoTurno; dados: SegundoTurno }) {
  const id = `disputa-${d.chave}`;
  const traco = <span className="text-sm text-muted-foreground">—</span>;
  const ano = dados.ano_eleicao ?? "";
  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <p className="sobretitulo">
          {d.decidida ? "Resultado do 2º turno" : "2º turno"}
          {dados.data_segundo_turno ? ` · ${formatarData(dados.data_segundo_turno)}` : ""}
        </p>
        <h2 id={id} className="text-[1.625rem] leading-tight">
          {tituloDisputa(d)}
        </h2>
      </div>

      <div className="rounded-[2px] border border-border bg-card">
        <div className="grid grid-cols-2 gap-3 border-b border-foreground p-4 sm:gap-6 sm:p-5">
          {d.candidatos.map((c) => (
            <Cabecalho key={c.id} c={c} />
          ))}
          {d.faltam > 0 && d.candidatos.length < 2 && <Lacuna faltam={d.faltam} />}
        </div>
        <dl className="flex flex-col px-4 sm:px-5">
          <Linha rotulo="Vice na chapa" valores={colunas(d, valorVice, traco)} />
          {d.decidida ? (
            <Linha rotulo="Votos no 2º turno" valores={colunas(d, valorVotos2, traco)} />
          ) : (
            <Linha rotulo="Votos no 1º turno" valores={colunas(d, valorVotos, traco)} />
          )}
          <Linha rotulo={`Bens declarados em ${ano}`} detalhe="Patrimônio informado ao TSE" valores={colunas(d, valorBens, traco)} />
          <Linha
            rotulo="Dinheiro arrecadado na campanha"
            detalhe="Prestação de contas do 1º turno"
            valores={colunas(d, valorCampanha, traco)}
          />
          <Linha rotulo="Eleições que disputou antes" valores={colunas(d, valorCarreira, traco)} />
          <Linha
            rotulo="Registros na CGU e no TCU"
            detalhe="Sanções e contas julgadas irregulares"
            valores={colunas(d, valorSancoes, traco)}
          />
        </dl>
        <div className="grid grid-cols-2 gap-3 p-4 sm:gap-6 sm:p-5">
          {colunas(
            d,
            (c) => (
              <Link href={c.perfil} className="botao-linha w-full px-2! text-center">
                Perfil completo<span className="sr-only"> de {c.nome_urna}</span>
              </Link>
            ),
            <span />,
          ).map((n, i) => (
            <div key={i} className="min-w-0">
              {n}
            </div>
          ))}
        </div>
      </div>
      {d.faltam > 0 && (
        <p className="text-sm text-muted-foreground">
          O 2º turno tem dois candidatos.{" "}
          {d.faltam === 2 ? "Os dados deles" : "Os dados do outro candidato"} ainda não foram carregados no Panóptico a
          partir do TSE.
        </p>
      )}
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}

/** Detalhe de um candidato: textos longos, empilhados (não cabem lado a lado no celular). */
export function DetalheCandidato({
  c,
  dados,
  cargo,
}: {
  c: CandidatoSegundoTurno;
  dados: SegundoTurno;
  cargo: string;
}) {
  const eleicoes = c.carreira ?? [];
  return (
    <details className="painel group">
      <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between gap-3 font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze [&::-webkit-details-marker]:hidden">
        <span className="min-w-0 break-words">
          {c.nome_urna}
          {c.numero && <span className="text-muted-foreground"> · {c.numero}</span>}
          <span className="block text-sm font-normal text-muted-foreground">{cargo}: bens, campanha, eleições e registros</span>
        </span>
        <span aria-hidden className="text-lg text-muted-foreground transition-transform group-open:rotate-90 motion-reduce:transition-none">
          ›
        </span>
      </summary>
      <div className="mt-3 flex flex-col gap-5 text-sm leading-relaxed">
        <div className="flex flex-col gap-2">
          <h4 className="font-semibold">Maiores bens declarados</h4>
          {c.bens ? (
            <>
              <p>
                {INTEIRO.format(c.bens.quantidade)} {c.bens.quantidade === 1 ? "bem" : "bens"}, somando{" "}
                <span className="tabular-nums">{formatarReais(c.bens.total, true)}</span>
                {c.bens.anterior?.total != null && (
                  <>
                    . Na eleição de {c.bens.anterior.ano} ({c.bens.anterior.cargo.toLowerCase()}), declarou{" "}
                    <span className="tabular-nums">{formatarReais(c.bens.anterior.total, true)}</span>
                  </>
                )}
                .
              </p>
              <ul className="lista-fios flex flex-col">
                {c.bens.maiores.map((b, i) => (
                  <li key={i} className="flex items-baseline justify-between gap-3 py-2">
                    <span className="min-w-0 break-words">{b.tipo}</span>
                    <span className="shrink-0 tabular-nums">{formatarReais(b.valor, true)}</span>
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-muted-foreground">Bens {NAO_INFORMADO}.</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <h4 className="font-semibold">De onde veio o dinheiro da campanha</h4>
          {c.campanha ? (
            <>
              <p>
                Arrecadou <span className="tabular-nums">{formatarReais(c.campanha.receitas_total, true)}</span> e gastou{" "}
                <span className="tabular-nums">{formatarReais(c.campanha.despesas_total, true)}</span>, segundo a
                prestação de contas.
              </p>
              <ul className="lista-fios flex flex-col">
                {c.campanha.receitas_por_origem.map((o) => (
                  <li key={o.nome} className="flex items-baseline justify-between gap-3 py-2">
                    <span className="min-w-0 break-words">{o.nome}</span>
                    <span className="shrink-0 tabular-nums">{formatarReais(o.valor, true)}</span>
                  </li>
                ))}
              </ul>
              <p className="text-[13px] text-muted-foreground">
                Origem como o TSE classifica. Nomes de doadores pessoas físicas não são mostrados.
              </p>
            </>
          ) : (
            <p className="text-muted-foreground">Contas de campanha {NAO_INFORMADO}.</p>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <h4 className="font-semibold">Eleições que disputou antes</h4>
          {c.carreira === null ? (
            <p className="text-muted-foreground">
              Esta candidatura ainda não está ligada com segurança ao histórico da pessoa na base.
            </p>
          ) : eleicoes.length === 0 ? (
            <p>Nenhuma outra candidatura na base do TSE do Panóptico.</p>
          ) : (
            <ul className="lista-fios flex flex-col">
              {eleicoes.map((e, i) => (
                <li key={i} className="flex flex-col py-2">
                  <span>
                    <span className="tabular-nums">{e.ano}</span> · {e.cargo} · {e.unidade}
                  </span>
                  <span className="text-[13px] text-muted-foreground">
                    {[e.partido, e.situacao].filter(Boolean).join(" · ")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex flex-col gap-2">
          <h4 className="font-semibold">Registros na CGU e no TCU</h4>
          {c.sancoes === null ? (
            <p className="text-muted-foreground">
              Sem ligação segura entre esta candidatura e os cadastros da CGU e do TCU; não dá para dizer se há registros.
            </p>
          ) : c.sancoes.length === 0 ? (
            <p>Nenhum registro ligado a esta pessoa nos cadastros consultados.</p>
          ) : (
            <ul className="lista-fios flex flex-col">
              {c.sancoes.map((s, i) => (
                <li key={i} className="flex flex-col gap-0.5 py-2">
                  <span className="break-words">{s.descricao}</span>
                  <span className="text-[13px] text-muted-foreground">
                    {[s.orgao, s.data ? formatarData(s.data) : null, s.situacao].filter(Boolean).join(" · ")}
                    {s.fonte_url && (
                      <>
                        {" · "}
                        <LinkExterno href={s.fonte_url} className="underline underline-offset-2">
                          fonte
                        </LinkExterno>
                      </>
                    )}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <FonteRodape fonte={dados.sancoes_fonte_nome} url={dados.sancoes_fonte_url} atualizadoEm={dados.sancoes_atualizado_em} />
        </div>

        <FonteRodape
          fonte="TSE: candidaturas, bens e prestação de contas"
          url={c.campanha?.fonte_url ?? c.bens?.fonte_url ?? dados.fonte_url}
          atualizadoEm={dados.atualizado_em}
        />
      </div>
    </details>
  );
}
