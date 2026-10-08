import type { Canal } from "@/lib/api";
import { formatarData } from "@/lib/formato";

const ROTULOS: Record<string, string> = {
  prefeitura: "Site da prefeitura",
  camara: "Site da câmara municipal",
  transparencia_prefeitura: "Portal da transparência da prefeitura",
  transparencia_camara: "Portal da transparência da câmara",
  sapl: "Sistema legislativo da câmara (projetos e vereadores)",
};

/** Sites oficiais da cidade, achados pela varredura e revisados (catálogo no repositório). */
export function CanaisSecao({ canais, cidade }: { canais: Canal[]; cidade: string }) {
  if (canais.length === 0) return null;
  const verificado = canais.map((c) => c.verificado_em).filter(Boolean).sort().at(-1);
  return (
    <section aria-labelledby="canais-titulo" className="revelar flex flex-col gap-3">
      <div>
        <h2 id="canais-titulo" className="text-2xl">
          Canais oficiais de {cidade}
        </h2>
        <p className="text-sm text-muted-foreground">
          Onde a prefeitura e a câmara publicam o que fazem. Pela lei, todo município precisa ter
          um portal da transparência.
        </p>
      </div>
      <ul className="lista-fios flex flex-col">
        {canais.map((c) => (
          <li key={c.tipo} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-3">
            <span className="text-sm text-muted-foreground">{ROTULOS[c.tipo] ?? c.tipo}</span>
            <a href={c.url} target="_blank" rel="noopener noreferrer" className="min-w-0 truncate text-sm underline underline-offset-2">
              {new URL(c.url).hostname.replace(/^www\./, "")}
            </a>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">
        Encontrados automaticamente
        {verificado ? ` e verificados em ${formatarData(verificado)}` : ""}. Achou um link errado
        ou faltando? O catálogo é aberto:{" "}
        <a href="https://github.com/Gipsy7/panoptico/blob/dev/data/canais_oficiais.csv" className="underline underline-offset-2">
          corrija pelo GitHub
        </a>
        .
      </p>
    </section>
  );
}
