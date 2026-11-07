import type { ReactNode } from "react";

import { FonteRodape } from "@/components/fonte-rodape";
import { TermoOficial } from "@/components/termo-oficial";
import type { PopulacaoCidade, SubsidioEstadual } from "@/lib/api";
import {
  CF_CONFERIDA_EM,
  CF_NOME,
  CF_URL,
  FONTE_SUBSIDIO_FEDERAL,
  SUBSIDIO_FEDERAL,
  SUBSIDIO_FEDERAL_DESDE,
  TETO_DEPUTADO_ESTADUAL,
  tetoVereador,
} from "@/lib/cargos";
import { formatarData, formatarReais } from "@/lib/formato";

/**
 * Teto que a Constituição põe no salário do vereador (art. 29, VI) e do deputado estadual
 * (art. 27, § 2º), com a conta à vista e, ao lado, o valor pago quando o Panóptico o tem. Sem o
 * valor pago, diz isso: não se estima nem se completa com o teto. Só descreve a regra e o número.
 */

const ALINEAS = ["a", "b", "c", "d", "e", "f"];
const N = (n: number) => n.toLocaleString("pt-BR");

/** Barra de comparação: valor pago (cheia até o teto) e o teto (hachurado). */
function BarrasPagoETeto({
  rotuloPago,
  pago,
  teto,
}: {
  rotuloPago: string;
  /** Nulo: o valor pago não está publicado. */
  pago: number | null;
  teto: number | null;
}) {
  const largura = pago !== null && teto ? `${Math.min(100, (pago / teto) * 100).toFixed(1)}%` : "0%";
  const descricao = `${rotuloPago}: ${pago !== null ? formatarReais(pago) : "não publicado"}. Teto pela Constituição: ${
    teto !== null ? formatarReais(teto) : "valor em reais não calculado"
  }.`;
  return (
    <div role="img" aria-label={descricao} className="flex flex-col gap-2">
      <div>
        <p className="flex justify-between gap-2 text-sm" aria-hidden="true">
          <span>{rotuloPago}</span>
          <span className="whitespace-nowrap tabular-nums">{pago !== null ? formatarReais(pago) : "não publicado"}</span>
        </p>
        <div
          className={`relative mt-1 h-2 ${pago !== null ? "bg-muted" : "bg-transparent ring-1 ring-border"}`}
          aria-hidden="true"
        >
          <i className="absolute inset-y-0 left-0 bg-chart-1" style={{ width: largura }} />
        </div>
      </div>
      {teto !== null && (
        <div>
          <p className="flex justify-between gap-2 text-sm" aria-hidden="true">
            <span>Teto pela Constituição</span>
            <span className="whitespace-nowrap tabular-nums">{formatarReais(teto)}</span>
          </p>
          <div className="relative mt-1 h-2 ring-1 ring-border" aria-hidden="true">
            <i
              className="absolute inset-0"
              style={{
                backgroundImage: "repeating-linear-gradient(135deg, var(--chart-3) 0 3px, transparent 3px 6px)",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function DiferencaAoTeto({ pago, teto }: { pago: number; teto: number }) {
  const dif = Math.round((teto - pago) * 100) / 100;
  return (
    <p className="text-sm tabular-nums">
      {dif === 0
        ? `O valor pago é igual ao teto: ${formatarReais(teto)} por mês.`
        : `Diferença entre o teto e o valor pago: ${formatarReais(Math.abs(dif))} por mês.`}
    </p>
  );
}

function FaltaPago({ quem, motivo }: { quem: string; motivo: string }) {
  return (
    <p className="rounded-md border border-dashed border-border p-3 text-sm">
      <strong className="font-semibold">O valor pago não está publicado aqui.</strong> O Panóptico não tem o salário que {quem}{" "}
      paga de fato. {motivo} Aparece só o teto; não estimamos o valor pago.
    </p>
  );
}

function Conta({ titulo, passos }: { titulo: string; passos: ReactNode[] }) {
  return (
    <details className="rounded-md border border-border px-3">
      <summary className="alvo-44 flex min-h-11 cursor-pointer items-center text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
        {titulo}
      </summary>
      <ol className="flex list-decimal flex-col gap-2 pb-3 pl-5 text-sm">
        {passos.map((p, i) => (
          <li key={i}>{p}</li>
        ))}
      </ol>
    </details>
  );
}

const Peq = ({ children }: { children: ReactNode }) => <span className="text-xs text-muted-foreground"> ({children})</span>;

/** Teto do vereador da cidade, pela população dela. */
export function TetoVereador({
  cidade,
  uf,
  populacao,
  subsidioUf,
  nomeCasa,
  compacto = false,
}: {
  cidade: string;
  uf: string;
  populacao: PopulacaoCidade;
  /** Subsídio do deputado estadual do estado (base da conta). */
  subsidioUf: SubsidioEstadual | null | undefined;
  nomeCasa: string;
  compacto?: boolean;
}) {
  const base = subsidioUf?.valor ?? null;
  const t = tetoVereador(populacao.valor, base);
  const ano = populacao.origem === "censo" ? `Censo de ${populacao.ano}` : `estimativa de ${populacao.ano}`;
  const moradores = `${N(populacao.valor)} moradores`;
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sm text-muted-foreground">
          {t.valor !== null ? "Teto por mês, valor bruto" : "Teto, em percentual do salário do deputado estadual"}
        </p>
        <p className="numero text-3xl tabular-nums">{t.valor !== null ? formatarReais(t.valor) : `${t.percentual}%`}</p>
        <p className="text-sm text-muted-foreground">
          {t.percentual}% do salário do deputado estadual de {uf}
          {t.valor === null && ", cujo valor ainda não está publicado aqui"}
        </p>
      </div>
      <p className="text-sm">
        {cidade} tem {moradores} ({ano}): faixa {t.faixa}, teto de {t.percentual}%.
      </p>
      <BarrasPagoETeto rotuloPago="Pago a cada vereador" pago={null} teto={t.valor} />
      <FaltaPago
        quem={`a ${nomeCasa}`}
        motivo="A câmara fixa o valor por lei própria e não há fonte nacional carregada com ele."
      />
      <Conta
        titulo={t.valor !== null ? `Por que o teto é ${formatarReais(t.valor)}` : "Como o teto é calculado"}
        passos={[
          <>
            {cidade} tem <b className="tabular-nums">{moradores}</b>
            <Peq>
              {populacao.origem === "censo" ? "IBGE, Censo" : "IBGE, estimativa"} de {populacao.ano}
            </Peq>
          </>,
          <>
            Cidade {t.faixa}: o teto é <b className="tabular-nums">{t.percentual}%</b> do salário do deputado estadual
            <Peq>CF, art. 29, VI, “{ALINEAS[t.indice]}”</Peq>
          </>,
          base !== null ? (
            <>
              O deputado estadual de {uf} ganha <b className="tabular-nums">{formatarReais(base)}</b>
              {subsidioUf?.ato_normativo && <Peq>{subsidioUf.ato_normativo}</Peq>}
            </>
          ) : (
            <>O salário do deputado estadual de {uf} não está publicado aqui, então o valor em reais não é calculado.</>
          ),
          ...(t.valor !== null && base !== null
            ? [
                <>
                  A conta:{" "}
                  <b className="tabular-nums">
                    {t.percentual}% × {formatarReais(base)} = {formatarReais(t.valor)}
                  </b>
                </>,
              ]
            : []),
        ]}
      />
      <div className="flex flex-col gap-1">
        <FonteRodape fonte={populacao.fonte_nome} url={populacao.fonte_url} atualizadoEm={populacao.atualizado_em} />
        {base !== null && subsidioUf?.fonte_url && (
          <FonteRodape
            fonte={subsidioUf.ato_normativo ?? `Assembleia de ${uf}`}
            url={subsidioUf.fonte_url}
            atualizadoEm={subsidioUf.consultado_em}
            semAviso
          />
        )}
        <FonteRodape fonte={`${CF_NOME}, art. 29, VI`} url={CF_URL} atualizadoEm={CF_CONFERIDA_EM} semAviso />
      </div>
      {!compacto && (
        <p className="text-xs text-muted-foreground">
          <TermoOficial id="subsidio">Subsídio</TermoOficial> dos vereadores: limite fixado pela Constituição; cada
          câmara decide o valor, em uma legislatura para a seguinte.
        </p>
      )}
    </div>
  );
}

/** Teto do deputado estadual (75% do deputado federal) ao lado do valor pago, quando publicado. */
export function TetoDeputadoEstadual({
  uf,
  subsidio,
  nomeCasa,
}: {
  uf: string;
  subsidio: SubsidioEstadual | null | undefined;
  nomeCasa: string;
}) {
  const pago = subsidio?.valor ?? null;
  return (
    <div className="flex flex-col gap-3">
      {pago !== null && (
        <dl className="grid grid-cols-2 gap-3">
          <div>
            <dt className="text-sm text-muted-foreground">Pago por mês</dt>
            <dd className="numero text-2xl tabular-nums">{formatarReais(pago)}</dd>
            {subsidio?.vigente_desde && (
              <dd className="text-xs text-muted-foreground">Desde {formatarData(subsidio.vigente_desde)}</dd>
            )}
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Teto</dt>
            <dd className="numero text-2xl tabular-nums">{formatarReais(TETO_DEPUTADO_ESTADUAL)}</dd>
            <dd className="text-xs text-muted-foreground">75% do deputado federal</dd>
          </div>
        </dl>
      )}
      {pago === null && (
        <div>
          <p className="text-sm text-muted-foreground">Teto por mês, valor bruto</p>
          <p className="numero text-3xl tabular-nums">{formatarReais(TETO_DEPUTADO_ESTADUAL)}</p>
          <p className="text-sm text-muted-foreground">75% do salário do deputado federal</p>
        </div>
      )}
      <BarrasPagoETeto rotuloPago={`Pago em ${uf}`} pago={pago} teto={TETO_DEPUTADO_ESTADUAL} />
      {pago !== null ? (
        <DiferencaAoTeto pago={pago} teto={TETO_DEPUTADO_ESTADUAL} />
      ) : (
        <FaltaPago
          quem={`a ${nomeCasa}`}
          motivo="O ato que fixa o valor ainda não foi conferido em fonte oficial."
        />
      )}
      <Conta
        titulo="Como o teto é calculado"
        passos={[
          <>
            O deputado federal ganha <b className="tabular-nums">{formatarReais(SUBSIDIO_FEDERAL)}</b>
            <Peq>
              {FONTE_SUBSIDIO_FEDERAL.nome}, desde {SUBSIDIO_FEDERAL_DESDE}
            </Peq>
          </>,
          <>
            O deputado estadual pode ganhar até <b>75%</b> disso<Peq>CF, art. 27, § 2º</Peq>
          </>,
          <>
            A conta:{" "}
            <b className="tabular-nums">
              75% × {formatarReais(SUBSIDIO_FEDERAL)} = {formatarReais(TETO_DEPUTADO_ESTADUAL)}
            </b>
          </>,
        ]}
      />
      <div className="flex flex-col gap-1">
        <FonteRodape fonte={FONTE_SUBSIDIO_FEDERAL.nome} url={FONTE_SUBSIDIO_FEDERAL.url} semAviso />
        <FonteRodape fonte={`${CF_NOME}, art. 27, § 2º`} url={CF_URL} atualizadoEm={CF_CONFERIDA_EM} semAviso />
      </div>
    </div>
  );
}
