import type { Metadata } from "next";

import { Revelacao } from "@/components/revelacao";
import { getFontes } from "@/lib/api";
import { formatarData } from "@/lib/formato";

export const metadata: Metadata = {
  title: "Sobre as fontes",
  description: "De onde vem cada dado do Panóptico, como é calculado e quando foi atualizado.",
};

export default function SobreAsFontesPage() {
  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl tracking-tight">Sobre as fontes</h1>
        <p className="text-muted-foreground">
          Todos os dados do Panóptico vêm de fontes públicas e oficiais. Não fazemos notas,
          rankings nem avaliações: mostramos o dado, a média para comparação e o link para a
          fonte.
        </p>
      </header>

      <section aria-labelledby="fontes-titulo" className="revelar flex flex-col gap-3">
        <h2 id="fontes-titulo" className="text-2xl">
          De onde vem cada dado
        </h2>
        <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
          <ListaFontes />
        </Revelacao>
      </section>

      <section aria-labelledby="calculo-titulo" className="revelar flex flex-col gap-4">
        <h2 id="calculo-titulo" className="text-2xl">
          Como cada número é calculado
        </h2>
        <Item titulo="Gastos do gabinete">
          Soma dos reembolsos da cota parlamentar no ano (CEAP na Câmara, CEAPS no Senado),
          incluindo restituições, que aparecem como valores negativos. A média da Casa é a média
          do total por parlamentar em exercício; quem não gastou entra com zero.
        </Item>
        <Item titulo="Presença em votações">
          Quantas votações nominais do Plenário o parlamentar registrou voto, contadas a partir do
          início do ano ou do início do seu exercício atual (posse, posse de suplente ou retorno),
          o que vier depois. Quem preside a sessão conta como presente. O Senado informa ausências
          justificadas (missão oficial, licença); a Câmara publica apenas quem votou.
        </Item>
        <Item titulo="Projetos de lei">
          Projetos de lei (PL e PLP), propostas de emenda à Constituição (PEC) e projetos de
          decreto legislativo (PDL) apresentados desde fevereiro de 2023. O número principal conta
          só os projetos em que o parlamentar é o autor principal; coautorias aparecem à parte.
          &quot;Virou lei ou norma&quot; quer dizer que a situação oficial é &quot;transformado em
          norma jurídica&quot;.
        </Item>
        <Item titulo="Dinheiro enviado para a cidade">
          Valores de emendas individuais, dos orçamentos de 2023 em diante, pagos à prefeitura, aos
          fundos municipais e a entidades sem fins lucrativos da cidade. Não entram emendas de
          bancada, de comissão ou de relator, nem pagamentos a empresas ou a bancos
          intermediários. O autor é identificado pelo nome usado no orçamento; quem não está em
          exercício aparece em &quot;outros autores&quot;.
        </Item>
        <Item titulo="Bens e campanha">
          Dados que o próprio candidato declarou à Justiça Eleitoral (TSE) nas eleições de 2018 e
          2022, ligados ao parlamentar pelo CPF. Os bens são os da candidatura mais recente,
          comparados com a anterior, pelo valor declarado e sem correção. A campanha é a que deu o
          mandato atual: quanto arrecadou, de onde veio (fundo eleitoral e fundo partidário são
          dinheiro público) e com o que gastou. Não mostramos o nome de doadores pessoas físicas.
        </Item>
        <Item titulo="Votos nas comissões">
          Votações nominais nas comissões da Câmara e do Senado, com o voto do parlamentar e a
          comissão. Ficam separadas do Plenário: cada parlamentar vota só nas comissões de que
          faz parte, então não calculamos percentual nem média, e a presença e o alinhamento
          continuam contando só o Plenário.
        </Item>
        <Item titulo="Eleitos: do vereador ao presidente">
          Presidente, governador, prefeito (com os vices), deputados estaduais e vereadores eleitos,
          como publicado pelo TSE: foto da candidatura, votos recebidos, dados pessoais declarados
          (idade, escolaridade, ocupação; gênero e cor ou raça são autodeclarados), redes
          informadas, bens declarados e contas de campanha. Mudanças depois da eleição
          (renúncia, cassação, posse de suplente) não aparecem nesta lista.
        </Item>
        <Item titulo="Câmara hoje">
          Nas câmaras que usam o SAPL (sistema legislativo do Interlegis), mostramos quem está no
          cargo agora, como a própria câmara publica: titulares e suplentes, partido atual,
          contato e projetos do ano atual e do anterior. Requerimentos, indicações e moções
          aparecem só como contagem. Onde a câmara registra, também aparecem a presença nas
          sessões (só as sessões com a lista de presença lançada, durante o mandato, com a média
          da câmara) e o voto de cada um nas votações nominais; as votações simbólicas não anotam
          o voto de cada um e não aparecem. Cada vereador é ligado ao eleito do TSE pelo nome.
        </Item>
        <Item titulo="Assembleia hoje">
          O mesmo para os deputados estaduais, nas assembleias que usam o SAPL (Acre, Alagoas,
          Amazonas, Paraíba, Piauí, Rondônia e Tocantins). Roraima também usa o SAPL, mas o
          servidor da assembleia bloqueia o acesso automático vindo de fora do país, de onde a
          carga roda. Nos outros estados, por enquanto, aparece a lista de eleitos do TSE. Em Minas Gerais, os
          dados vêm da API aberta da própria assembleia (ALMG): deputados no cargo, projetos e
          gastos do gabinete (verba indenizatória, com a média da assembleia). A ALMG não publica
          o voto de cada deputado nem a lista de presença. Em São Paulo, o mesmo vem dos arquivos de
          dados abertos da ALESP, com o voto de cada deputado nas comissões permanentes (cada
          votação aparece com o nome da comissão); votos e presença em Plenário não estão neles. Em Pernambuco,
          da API de dados abertos da ALEPE: deputados no cargo e projetos, com indicações e
          requerimentos como contagem; a API não traz votos, presença nem gastos do gabinete. No
          Distrito Federal, da API pública do processo legislativo da Câmara Legislativa (CLDF):
          deputados distritais no cargo e projetos; votos e presença não estão nela. Em Santa
          Catarina, das páginas públicas da ALESC e do sistema e-Legis: deputados no cargo e
          proposições (a ALESC não tem API de dados abertos).
        </Item>
        <Item titulo="Dinheiro dos partidos">
          Prestação de contas anual dos partidos ao TSE (dados abertos): quanto o diretório
          nacional recebeu do Fundo Partidário e do fundo eleitoral (FEFC) mês a mês, as receitas
          por fonte e as despesas por tipo, somando diretórios nacional, estaduais e municipais.
          São valores declarados pelos partidos; a análise das contas pela Justiça Eleitoral vem
          depois e não está aqui. Transferências entre diretórios e repasses a candidaturas ficam
          separadas do gasto, para não contar o mesmo dinheiro duas vezes. A divisão do fundo
          eleitoral e do Fundo Partidário por gênero e cor ou raça vem de outro arquivo do TSE e
          cobre a eleição de 2024. Não mostramos doadores pessoas físicas nem pagamentos a
          fornecedores específicos.
        </Item>
        <Item titulo="Contas da cidade">
          O que a prefeitura declarou ao Tesouro Nacional na Declaração de Contas Anuais
          (SICONFI): receita realizada, despesa paga e despesa paga por função de governo (saúde,
          educação...). A função &quot;Legislativa&quot; é o custo da câmara municipal. Os dados são
          anuais; nem todo município entrega no prazo.
        </Item>
        <Item titulo="Para quem a cidade pagou">
          Nas cidades de São Paulo, os pagamentos da prefeitura, da câmara e de autarquias e
          fundos municipais, como as cidades informam ao Tribunal de Contas do Estado. Mostramos
          o total pago a cada um dos maiores fornecedores no ano; o restante aparece somado.
          Pagamentos a pessoas físicas (servidores, autônomos, beneficiários) aparecem somados e
          sem nomes. Outros estados entram à medida que seus Tribunais de Contas publiquem
          dados abertos equivalentes.
        </Item>
        <Item titulo="Canais oficiais da cidade">
          Os sites da prefeitura, da câmara e dos portais da transparência foram encontrados por
          uma varredura automática dos domínios oficiais (.gov.br e .leg.br) e conferidos por
          amostragem; as capitais foram conferidas uma a uma. O catálogo é aberto no GitHub e
          aceita correções.
        </Item>
        <Item titulo="Como votou">
          Contam as votações nominais do Plenário em que o parlamentar deu voto (Sim, Não,
          Abstenção ou Obstrução). &quot;Votou como o Governo orientou&quot; usa a orientação da
          liderança do Governo registrada por cada Casa, só quando ela foi Sim, Não ou Obstrução;
          votações liberadas ficam de fora. No Senado, a maior parte das votações nominais é
          secreta ou não tem orientação registrada, então os totais dos senadores são menores.
          &quot;Votou como a maioria do seu partido&quot; compara com o voto mais comum entre os
          outros parlamentares do mesmo partido naquele dia (pelo menos dois votando; empates ficam
          de fora).
        </Item>
        <Item titulo="Temas">
          Os temas são a classificação oficial de cada Casa para cada proposição (uma proposição
          pode ter vários). Na Câmara, são os temas da própria Câmara; no Senado, usamos o segundo
          nível da classificação do Senado (por exemplo &quot;Educação&quot; em &quot;Política
          Social / Educação&quot;). Por isso os nomes dos temas não coincidem entre as Casas. O Panóptico não classifica ninguém como a favor ou contra um tema:
          um voto &quot;Sim&quot; pode tanto endurecer quanto suavizar uma lei, e por isso
          mostramos a ementa de cada votação.
        </Item>
        <Item titulo="Votos em comum (comparador)">
          Entre dois parlamentares da mesma Casa, contamos as votações em que os dois deram voto e
          quantas vezes o voto foi igual. Votações secretas ficam de fora. Deputados e senadores
          votam em votações diferentes, então entre eles só comparamos os números.
        </Item>
        <Item titulo="Lista de todos os parlamentares">
          A lista pode ser ordenada por um critério de cada vez, sempre com a definição na tela e
          a média da Casa. Não há nota geral nem posição: juntar critérios exigiria escolher pesos,
          e isso seria uma opinião. A ordem padrão é alfabética.
        </Item>
        <Item titulo="Salário">
          O subsídio é o mesmo para todos os deputados federais e senadores e é fixado por decreto
          legislativo. Os gastos do gabinete são uma verba separada.
        </Item>
      </section>

      <section aria-labelledby="erros-titulo" className="revelar flex flex-col gap-2">
        <h2 id="erros-titulo" className="text-2xl">
          Encontrou um erro?
        </h2>
        <p className="text-muted-foreground">
          Os dados são copiados das fontes oficiais sem edição. Se algo estiver diferente da
          fonte, confira a data de atualização: as fontes corrigem dados com frequência e o
          Panóptico atualiza tudo diariamente.
        </p>
      </section>
    </article>
  );
}

async function ListaFontes() {
  const resultado = await getFontes();
  if (!resultado.ok) {
    return <p className="text-muted-foreground">Não foi possível carregar a lista agora.</p>;
  }
  return (
    <ul className="lista-fios flex flex-col">
      {resultado.dados.map((f) => (
        <li key={f.dado} className="flex flex-col gap-0.5 p-4">
          <span className="font-medium">{f.dado}</span>
          <span className="text-sm text-muted-foreground">
            <a
              href={f.url}
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2"
            >
              {f.orgao}
            </a>
            {f.atualizado_em && <> · atualizado em {formatarData(f.atualizado_em)}</>}
          </span>
        </li>
      ))}
    </ul>
  );
}

function Item({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <h3 className="font-medium">{titulo}</h3>
      <p className="text-sm text-muted-foreground">{children}</p>
    </div>
  );
}
