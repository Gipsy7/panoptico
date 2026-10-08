import type { Pessoais } from "@/lib/api";

/** "Quem é": dados declarados ao TSE e votos recebidos, logo depois do cabeçalho, igual em
 * todos os perfis (federal, estadual, vereador, Executivo). */
export function QuemESecao({
  pessoais,
  votos,
}: {
  pessoais: Pessoais | null | undefined;
  votos?: { ano: number; total: number } | null;
}) {
  if (!pessoais && !votos) return null;
  return (
    <section aria-labelledby="quem-e-titulo" className="revelar flex flex-col gap-3">
      <h2 id="quem-e-titulo" className="text-2xl">
        Quem é
      </h2>
      <DadosPessoais pessoais={pessoais ?? null} votos={votos} />
    </section>
  );
}

/** Dados declarados ao TSE na candidatura mais recente, e os votos recebidos. */
export function DadosPessoais({
  pessoais,
  votos,
}: {
  pessoais: Pessoais | null;
  votos?: { ano: number; total: number } | null;
}) {
  if (!pessoais && !votos) return null;
  const linhas: [string, string | null | undefined][] = [
    ["Votos recebidos", votos ? `${votos.total.toLocaleString("pt-BR")} na eleição de ${votos.ano}` : null],
    ["Idade", pessoais?.idade != null ? `${pessoais.idade} anos` : null],
    ["Escolaridade", pessoais?.grau_instrucao],
    ["Ocupação declarada", pessoais?.ocupacao],
    ["Gênero", pessoais?.genero],
    ["Cor ou raça", pessoais?.cor_raca],
    ["Estado civil", pessoais?.estado_civil],
  ];
  const visiveis = linhas.filter(([, valor]) => valor);

  return (
    <div className="flex flex-col gap-3">
      <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
        {visiveis.map(([rotulo, valor]) => (
          <div key={rotulo} className="flex items-baseline justify-between gap-4 border-b border-border py-2 text-sm">
            <dt className="text-muted-foreground">{rotulo}</dt>
            <dd className="text-right">{valor}</dd>
          </div>
        ))}
      </dl>
      {pessoais && pessoais.redes.length > 0 && (
        <div className="flex flex-col gap-1">
          <p className="text-sm text-muted-foreground">Redes e sites informados ao TSE</p>
          <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
            {pessoais.redes.map((url) => (
              <li key={url}>
                <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="underline underline-offset-2">
                  {rotuloDaRede(url)}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
      {pessoais && (
        <p className="text-xs text-muted-foreground">
          Declarado pelo próprio candidato ao TSE em {pessoais.ano}. Gênero e cor ou raça são
          autodeclarados.
        </p>
      )}
    </div>
  );
}

function rotuloDaRede(url: string): string {
  try {
    const host = new URL(url).hostname.replace(/^www\./, "");
    const conhecidas: Record<string, string> = {
      "instagram.com": "Instagram",
      "facebook.com": "Facebook",
      "x.com": "X (Twitter)",
      "twitter.com": "X (Twitter)",
      "youtube.com": "YouTube",
      "tiktok.com": "TikTok",
      "linkedin.com": "LinkedIn",
      "kwai.com": "Kwai",
      "threads.net": "Threads",
    };
    return conhecidas[host] ?? host;
  } catch {
    return url;
  }
}
