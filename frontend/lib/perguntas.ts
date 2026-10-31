/**
 * Perguntas frequentes (texto puro). A página /perguntas mostra cada uma com links no lugar certo
 * (a `resposta` em JSX fica lá, por `id`); o Argos usa o `texto` para responder dúvidas sobre o site.
 */
export type PerguntaFrequente = { id: string; pergunta: string; texto: string };

export const PERGUNTAS_FREQUENTES: PerguntaFrequente[] = [
  {
    id: "fonte",
    pergunta: "De onde vêm os dados?",
    texto:
      "Todos os dados vêm de fontes públicas e oficiais, como a Câmara dos Deputados, o Senado Federal, o Portal da Transparência, o TSE e o IBGE. Cada seção tem o link da fonte e a data da última atualização. A página Sobre as fontes lista as fontes e explica como cada número é calculado.",
  },
  {
    id: "frequencia",
    pergunta: "Com que frequência os dados são atualizados?",
    texto:
      "Os dados federais são atualizados todos os dias. As câmaras municipais e as assembleias são atualizadas toda semana, e algumas fontes, como as contas dos partidos e das cidades, uma vez por mês. A data de cada fonte aparece na própria seção.",
  },
  {
    id: "cobertura",
    pergunta: "Por que a câmara ou os vereadores da minha cidade não aparecem?",
    texto:
      "Nem todo órgão publica seus dados de forma aberta. Quando a fonte não existe, bloqueia o acesso automático ou ainda não foi conectada, o site diz o que falta. Nos casos em que o acesso foi pedido pela Lei de Acesso à Informação, o pedido fica aberto ao público. A página de cobertura mostra a situação estado por estado.",
  },
  {
    id: "cep",
    pergunta: "O site guarda o meu CEP ou a minha localização?",
    texto:
      "Não. O CEP é usado só para descobrir a cidade e o estado e não é gravado em banco de dados. A localização, se você escolher usá-la, é processada no seu aparelho e não é enviada a nenhum servidor. Não há cadastro nem cookies de rastreamento ou publicidade. A única exceção é opcional: se você ativar avisos no celular (nos ambientes em que existirem), guardamos um endereço técnico do aparelho e o que ele acompanha, e você pode apagar tudo ao cancelar. Os detalhes estão na página de privacidade.",
  },
  {
    id: "nota",
    pergunta: "O site dá nota ou ranking? Ele é ligado a algum partido?",
    texto:
      "Não. O Panóptico não é ligado a nenhum partido, mandato ou campanha. O site não dá nota, não faz ranking e não classifica ninguém: mostra o número, a média da Casa ao lado e o link da fonte. Ele não aceita doações de partidos, mandatos, gabinetes ou campanhas eleitorais, e doações não mudam nada no que o site mostra.",
  },
  {
    id: "media-casa",
    pergunta: "O que é a média da Casa?",
    texto:
      "É a média entre os parlamentares em exercício na mesma Casa (Câmara ou Senado). Quem não tem nada no item, por exemplo quem não gastou, entra na conta com zero. Ela aparece ao lado do número para dar uma referência, sem julgamento.",
  },
  {
    id: "erro",
    pergunta: "Achei um número diferente da fonte. O que eu faço?",
    texto:
      "Os dados são copiados das fontes oficiais sem edição. Confira primeiro a data de atualização, porque as fontes corrigem dados com frequência. Se ainda estiver diferente, escreva para o e-mail de contato ou abra uma issue no GitHub com o link do perfil e da fonte.",
  },
  {
    id: "quem-paga",
    pergunta: "Quem faz o Panóptico e quem paga?",
    texto:
      "O trabalho de desenvolvimento é voluntário e o código é aberto. O site é gratuito, sem anúncios e sem cadastro. Os custos de manter tudo no ar são pequenos e pagos por doações; a página Apoie mostra quanto custa. Quem ajudou a fazer o projeto, de qualquer forma, e autorizou o nome aparece na lista de apoiadores.",
  },
  {
    id: "dados",
    pergunta: "Posso usar os dados do site?",
    texto:
      "Sim. Os arquivos de dados abertos do Panóptico estão sob a licença Creative Commons Atribuição 4.0 (CC BY 4.0): podem ser copiados, adaptados e usados para qualquer fim, inclusive comercial, com crédito ao Panóptico e à fonte oficial. Em caso de dúvida, vale o que consta na fonte oficial.",
  },
];
