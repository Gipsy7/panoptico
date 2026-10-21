import { SITE_URL } from "@/lib/site";

/** Bloco JSON-LD (dados estruturados para buscadores). `<` vira < para não fechar o script. */
export function JsonLd({ dados }: { dados: Record<string, unknown> }) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(dados).replace(/</g, "\\u003c") }}
    />
  );
}

type PerfilPessoa = {
  caminho: string;
  nome: string;
  cargo: string;
  /** Casa ou órgão em que exerce o cargo. */
  casa?: string | null;
  partido?: string | null;
  uf?: string | null;
  imagem?: string | null;
  oficial?: string | null;
};

/** `ProfilePage` com uma `Person`. Só dados públicos do mandato: nada de CPF, nascimento ou título. */
export function JsonLdPerfil({ caminho, nome, cargo, casa, partido, uf, imagem, oficial }: PerfilPessoa) {
  const url = `${SITE_URL}${caminho}`;
  const pessoa: Record<string, unknown> = { "@type": "Person", name: nome, jobTitle: cargo, url };
  if (partido) pessoa.memberOf = { "@type": "PoliticalParty", name: partido };
  if (casa) pessoa.worksFor = { "@type": "GovernmentOrganization", name: casa };
  if (uf && uf !== "BR") {
    pessoa.address = { "@type": "PostalAddress", addressRegion: uf, addressCountry: "BR" };
  }
  if (imagem) pessoa.image = imagem;
  if (oficial) pessoa.sameAs = [oficial];
  return (
    <JsonLd
      dados={{ "@context": "https://schema.org", "@type": "ProfilePage", url, name: nome, mainEntity: pessoa }}
    />
  );
}

/** "Nome (PARTIDO-UF)"; sem partido nem UF, sem parêntese. */
export function nomeComSigla(nome: string, partido?: string | null, uf?: string | null) {
  const sigla = [partido, uf && uf !== "BR" ? uf : null].filter(Boolean).join("-");
  return sigla ? `${nome} (${sigla})` : nome;
}

/** Junta as frases que couberem em ~160 caracteres, na ordem; a primeira sempre entra. */
export function montarDescricao(
  frases: (string | null | false | undefined)[],
  final = "Dados oficiais com fonte.",
): string {
  let texto = "";
  for (const f of frases.filter((x): x is string => Boolean(x))) {
    const novo = texto ? `${texto} ${f}` : f;
    if (texto && `${novo} ${final}`.length > 160) break;
    texto = novo;
  }
  return texto ? `${texto} ${final}` : final;
}

export const LICENCA_DADOS_URL = "https://github.com/Gipsy7/panoptico/blob/main/LICENCA-DADOS.md";

export type DistribuicaoDataset = {
  formato: string; // ex.: "application/vnd.apache.parquet", "text/csv"
  url: string; // só links que a página já mostra
};

/** JSON-LD `Dataset` (schema.org). Sem `distribution` quando não há link de download. */
export function JsonLdDataset({
  nome,
  descricao,
  distribuicoes = [],
}: {
  nome: string;
  descricao: string;
  distribuicoes?: DistribuicaoDataset[];
}) {
  return (
    <JsonLd
      dados={{
        "@context": "https://schema.org",
        "@type": "Dataset",
        name: nome,
        description: descricao,
        url: SITE_URL,
        license: LICENCA_DADOS_URL,
        isAccessibleForFree: true,
        inLanguage: "pt-BR",
        spatialCoverage: "Brasil",
        creator: { "@type": "Organization", name: "Panóptico", url: SITE_URL },
        ...(distribuicoes.length > 0 && {
          distribution: distribuicoes.map((d) => ({
            "@type": "DataDownload",
            encodingFormat: d.formato,
            contentUrl: d.url,
          })),
        }),
      }}
    />
  );
}
