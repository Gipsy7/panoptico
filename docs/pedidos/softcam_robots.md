# Pedido: câmaras que vedam leitura automatizada (sistema Softcam)

**Situação:** a enviar (redigido em 27/10/2026). **Quem:** fornecedor do sistema e câmaras municipais (e-SIC / LAI, Lei 12.527/2011).

## O que encontramos

Em 191 câmaras municipais sem canal oficial no catálogo (levantamento de 21/10/2026, `data/cidades_sem_canal_sistemas.csv`), o `robots.txt` do site libera os buscadores (Google, Bing) apenas para algumas pastas e veda todo o resto aos demais robôs:

```
User-agent: *
Disallow: /
```

As pastas citadas nas regras dos buscadores (`/softcam/`, `/ciga/`, `/legisbr/`, `/legisla/`, `/rfassessoria/`, `/legislarr/`) identificam o mesmo sistema nas 191 câmaras. Pela regra do Panóptico, `robots.txt` que veda não é contornado: não abrimos nem a página inicial desses sites. Por isso essas câmaras ficam sem a lista de vereadores, projetos, votos e presença, e o site informa que o dado existe mas não é aberto à leitura automatizada.

## O que pedimos

1. Ao fornecedor: liberar no `robots.txt` o acesso do `User-Agent: Panoptico` (ou de leitores identificados) às páginas públicas de vereadores, proposições e votações; ou publicar um arquivo/API de dados abertos por câmara.
2. Às câmaras (LAI): lista dos vereadores em exercício com partido, proposições do ano e votações nominais, em formato aberto (CSV/JSON), ou autorização para leitura automatizada do site público.

Identificação do robô: `Panoptico/0.1 (+https://panoptico.social.br; contato@panoptico.social.br)`; uma requisição por vez, com pausa, só dados que já são públicos.

## Câmaras afetadas

- MG (5): Aiuruoca, Cambuí, Leopoldina, Ponto dos Volantes, Santa Rita do Sapucaí
- PR (15): Abatiá, Braganey, Candói, Curiúva, Douradina, Ibiporã, Iguatu, Iracema do Oeste, Jesuítas, Matinhos, Nova Aurora, Paiçandu, Palotina, Porto Amazonas, São Pedro do Iguaçu
- RS (22): Arroio Grande, Arroio do Sal, Augusto Pestana, Bom Jesus, Brochier, Canela, Cerro Largo, Cândido Godói, Dom Pedrito, Farroupilha, Giruá, Horizontina, Ipê, Paraí, Porto Lucena, Rosário do Sul, Santana da Boa Vista, Taquara, Torres, Tucunduva, Ubiretama, Venâncio Aires
- SC (138): Abdon Batista, Alto Bela Vista, Anitápolis, Antônio Carlos, Arabutã, Armazém, Arroio Trinta, Arvoredo, Bandeirante, Barra Bonita, Barra Velha, Bela Vista do Toldo, Belmonte, Benedito Novo, Bom Jesus, Bom Jesus do Oeste, Bombinhas, Brunópolis, Caibi, Calmon, Campo Alegre, Canelinha, Canoinhas, Capinzal, Capão Alto, Catanduvas, Caçador, Celso Ramos, Cerro Negro, Chapadão do Lageado, Cocal do Sul, Concórdia, Cordilheira Alta, Coronel Freitas, Coronel Martins, Correia Pinto, Cunha Porã, Cunhataí, Curitibanos, Doutor Pedrinho, Entre Rios, Ermo, Erval Velho, Flor do Sertão, Frei Rogério, Galvão, Grão-Pará, Guaramirim, Herval d'Oeste, Ibicaré, Imaruí, Imbituba, Ipumirim, Iraceminha, Irani, Irati, Itaiópolis, Jaborá, Jaguaruna, Jardinópolis, Joaçaba, Lacerdópolis, Lajeado Grande, Lebon Régis, Leoberto Leal, Lontras, Luzerna, Macieira, Mafra, Major Gercino, Maracajá, Marema, Matos Costa, Meleiro, Modelo, Mondaí, Navegantes, Nova Trento, Nova Veneza, Novo Horizonte, Otacílio Costa, Ouro, Ouro Verde, Paial, Palmitos, Paraíso, Passo de Torres, Passos Maia, Paulo Lopes, Pedras Grandes, Peritiba, Ponte Alta, Ponte Serrada, Praia Grande, Presidente Castello Branco, Rio Rufino, Rio das Antas, Rio do Oeste, Rio dos Cedros, Riqueza, Saltinho, Salto Veloso, Sangão, Santa Helena, Santa Terezinha, Santa Terezinha do Progresso, Saudades, Seara, Serra Alta, Siderópolis, Sul Brasil, São Bonifácio, São Joaquim, São Martinho, São Miguel da Boa Vista, São Miguel do Oeste, Taió, Tangará, Tigrinhos, Timbó Grande, Treze Tílias, Treze de Maio, Três Barras, Tubarão, Turvo, União do Oeste, Urupema, Urussanga, Vargem, Vargem Bonita, Vargeão, Vitor Meireles, Xanxerê, Xavantina, Xaxim, Água Doce, Águas Frias, Águas de Chapecó
- SP (11): Engenheiro Coelho, Itaberá, Itirapina, Paraibuna, Pindamonhangaba, Pitangueiras, Potim, Salesópolis, Santa Branca, Tabatinga, Vargem Grande do Sul
