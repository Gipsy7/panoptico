import Link from "next/link";
import { FonteRodape } from "@/components/fonte-rodape";
import type { Antecessores } from "@/lib/api";
import { nomeCargo } from "@/lib/eleicao";

/** Quem teve o cargo antes, em linha do tempo (versão B, Frente 5). Só nome, partido e período,
 * sem comparar desempenho. Vereador: cada legislatura recolhida, com quem continua marcado. */
export function AntecessoresLinha({
  d,
  atualId,
}: {
  d: Antecessores;
  atualId?: number | null;
}) {
  const cargo = nomeCargo(d.cargo);
  const lugar = d.municipio
    ? d.municipio.nome
    : d.uf === "BR" || !d.uf
      ? "no Brasil"
      : d.uf;
  const atuais = new Set(d.mandatos[0]?.pessoas.map((p) => p.nome) ?? []);
  const muitos = d.mandatos.some((m) => m.pessoas.length > 3);

  return (
    <section
      aria-labelledby="antecessores-titulo"
      className="flex flex-col gap-3"
    >
      <div>
        <h2 id="antecessores-titulo" className="text-2xl">
          Quem teve o cargo antes
        </h2>
        <p className="text-sm text-muted-foreground">
          {cargo} em {lugar}, eleição a eleição
        </p>
      </div>
      <ol className="relative flex flex-col gap-4 border-l-2 border-border pl-4">
        {d.mandatos.map((m, i) => (
          <li key={m.ano} className="relative flex flex-col gap-1 text-sm">
            <span
              aria-hidden
              className={`absolute -left-[1.4rem] top-1.5 size-3 rounded-full border-2 border-background ${i === 0 ? "bg-bronze" : "bg-muted-foreground"}`}
            />
            <p className="font-medium tabular-nums">
              {m.inicio}–{m.fim}
              <span className="font-normal text-muted-foreground">
                {" "}
                · eleição de {m.ano}
              </span>
              {i === 0 && (
                <span className="font-normal text-muted-foreground">
                  {" "}
                  · mandato atual
                </span>
              )}
            </p>
            {muitos ? (
              <details>
                <summary className="flex min-h-11 cursor-pointer items-center">
                  {m.pessoas.length} pessoas
                </summary>
                <ul className="flex flex-col gap-0.5">
                  {m.pessoas.map((p) => (
                    <li key={p.nome}>
                      {p.nome}
                      {p.partido ? (
                        <span className="text-muted-foreground">
                          {" "}
                          · {p.partido}
                        </span>
                      ) : null}
                      {i > 0 && atuais.has(p.nome) ? (
                        <span className="text-muted-foreground">
                          {" "}
                          · está no mandato atual
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              </details>
            ) : (
              <ul className="flex flex-col gap-0.5">
                {m.pessoas.map((p) => (
                  <li key={p.nome}>
                    {p.candidatura_id && p.candidatura_id !== atualId ? (
                      <Link
                        href={`/eleito/${p.candidatura_id}`}
                        className="underline underline-offset-2"
                      >
                        {p.nome}
                      </Link>
                    ) : (
                      p.nome
                    )}
                    {p.partido ? (
                      <span className="text-muted-foreground">
                        {" "}
                        · {p.partido}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ol>
      <p className="text-xs text-muted-foreground">
        Quem se elegeu, segundo o TSE. Mudanças no meio do mandato (renúncia,
        cassação, posse do vice) não aparecem aqui.
      </p>
      <FonteRodape
        fonte={d.fonte_nome}
        url={d.fonte_url}
        atualizadoEm={d.atualizado_em}
        semAviso
      />
    </section>
  );
}
