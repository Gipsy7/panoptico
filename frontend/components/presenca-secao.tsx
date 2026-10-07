import { FonteRodape } from "@/components/fonte-rodape";
import type { Casa, Presenca } from "@/lib/api";
import { CASA_CURTA, formatarData } from "@/lib/formato";

const PCT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });

export function PresencaSecao({ presenca, casa }: { presenca: Presenca; casa: Casa }) {
  const p = presenca;
  const inicioDoAno = p.periodo_inicio.endsWith("-01-01");

  return (
    <section aria-labelledby="presenca-titulo" className="revelar flex flex-col gap-4">
      <div>
        <h2 id="presenca-titulo" className="text-2xl">
          Presença em votações
        </h2>
        <p className="text-xs text-muted-foreground">
          Votações nominais no Plenário em {p.ano}
          {!inicioDoAno && `, desde ${formatarData(p.periodo_inicio)} (início do exercício atual)`}
        </p>
      </div>

      {p.total_votacoes === 0 ? (
        <p className="text-muted-foreground">Nenhuma votação nominal neste período.</p>
      ) : (
        <>
          <dl className="grid grid-cols-2 gap-3">
            <div className="figura">
              <dt className="text-sm text-muted-foreground">Votou em</dt>
              <dd className="numero text-3xl">
                {p.votou} de {p.total_votacoes}
              </dd>
              <dd className="text-sm text-muted-foreground tabular-nums">
                {PCT.format(p.percentual ?? 0)}%
              </dd>
            </div>
            <div className="figura">
              <dt className="text-sm text-muted-foreground">
                Média por parlamentar do {CASA_CURTA[casa]}
              </dt>
              <dd className="numero text-3xl">
                {p.media_casa_percentual === null ? "—" : `${PCT.format(p.media_casa_percentual)}%`}
              </dd>
            </div>
          </dl>

          <div
            role="meter"
            aria-label="Participação nas votações"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={p.percentual ?? 0}
            aria-valuetext={`${PCT.format(p.percentual ?? 0)}%`}
            className="h-2 w-full rounded-full bg-muted"
          >
            <div
              className="h-2 rounded-full bg-chart-1"
              style={{ width: `${p.percentual ?? 0}%` }}
            />
          </div>

          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-1 text-sm">
            <dt>Votou</dt>
            <dd className="text-right tabular-nums">{p.votou}</dd>
            {p.presente_sem_voto > 0 && (
              <>
                <dt>Presente, sem registrar voto</dt>
                <dd className="text-right tabular-nums">{p.presente_sem_voto}</dd>
              </>
            )}
            {p.ausencia_detalhada && (
              <>
                <dt>Ausência justificada</dt>
                <dd className="text-right tabular-nums">{p.justificada}</dd>
                {p.justificativas.map((j) => (
                  <div key={j.motivo} className="col-span-2 grid grid-cols-subgrid pl-4 text-muted-foreground">
                    <dt>{j.motivo}</dt>
                    <dd className="text-right tabular-nums">{j.quantidade}</dd>
                  </div>
                ))}
              </>
            )}
            <dt>{p.ausencia_detalhada ? "Não compareceu" : "Sem registro de voto"}</dt>
            <dd className="text-right tabular-nums">{p.nao_compareceu}</dd>
          </dl>

          <p className="text-sm text-muted-foreground">
            {p.ausencia_detalhada
              ? "Ausência justificada inclui missão oficial, licença e atividade parlamentar fora do Plenário, conforme o registro do Senado."
              : "A Câmara publica apenas quem registrou voto. Ausências por licença ou missão oficial não aparecem separadas nestes dados."}
          </p>
        </>
      )}

      <FonteRodape fonte={p.fonte_nome} url={p.fonte_url} atualizadoEm={p.atualizado_em} />
    </section>
  );
}
