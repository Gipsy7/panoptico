import { CONTATO_EMAIL, SITE_URL } from "@/lib/site";

const LICENCA_DADOS = "https://github.com/Gipsy7/panoptico/blob/main/LICENCA-DADOS.md";
const REPOSITORIO = "https://github.com/Gipsy7/panoptico";

const TEXTO = `# Panóptico

> Site de transparência política: mostra quem representa cada cidadão (presidente a vereador) e o que cada um faz, gasta, vota e recebe. Todo número vem de dado oficial, com link da fonte e data da última atualização, e aparece ao lado da média da Casa para comparação. Não há nota, ranking nem avaliação.

## Como achar um representante

- [Início (busca por CEP)](${SITE_URL}/): digite o CEP e veja quem o representa.
- Perfil de deputado federal ou senador: ${SITE_URL}/parlamentar/{id}
- Cidade (vereadores, prefeitura, repasses): ${SITE_URL}/cidade/{codigo-ibge}
- [Representantes](${SITE_URL}/representantes): quem representa o cidadão em cada nível.
- [Partidos](${SITE_URL}/partidos): dinheiro público e contas dos partidos.
- [Projetos e votações](${SITE_URL}/projetos): busca por número ou assunto; cada projeto mostra o que diz, as votações nominais, quem votou, o que disseram em Plenário e o caminho. Páginas: ${SITE_URL}/projeto/{camara|senado}/{id}, ${SITE_URL}/projeto/local/{id}, ${SITE_URL}/votacao/{camara|senado}/{id}, ${SITE_URL}/votacao/local/{id}.

## Páginas principais

- [Sobre as fontes](${SITE_URL}/sobre-as-fontes): de onde vem cada dado, como é calculado e quando foi atualizado.
- [Cobertura](${SITE_URL}/sobre-as-fontes/cobertura): o que o site já cobre e o que ainda falta.
- [Impostos e repasses](${SITE_URL}/impostos-e-repasses): dinheiro enviado pela União para estados e cidades.
- [Status](${SITE_URL}/status): situação e data da última carga de cada fonte.
- [Privacidade](${SITE_URL}/privacidade): que dados são coletados e quais não são.

## Dados abertos e licenças

- [Código-fonte](${REPOSITORIO}): licença AGPL-3.0.
- [Licença dos dados](${LICENCA_DADOS}): os arquivos de dados abertos (Parquet e CSV.gz, gerados por backend/exportar) estão sob CC BY 4.0; é preciso dar crédito ao Panóptico e à fonte oficial.
- Nada de CPF, título de eleitor ou data de nascimento é publicado; doadores pessoas físicas não têm nome exibido.

## Contato

- ${CONTATO_EMAIL}

## Ao citar

Cite a fonte oficial de cada dado (indicada em cada seção) e a data de atualização exibida, além do Panóptico (${SITE_URL}). Os números são reproduzidos como a fonte os publica.
`;

export function GET() {
  return new Response(TEXTO, {
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
}
