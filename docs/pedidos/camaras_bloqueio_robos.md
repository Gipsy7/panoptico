# Pedido: câmaras que bloqueiam leitura automatizada (robots.txt ou HTTP 403/429)

**Situação:** a enviar (redigido em 27/10/2026). **Quem:** câmaras municipais (e-SIC / LAI) e, onde houver, o fornecedor do site.

## O que encontramos

86 câmaras sem canal no catálogo respondem ao nosso robô identificado com bloqueio: `robots.txt` com `User-agent: * / Disallow: /`, ou HTTP 403/429 já na página inicial (a maior parte atrás de proteção contra robôs do Cloudflare). Não trocamos o `User-Agent`, não usamos proxy nem navegador automatizado. Detalhe por câmara na coluna `evidencia` de `data/cidades_sem_canal_sistemas.csv`.

## O que pedimos

Liberar a leitura automatizada identificada das páginas públicas de vereadores, proposições e votações (regra no `robots.txt` ou no firewall para `Panoptico`), ou fornecer esses dados em formato aberto (LAI). O Panóptico lê só dado já público, uma requisição por vez, com pausa.

## Câmaras afetadas

- BA (3): Camaçari, Ilhéus, Miguel Calmon
- ES (1): Barra de São Francisco
- MA (1): Pinheiro
- MG (41): Aimorés, Alfredo Vasconcelos, Alpercata, Alvarenga, Antônio Carlos, Barroso, Belo Vale, Bugre, Camacho, Campanário, Cantagalo, Capelinha, Casa Grande, Catas Altas da Noruega, Coroaci, Crisólita, Cuparaque, Divino das Laranjeiras, Fernandes Tourinho, Frei Inocêncio, Ipaba, Itumirim, Jaguaraçu, Jeceaba, Joanésia, Lagoa Santa, Machacalis, Mesquita, Onça de Pitangui, Papagaios, Paracatu, Resplendor, Rio Acima, Santa Bárbara do Tugúrio, Santana do Riacho, Santana dos Montes, São José do Divino, São João Evangelista, São João del Rei, São Tiago, Tiradentes
- MT (6): Curvelândia, Juruena, Lambari D'Oeste, Reserva do Cabaçal, Rio Branco, Salto do Céu
- PB (1): Remígio
- PR (3): Godoy Moreira, São Carlos do Ivaí, São Jerônimo da Serra
- RJ (1): Laje do Muriaé
- RS (5): Cachoeirinha, Gravataí, Jaquirana, Morro Reuter, Segredo
- SC (12): Abelardo Luz, Alfredo Wagner, Campo Belo do Sul, Caxambu do Sul, Formosa do Sul, Forquilhinha, Gaspar, Ibirama, Painel, Papanduva, Timbé do Sul, Vidal Ramos
- SP (12): Alfredo Marcondes, Anhumas, Boituva, Bálsamo, Cabreúva, Descalvado, Francisco Morato, Guarulhos, Onda Verde, Porto Ferreira, Santa Mercedes, Taciba
