import Link from "next/link";

import { FotoOuIniciais } from "@/components/eleitos-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import type { Chapa, Executivo } from "@/lib/api";

/** Presidente, governador e prefeito eleitos, cada um com o vice (TSE). */
export function ExecutivoSecao({ dados, estado, cidade }: { dados: Executivo; estado: string; cidade: string | null }) {
  const chapas: { rotulo: string; chapa: Chapa | null }[] = [
    { rotulo: "Presidente", chapa: dados.presidente },
    { rotulo: `Governador de ${estado}`, chapa: dados.governador },
    ...(cidade ? [{ rotulo: `Prefeito de ${cidade}`, chapa: dados.prefeito }] : []),
  ];
  if (chapas.every((c) => !c.chapa)) return null;

  return (
    <section aria-labelledby="executivo-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="executivo-titulo" className="text-2xl">
          Executivo
        </h2>
        <p className="text-sm text-muted-foreground">
          Quem foi eleito para governar o país, o estado e a cidade, segundo o TSE.
        </p>
      </div>
      <ul className="grid border-t border-border sm:grid-cols-3 sm:gap-x-8">
        {chapas.map(({ rotulo, chapa }) =>
          chapa ? (
            <li key={rotulo} className="flex flex-col gap-2 border-b border-border py-3">
              <span className="sobretitulo">{rotulo}</span>
              <Link href={`/eleito/${chapa.titular.id}`} className="group flex items-center gap-3 hover:opacity-80">
                <FotoOuIniciais eleito={chapa.titular} />
                <span className="min-w-0">
                  <span className="block truncate font-semibold group-hover:underline">{chapa.titular.nome_urna}</span>
                  <span className="block text-sm text-muted-foreground">
                    {[chapa.titular.partido, `eleição de ${chapa.ano_eleicao}`].filter(Boolean).join(" · ")}
                  </span>
                </span>
              </Link>
              {chapa.vice && (
                <p className="text-sm text-muted-foreground">
                  Vice:{" "}
                  <Link href={`/eleito/${chapa.vice.id}`} className="underline underline-offset-2">
                    {chapa.vice.nome_urna}
                  </Link>
                  {chapa.vice.partido && ` (${chapa.vice.partido})`}
                </p>
              )}
            </li>
          ) : null,
        )}
      </ul>
      <p className="text-xs text-muted-foreground">
        Mudanças depois da eleição (renúncia, cassação, posse do vice) ainda não aparecem aqui.
      </p>
      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </section>
  );
}
