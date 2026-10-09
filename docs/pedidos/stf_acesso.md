# Pedido ao STF: acesso automatizado à consulta processual

**Para:** Secretaria de Tecnologia da Informação / Ouvidoria do Supremo Tribunal Federal
**Assunto:** Pedido de acesso automatizado a dados públicos de processos (pesquisa sem fins lucrativos)

Prezados,

O Panóptico (https://panoptico.social.br) é um projeto aberto e sem fins lucrativos de transparência sobre quem exerce função pública no Brasil. Todo dado exibido tem fonte oficial, link e data; o código é público (licença AGPL-3.0) em https://github.com/Gipsy7/panoptico.

Queremos mostrar, nos perfis de parlamentares federais e demais autoridades com foro no STF, os processos públicos em que figuram como parte: classe, número, relator, data de autuação, situação e link para a página do processo no portal do STF. Seguiremos a mesma regra que já usamos com outros órgãos: só processos públicos (nada sob segredo de justiça), texto estritamente factual e, em igual destaque, arquivamentos, absolvições e extinções.

Hoje a consulta processual responde "403 Forbidden" a qualquer acesso que não seja de navegador, inclusive à leitura do robots.txt. Não queremos contornar essa proteção, e por isso pedimos uma destas alternativas:

1. **Liberação de um endereço IP fixo**, identificado pelo User-Agent `Panoptico/0.1 (+https://panoptico.social.br)`, para consultas à lista de partes e à página do processo. Volume previsto: cerca de 700 consultas por nome uma vez por semana (parlamentares federais, Presidente e Vice-Presidente, ministros de Estado e ministros dos tribunais superiores), uma requisição por vez, com pausa entre elas, fora do horário de expediente; ou
2. **Um arquivo em formato aberto** (CSV ou JSON) com as partes dos processos das classes Inq, AP, Pet, HC e Rcl. Pode ser parte do Programa Corte Aberta. Basta o nome da parte, o polo, a classe, o número, o relator, a data de autuação e a situação; ou
3. **Uma chave de API** ou outro canal técnico que o Tribunal já ofereça a pesquisadores.

Ficamos à disposição para ajustar volume, horário e formato conforme a orientação técnica do Tribunal.

Atenciosamente,
[nome], responsável pelo projeto Panóptico
[e-mail de contato]
