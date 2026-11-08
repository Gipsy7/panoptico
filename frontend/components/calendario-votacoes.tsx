/**
 * Calendário das votações nominais do Plenário em /projetos (Frente 4, mapa de calor C): número
 * de votações em cada dia, um tom só (bronze) em degraus com legenda, número sempre escrito.
 * Tocar num dia filtra a lista logo abaixo; a chave "Só o que muda leis" vale para os números e
 * para a lista. Tudo pelo endereço (funciona sem JavaScript).
 */
import Link from "next/link";

import { ChaveSoTexto } from "@/components/chave-so-texto";
import { ComoSeparamos } from "@/components/como-separamos-votacoes";
import { FonteRodape } from "@/components/fonte-rodape";
import { TermoOficial } from "@/components/termo-oficial";
import { TextoLongo } from "@/components/ui/texto-longo";
import { type CalendarioVotacoes as Dados, type Casa, type VotacaoDoCalendario, getCalendarioVotacoes } from "@/lib/api";
import {
  DIAS_SEMANA_CURTO,
  FAIXAS,
  MESES_NOME,
  type EstadoCalendario,
  contagemTexto,
  dataIso,
  degrau,
  diaDaSemana,
  enderecoCalendario,
  gradeDoMes,
  rotuloDia,
} from "@/lib/calendario-votacoes";
import { CASA_CURTA, formatarData } from "@/lib/formato";
import { ROTULO_TIPO, avisoRecorte } from "@/lib/recorte-votacoes";
import { cn } from "@/lib/utils";

const INTEIRO = new Intl.NumberFormat("pt-BR");

/** Fundo e texto de cada degrau (tokens --calor-*, app/globals.css). */
const COR_DEGRAU = [
  "bg-background text-foreground",
  "bg-calor-1 text-foreground",
  "bg-calor-2 text-foreground",
  "bg-calor-3 text-foreground",
  "bg-calor-4 text-calor-texto-4",
] as const;

const CASA_NO_PLENARIO: Record<Casa, string> = {
  camara: "no Plenário da Câmara",
  senado: "no Plenário do Senado",
};

/** Busca e mostra o calendário; sem dado (API fora ou Casa sem votação), não mostra nada. */
export async function SecaoCalendarioVotacoes({ estado }: { estado: EstadoCalendario }) {
  const [ano, mes] = estado.mes ? estado.mes.split("-") : [undefined, undefined];
  const r = await getCalendarioVotacoes({
    casa: estado.casa,
    ano,
    mes,
    dia: estado.dia,
    tipo: estado.tipo,
    pagina: estado.pagina,
  });
  if (!r.ok) return null;
  return <CalendarioVotacoes dados={r.dados} estado={estado} />;
}

export function CalendarioVotacoes({ dados, estado }: { dados: Dados; estado: EstadoCalendario }) {
  const { ano, mes, tipo } = dados;
  const nomeMes = MESES_NOME[mes - 1];
  const contaDoDia = new Map(dados.dias.map((d) => [d.data, d]));
  const numero = (c: { todas: number; merito: number; procedimento: number }) =>
    tipo === "merito" ? c.merito : tipo === "procedimento" ? c.procedimento : c.todas;
  const totalMes = numero(dados.totais);
  const diasComVotacao = dados.dias.filter((d) => numero(d) > 0).length;
  const atual: EstadoCalendario = { ...estado, casa: dados.casa, mes: `${ano}-${String(mes).padStart(2, "0")}` };
  const ir = (muda: Partial<EstadoCalendario>) => enderecoCalendario(atual, { pagina: undefined, ...muda });
  const mesRef = (m: { ano: number; mes: number }) => `${m.ano}-${String(m.mes).padStart(2, "0")}`;
  const diaSel = dados.dia ? Number(dados.dia.slice(8, 10)) : null;
  const lista = dados.lista;
  const paginas = Math.max(1, Math.ceil(lista.total / lista.por_pagina));

  return (
    <section id="calendario-votacoes" aria-labelledby="calendario-titulo" className="flex scroll-mt-20 flex-col gap-3">
      <div>
        <h2 id="calendario-titulo" className="text-2xl">
          Votações no Plenário, dia a dia
        </h2>
        <p className="text-sm text-muted-foreground">
          Quantas <TermoOficial id="votacao-nominal">votações nominais</TermoOficial> houve em cada dia do mês, com as que o
          Panóptico já tem.
        </p>
      </div>

      <nav aria-label="Casa" className="flex flex-wrap gap-2">
        {(["camara", "senado"] as const).map((c) => (
          <Link
            key={c}
            href={enderecoCalendario({ tipo: estado.tipo, mes: atual.mes }, { casa: c })}
            scroll={false}
            aria-current={c === dados.casa ? "true" : undefined}
            className={cn(
              "inline-flex min-h-11 items-center rounded-md border px-3 text-sm font-medium tabular-nums",
              c === dados.casa ? "border-foreground bg-accent" : "border-border hover:bg-accent/50",
            )}
          >
            {CASA_CURTA[c]} · {INTEIRO.format(dados.por_casa[c])}
            <span className="sr-only"> votações nominais em {nomeMes}</span>
          </Link>
        ))}
      </nav>

      <ChaveSoTexto ligada={tipo === "merito"} href={ir({ tipo: tipo === "merito" ? "todas" : "merito", dia: estado.dia })} />

      <div className="flex items-center justify-between gap-2">
        <h3 className="text-xl first-letter:uppercase">
          {nomeMes} de {ano}
        </h3>
        <div className="flex gap-1">
          <NavMes
            alvo={dados.mes_anterior}
            rotulo={(m) => `Mês anterior com votação: ${MESES_NOME[m.mes - 1]} de ${m.ano}`}
            href={(m) => ir({ mes: mesRef(m), dia: undefined })}
            seta="‹"
          />
          <NavMes
            alvo={dados.mes_seguinte}
            rotulo={(m) => `Próximo mês com votação: ${MESES_NOME[m.mes - 1]} de ${m.ano}`}
            href={(m) => ir({ mes: mesRef(m), dia: undefined })}
            seta="›"
          />
        </div>
      </div>

      <p className="text-sm">
        <strong className="tabular-nums">{contagemTexto(totalMes, tipo)}</strong> {CASA_NO_PLENARIO[dados.casa]}
        {diasComVotacao > 0 && `, em ${diasComVotacao} ${diasComVotacao === 1 ? "dia" : "dias"} do mês`}.
        {tipo !== "todas" && dados.totais.todas > totalMes && (
          <> Com as de procedimento, {INTEIRO.format(dados.totais.todas)}.</>
        )}
      </p>

      <div>
        <div aria-hidden className="grid grid-cols-7 gap-[3px] pb-1 text-center text-xs text-muted-foreground">
          {DIAS_SEMANA_CURTO.map((s) => (
            <span key={s}>{s}</span>
          ))}
        </div>
        <ul aria-label={`Dias de ${nomeMes} de ${ano}`} className="grid grid-cols-7 gap-[3px]">
          {gradeDoMes(ano, mes).map((dia, i) => {
            if (dia === null) return <li key={`v${i}`} aria-hidden />;
            const c = contaDoDia.get(dataIso(ano, mes, dia));
            const todas = c?.todas ?? 0;
            const n = c ? numero(c) : 0;
            const nivel = degrau(n);
            const rotulo = rotuloDia(ano, mes, dia, n, todas, tipo);
            const corpo = (
              <>
                <span aria-hidden className={cn("text-xs leading-none", nivel === 0 && "text-muted-foreground")}>
                  {dia}
                </span>
                <span aria-hidden className={cn("numero leading-tight tabular-nums", todas ? "text-lg" : "text-sm text-muted-foreground")}>
                  {todas ? n : "–"}
                </span>
              </>
            );
            const base = "flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-sm border py-1";
            return (
              <li key={dia} className="min-w-0">
                {todas > 0 ? (
                  <Link
                    href={ir({ dia: diaSel === dia ? undefined : dataIso(ano, mes, dia) })}
                    scroll={false}
                    aria-current={diaSel === dia ? "date" : undefined}
                    className={cn(
                      base,
                      COR_DEGRAU[nivel],
                      diaSel === dia ? "border-2 border-foreground" : "border-border hover:border-foreground",
                    )}
                  >
                    {corpo}
                    {/* Nome pelo texto escondido, não por aria-label: o número visível ("2", "1") não
                        bate com a frase e o leitor de tela precisa da frase inteira. */}
                    <span className="sr-only">{rotulo}</span>
                  </Link>
                ) : (
                  <span className={cn(base, "border-transparent")}>
                    {corpo}
                    <span className="sr-only">{rotulo}</span>
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="flex flex-col gap-1">
        <p className="flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-muted-foreground">
          <span>Votações no dia:</span>
          {FAIXAS.map((f, i) => (
            <span
              key={f}
              className={cn(
                "inline-grid h-6 min-w-9 place-items-center rounded-sm border border-border px-1 text-xs tabular-nums",
                COR_DEGRAU[i],
              )}
            >
              {f}
            </span>
          ))}
        </p>
        <p className="text-sm text-muted-foreground">
          Quanto mais escuro, mais votações; o número está escrito em cada dia. Traço: nenhuma votação nominal, o que
          não quer dizer dia sem trabalho (pode ter tido sessão, votação simbólica ou comissão).
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <div className="flex flex-wrap items-baseline justify-between gap-x-3">
          <h3 className="text-lg">
            {diaSel
              ? `Votações de ${diaDaSemana(ano, mes, diaSel)}, ${diaSel} de ${nomeMes}`
              : `Votações de ${nomeMes}`}
          </h3>
          {diaSel && (
            <Link href={ir({ dia: undefined })} scroll={false} className="alvo-link text-sm font-medium underline underline-offset-2">
              Ver o mês inteiro
            </Link>
          )}
        </div>
        <p role="status" className="text-sm">
          {avisoRecorte(lista.contagem_tipos, tipo)}
        </p>
        <ComoSeparamos />
        {lista.itens.length === 0 ? (
          <p className="nota text-sm">
            {lista.contagem_tipos.todas === 0
              ? "Nenhuma votação nominal neste dia."
              : "Nenhuma votação sobre o texto aqui. Desligue a chave para ver as de procedimento."}
          </p>
        ) : (
          <ul className="lista-fios">
            {lista.itens.map((v) => (
              <ItemVotacao key={v.id_externo} v={v} casa={dados.casa} />
            ))}
          </ul>
        )}
        {paginas > 1 && (
          <nav aria-label="Páginas de votações" className="flex items-center justify-between text-sm">
            {lista.pagina > 1 ? (
              <Link href={enderecoCalendario(atual, { pagina: String(lista.pagina - 1) })} scroll={false} className="alvo-link font-medium underline underline-offset-4">
                <span aria-hidden>←</span> Mais recentes
              </Link>
            ) : (
              <span />
            )}
            <span className="text-muted-foreground tabular-nums">
              {lista.pagina} de {paginas}
            </span>
            {lista.pagina < paginas ? (
              <Link href={enderecoCalendario(atual, { pagina: String(lista.pagina + 1) })} scroll={false} className="alvo-link font-medium underline underline-offset-4">
                Mais antigas <span aria-hidden>→</span>
              </Link>
            ) : (
              <span />
            )}
          </nav>
        )}
      </div>

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} semAviso />
    </section>
  );
}

function NavMes({
  alvo,
  rotulo,
  href,
  seta,
}: {
  alvo: { ano: number; mes: number } | null;
  rotulo: (m: { ano: number; mes: number }) => string;
  href: (m: { ano: number; mes: number }) => string;
  seta: string;
}) {
  const classe = "inline-grid size-11 place-items-center rounded-md border text-lg";
  if (!alvo) {
    return (
      <span aria-hidden className={cn(classe, "border-border text-muted-foreground opacity-50")}>
        {seta}
      </span>
    );
  }
  return (
    <Link href={href(alvo)} scroll={false} aria-label={rotulo(alvo)} className={cn(classe, "border-muted-foreground hover:bg-accent/50")}>
      <span aria-hidden>{seta}</span>
    </Link>
  );
}

function ItemVotacao({ v, casa }: { v: VotacaoDoCalendario; casa: Casa }) {
  const { sim, nao } = v.placar;
  return (
    <li className="flex flex-col gap-1 py-3">
      <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground">
        <span className="tabular-nums">{formatarData(v.data)}</span>
        <span aria-hidden>·</span>
        <span className="rounded-sm border border-border px-1.5 text-xs font-medium text-foreground">
          {ROTULO_TIPO[v.tipo]}
        </span>
      </p>
      <Link href={`/votacao/${casa}/${encodeURIComponent(v.id_externo)}`} className="font-semibold underline underline-offset-2">
        {v.proposicao ?? "Votação sem projeto identificado"}
      </Link>
      {v.proposicao_ementa && <TextoLongo linhas={2}>{v.proposicao_ementa}</TextoLongo>}
      <p className="text-xs text-muted-foreground">Texto oficial: {v.descricao}</p>
      {v.secreta ? (
        <p className="text-sm">Votação secreta{v.resultado ? ` · ${v.resultado}` : ""}</p>
      ) : (
        (sim !== null || nao !== null) && (
          <p className="text-sm tabular-nums">
            <span className="numero text-base">{INTEIRO.format(sim ?? 0)}</span> Sim ×{" "}
            <span className="numero text-base">{INTEIRO.format(nao ?? 0)}</span> Não
            {v.resultado && <span className="text-muted-foreground"> · {v.resultado}</span>}
          </p>
        )
      )}
    </li>
  );
}
