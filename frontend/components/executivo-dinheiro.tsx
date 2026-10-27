import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { PorQueFalta } from "@/components/por-que-falta";
import { BarraComparacao } from "@/components/painel/barra-comparacao";
import type { Comparacao } from "@/components/painel/cartao-numero";
import type { BlocoPainel, ContasEstado, PainelExecutivo } from "@/lib/api";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";

/** Lê um campo numérico de `dados` (que varia por bloco); ausente ou não numérico vira null. */
export function num(dados: Record<string, unknown> | null, campo: string): number | null {
  const v = dados?.[campo];
  return typeof v === "number" ? v : null;
}

/** O que o ente é, em linguagem do dia a dia ("o governo do estado", "a prefeitura"). */
export function nomeDoGoverno(p: PainelExecutivo): string {
  if (p.ente.tipo === "uniao") return "o governo federal";
  if (p.ente.tipo === "estado") return `o governo do estado de ${p.ente.nome}`;
  return `a prefeitura de ${p.ente.nome}`;
}

/** Bloco sem dado: mesma frase para todo cargo e todo partido, com o motivo que a API deu. */
export function BlocoIndisponivel({
  titulo,
  bloco,
  painel,
}: {
  titulo: string;
  bloco: BlocoPainel;
  /** Com o painel, o aviso ganha o link "Por que falta este dado?" para a casa certa. */
  painel?: PainelExecutivo;
}) {
  const uf = painel ? (painel.ente.tipo === "uniao" ? "BR" : painel.ente.uf) : null;
  const casa = !painel
    ? undefined
    : painel.ente.tipo === "uniao"
      ? "Presidência da República"
      : uf
        ? painel.ente.tipo === "estado"
          ? `Governo de ${uf}`
          : `Prefeituras de ${uf}`
        : undefined;
  return (
    <section className="flex flex-col gap-1">
      <h2 className="text-2xl">{titulo}</h2>
      <p className="text-sm text-muted-foreground">
        Ainda não há dado aberto carregado para esta seção. {bloco.motivo ?? "A fonte não informou o motivo."}
      </p>
      {painel && uf && casa && (
        <p className="text-sm">
          <PorQueFalta uf={uf} casa={casa} />
        </p>
      )}
    </section>
  );
}

/** Aviso do vice: o número é do ente, não da pessoa. */
export function AvisoDoGoverno({ painel }: { painel: PainelExecutivo }) {
  if (painel.titular) return null;
  return (
    <p className="rounded-xl bg-card p-3 text-sm ring-1 ring-foreground/10">
      Os números desta página são de {nomeDoGoverno(painel)}, que é quem administra o dinheiro. Eles não são de{" "}
      {painel.nome_urna}: o cargo de vice não tem contas próprias na fonte.
    </p>
  );
}

function periodo(dados: Record<string, unknown> | null): string {
  const p = dados?.periodo as { inicio?: number | null; fim?: number | null } | null | undefined;
  if (p?.inicio != null && p.fim != null && p.inicio !== p.fim) return `de ${p.inicio} a ${p.fim}`;
  if (p?.inicio != null) return `em ${p.inicio}`;
  return "no período coberto";
}

/** Comparação por habitante do ente com a média dos entes do mesmo tipo (mesma escala). */
export function comparacaoContas(p: PainelExecutivo): { comparacao?: Comparacao; mediaRotulo: string } {
  const d = p.contas.dados;
  const porHab = num(d, "despesa_por_habitante");
  const estado = p.ente.tipo === "estado";
  const media = num(d, estado ? "media_estados_despesa_por_habitante" : "media_uf_despesa_por_habitante");
  const n = num(d, estado ? "estados_na_media" : "municipios_na_media");
  const mediaRotulo = estado
    ? `Média dos ${n ?? ""} estados`.replace("  ", " ")
    : `Média dos ${n?.toLocaleString("pt-BR") ?? ""} municípios do estado`.replace("  ", " ");
  if (porHab == null || media == null) return { mediaRotulo };
  return {
    mediaRotulo,
    comparacao: {
      pessoa: { rotulo: p.ente.nome, valor: porHab },
      media: { rotulo: mediaRotulo, valor: media },
      formato: "reais",
    },
  };
}

export { periodo as rotuloPeriodo };

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="figura min-w-0">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="numero text-xl break-words sm:text-3xl">{valor}</dd>
    </div>
  );
}

/** Contas do governo do ente (prefeitura ou estado), com a média por habitante ao lado. */
export function ContasDoGoverno({ painel, estado }: { painel: PainelExecutivo; estado: ContasEstado | null }) {
  const b = painel.contas;
  const d = b.dados;
  const ano = num(d, "ano");
  const despesa = num(d, "despesa_paga");
  const receita = num(d, "receita_total");
  const porHab = num(d, "despesa_por_habitante");
  const { comparacao, mediaRotulo } = comparacaoContas(painel);
  const nomeEnte = painel.ente.nome;
  const semDado = num(d, "estados_sem_dado");
  return (
    <section aria-labelledby="gov-contas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="gov-contas-titulo" className="text-2xl">
          Contas de {nomeEnte}
          {ano ? ` em ${ano}` : ""}
        </h2>
        <p className="text-sm text-muted-foreground">
          O que {nomeDoGoverno(painel)} declarou ao Tesouro Nacional (Declaração de Contas Anuais, SICONFI)
        </p>
      </div>
      <dl className="grid grid-cols-2 gap-3">
        {receita != null && <Linha rotulo="Arrecadou" valor={formatarReais(receita, true)} />}
        {despesa ? (
          <Linha rotulo="Gastou (pago)" valor={formatarReais(despesa, true)} />
        ) : (
          <div className="figura min-w-0">
            <dt className="text-sm text-muted-foreground">Gastou (pago)</dt>
            <dd className="text-sm text-muted-foreground">Não informado pela fonte</dd>
          </div>
        )}
      </dl>
      {comparacao && (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-muted-foreground">Gasto por habitante, na mesma escala</p>
          <BarraComparacao pessoa={comparacao.pessoa} media={comparacao.media} formato="reais" />
          {semDado != null && semDado > 0 && (
            <p className="text-sm text-muted-foreground">
              {semDado} {semDado === 1 ? "estado ficou" : "estados ficaram"} fora da média por não terem entregado a
              despesa paga ao Tesouro.
            </p>
          )}
          {estado?.media_estados_descricao && (
            <p className="text-sm text-muted-foreground">{estado.media_estados_descricao}</p>
          )}
        </div>
      )}
      {!comparacao && porHab != null && (
        <p className="text-sm">
          <span className="tabular-nums">{formatarReais(porHab, true)}</span> por habitante ({mediaRotulo} não
          disponível)
        </p>
      )}
      {estado && estado.por_area.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="font-medium">Em que áreas gastou</h3>
          <ul className="flex flex-col gap-2.5">
            {estado.por_area.slice(0, 6).map((a) => (
              <li key={a.nome} className="flex flex-col gap-1">
                <div className="flex items-baseline justify-between gap-3 text-sm">
                  <span className="min-w-0">{a.nome}</span>
                  <span className="shrink-0 tabular-nums">
                    {formatarReais(a.valor, true)}
                    <span className="ml-1 text-sm text-muted-foreground">
                      {a.percentual.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%
                    </span>
                  </span>
                </div>
                <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
                  <div
                    className="h-1.5 rounded-full bg-chart-1"
                    style={{ width: `${Math.max(1, Math.min(100, a.percentual))}%` }}
                  />
                </div>
              </li>
            ))}
          </ul>
          <p className="text-sm text-muted-foreground">
            Valores pagos no ano, pela função de governo (a classificação oficial do orçamento).
          </p>
        </div>
      )}
      {painel.ente.tipo === "municipio" && painel.ente.municipio_ibge && (
        <Link
          href={`/cidade/${painel.ente.municipio_ibge}`}
          className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Ver todo o dinheiro de {nomeEnte}
        </Link>
      )}
      <FonteRodape
        fonte={b.fonte_nome ?? "Tesouro Nacional (SICONFI)"}
        url={b.fonte_url ?? undefined}
        atualizadoEm={b.atualizado_em}
      />
    </section>
  );
}

/** Emendas recebidas pela cidade (todos os tipos), com a média por morador dos municípios do estado. */
export function EmendasDaCidade({ painel }: { painel: PainelExecutivo }) {
  const b = painel.emendas;
  const d = b.dados;
  const total = num(d, "total_geral");
  const porHab = num(d, "por_habitante_geral");
  const media = num(d, "media_uf_por_habitante_geral");
  const n = num(d, "municipios_na_media");
  return (
    <section aria-labelledby="gov-emendas-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="gov-emendas-titulo" className="text-2xl">
          Dinheiro enviado para {painel.ente.nome} por emendas
        </h2>
        <p className="text-sm text-muted-foreground">
          Emendas parlamentares pagas ao município {periodo(d)} (a verba que deputados e senadores indicam)
        </p>
      </div>
      {total != null && (
        <dl>
          <Linha rotulo="Total pago" valor={formatarReais(total, true)} />
        </dl>
      )}
      {porHab != null && media != null && (
        <BarraComparacao
          pessoa={{ rotulo: `${painel.ente.nome}, por morador`, valor: porHab }}
          media={{
            rotulo: n ? `Média dos ${n.toLocaleString("pt-BR")} municípios do estado` : "Média dos municípios do estado",
            valor: media,
          }}
          formato="reais"
        />
      )}
      {painel.ente.municipio_ibge && (
        <Link
          href={`/cidade/${painel.ente.municipio_ibge}#ver-emendas`}
          className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Ver quem enviou e para quê
        </Link>
      )}
      <FonteRodape fonte={b.fonte_nome ?? "Portal da Transparência"} url={b.fonte_url ?? undefined} atualizadoEm={b.atualizado_em} />
    </section>
  );
}

/** Resumo dos contratos da prefeitura no PNCP; a lista completa fica na página da cidade. */
export function ContratosDaCidade({ painel }: { painel: PainelExecutivo }) {
  const b = painel.contratos;
  const d = b.dados;
  const ano = num(d, "ano");
  const valor = num(d, "valor_dos_maiores");
  const n = num(d, "maiores_fornecedores");
  return (
    <section aria-labelledby="gov-contratos-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="gov-contratos-titulo" className="text-2xl">
          Contratos da prefeitura{ano ? ` em ${ano}` : ""}
        </h2>
        <p className="text-sm text-muted-foreground">
          Contratos publicados no Portal Nacional de Contratações Públicas (PNCP)
        </p>
      </div>
      {valor != null && n != null && (
        <p className="text-sm">
          Os {n.toLocaleString("pt-BR")} maiores fornecedores somam{" "}
          <span className="numero text-lg">{formatarReaisCompacto(valor)}</span> em contratos.
        </p>
      )}
      {painel.ente.municipio_ibge && (
        <Link
          href={`/cidade/${painel.ente.municipio_ibge}#ver-pncp`}
          className="alvo-link self-start text-sm font-medium text-primary underline underline-offset-4"
        >
          Ver a lista de fornecedores
        </Link>
      )}
      <FonteRodape fonte={b.fonte_nome ?? "PNCP"} url={b.fonte_url ?? undefined} atualizadoEm={b.atualizado_em} />
    </section>
  );
}
