import Link from "next/link";
import { FonteRodape } from "@/components/fonte-rodape";
import type { ResultadoEleicao } from "@/lib/api";
import {
  formatarPct,
  formatarVotos,
  larguraBarra,
  lugarDaDisputa,
  nomeCargo,
  situacaoSimples,
} from "@/lib/eleicao";

/**
 * Resultado de uma disputa (versão A, Frente 5): quem votou, a tabela de candidatos com barra
 * de % dos válidos e as eleições anteriores no mesmo lugar. Sem cor de partido: a barra tem um
 * tom só e "Eleito" vem escrito. Ver docs/DECISOES.md, "Eleições completas".
 */
export function TabelaResultado({
  r,
  titulo,
  nivelTitulo = 2,
  hrefTurno,
  semFonte = false,
}: {
  r: ResultadoEleicao;
  titulo?: string;
  nivelTitulo?: 2 | 3;
  /** Link para o outro turno, quando houver dois. */
  hrefTurno?: (turno: number) => string;
  semFonte?: boolean;
}) {
  const Titulo = nivelTitulo === 2 ? "h2" : "h3";
  const lugar = lugarDaDisputa(r);
  const cargo = nomeCargo(r.cargo);
  const maior = r.candidatos[0]?.votos ?? 0;
  const t = r.totais;
  const id = `resultado-${r.ano}-${r.cargo}-${r.turno}`
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, "-");

  return (
    <section aria-labelledby={id} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <Titulo id={id} className={nivelTitulo === 2 ? "text-2xl" : "text-xl"}>
          {titulo ?? `${cargo}, ${r.ano}`}
        </Titulo>
        <p className="text-sm text-muted-foreground">
          {lugar} · {r.turno}º turno
          {r.abrangencia === "municipio" ? " · votos dados nesta cidade" : ""}
        </p>
        {r.turnos.length > 1 && hrefTurno && (
          <nav aria-label="Turno" className="mt-1 flex gap-2 text-sm">
            {r.turnos.map((turno) =>
              turno === r.turno ? (
                <span
                  key={turno}
                  aria-current="page"
                  className="rounded-[2px] border border-foreground px-3 py-2 font-medium"
                >
                  {turno}º turno
                </span>
              ) : (
                <Link
                  key={turno}
                  href={hrefTurno(turno)}
                  className="rounded-[2px] border border-border px-3 py-2 underline-offset-2 hover:underline"
                >
                  {turno}º turno
                </Link>
              ),
            )}
          </nav>
        )}
      </div>

      {t && (
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-muted-foreground">Podiam votar</dt>
            <dd className="tabular-nums">{formatarVotos(t.aptos)}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Votaram</dt>
            <dd className="tabular-nums">
              {formatarVotos(t.comparecimento)}{" "}
              <span className="text-muted-foreground">
                ({formatarPct(t.pct_comparecimento, 1)})
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Em branco</dt>
            <dd className="tabular-nums">
              {formatarVotos(t.brancos)}{" "}
              <span className="text-muted-foreground">
                ({formatarPct(t.pct_brancos, 1)})
              </span>
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Nulos</dt>
            <dd className="tabular-nums">
              {formatarVotos(t.nulos)}{" "}
              <span className="text-muted-foreground">
                ({formatarPct(t.pct_nulos, 1)})
              </span>
            </dd>
          </div>
        </dl>
      )}

      <table className="w-full table-fixed border-collapse text-sm">
        <caption className="sr-only">
          Votos de cada candidato a {cargo.toLowerCase()} em {lugar}, {r.ano},{" "}
          {r.turno}º turno
        </caption>
        <thead>
          <tr className="border-b border-border text-left text-muted-foreground">
            <th scope="col" className="py-2 pr-2 font-normal">
              Candidato
            </th>
            <th scope="col" className="w-[42%] py-2 text-right font-normal">
              Votos <span className="text-xs">(% dos válidos)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {r.candidatos.map((c, i) => {
            const sit = situacaoSimples(c.situacao);
            const destaque =
              r.destaque_candidatura_id != null &&
              c.candidatura_id === r.destaque_candidatura_id;
            return (
              <tr
                key={`${c.nome_urna}-${i}`}
                className={`border-b border-border align-top ${destaque ? "bg-muted" : ""}`}
              >
                <th scope="row" className="py-2 pr-2 text-left font-normal">
                  <span
                    className={`block break-words ${c.eleito ? "font-semibold" : ""}`}
                  >
                    {c.candidatura_id ? (
                      <Link
                        href={`/eleito/${c.candidatura_id}`}
                        className="underline underline-offset-2"
                      >
                        {c.nome_urna}
                      </Link>
                    ) : (
                      c.nome_urna
                    )}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {[c.partido, c.numero ? `nº ${c.numero}` : null]
                      .filter(Boolean)
                      .join(" · ")}
                    {" · "}
                    {sit.texto}
                    {sit.oficial ? (
                      <span className="text-[0.7rem]"> ({sit.oficial})</span>
                    ) : null}
                  </span>
                </th>
                <td className="py-2 text-right">
                  <span className="block tabular-nums">
                    {formatarVotos(c.votos)}
                  </span>
                  <span className="block text-xs tabular-nums text-muted-foreground">
                    {formatarPct(c.pct)}
                  </span>
                  <span
                    aria-hidden
                    className="mt-1 block h-1.5 w-full overflow-hidden rounded-[2px] bg-muted"
                  >
                    <span
                      className="block h-full rounded-[2px] bg-bronze"
                      style={{
                        width: `${larguraBarra(c.votos, maior)}%`,
                        marginLeft: "auto",
                      }}
                    />
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {r.total_candidatos > r.candidatos.length && (
        <p className="text-sm text-muted-foreground">
          Mostrando os {r.candidatos.length} mais votados de{" "}
          {formatarVotos(r.total_candidatos)} candidatos.
        </p>
      )}
      {r.proporcional && (
        <p className="text-sm text-muted-foreground">
          Nesta eleição as vagas são divididas entre os partidos pela soma dos
          votos; por isso nem sempre o mais votado se elege.{" "}
          <span className="text-xs">
            (sistema proporcional, Código Eleitoral, arts. 106 a 109)
          </span>
        </p>
      )}

      {r.anteriores.length > 0 && (
        <details className="group rounded-[2px] border border-border">
          <summary className="flex min-h-11 cursor-pointer items-center px-3 text-sm font-medium">
            Quem se elegeu nas eleições anteriores aqui
          </summary>
          <ul className="flex flex-col gap-2 px-3 pb-3 text-sm">
            {r.anteriores.map((a) => (
              <li key={a.ano}>
                <span className="tabular-nums font-medium">{a.ano}</span>
                {a.turno > 1 ? (
                  <span className="text-muted-foreground">
                    {" "}
                    ({a.turno}º turno)
                  </span>
                ) : null}
                :{" "}
                {a.eleitos.length > 6
                  ? `${a.eleitos.length} eleitos`
                  : a.eleitos
                      .map(
                        (e) =>
                          `${e.nome_urna}${e.partido ? ` (${e.partido})` : ""}`,
                      )
                      .join(", ")}
              </li>
            ))}
          </ul>
        </details>
      )}

      {!semFonte && (
        <FonteRodape
          fonte={r.fonte_nome}
          url={r.fonte_url}
          atualizadoEm={r.atualizado_em}
        />
      )}
    </section>
  );
}
