# Assembleias sem votos nominais ou presença em formato aberto

Um pedido por Casa, com o mesmo texto-base (o mesmo de `almg_alesp_votos_presenca.md`). Em cada
envio, troque o nome da Casa e deixe só os itens que faltam a ela (tabela abaixo). Redigido em
29/10/2026, depois do levantamento descrito em `docs/DECISOES.md` ("Votos, presença e projetos
das assembleias", 29/10/2026). Não enviado.

| Casa | O que falta | O que existe hoje |
|---|---|---|
| ALBA (BA) | votos nominais | API de dados abertos (PLE) com proposições e frequência; sessões só com ata, áudio e vídeo |
| ALES (ES) | votos nominais | a mesma API (PLE); votação só no boletim em PDF |
| ALESE (SE) | votos nominais | a mesma API (PLE), sem votos |
| ALEGO (GO) | votos nominais | a mesma API (PLE, `alegodigital.al.go.leg.br`), sem votos |
| ALEPE (PE) | votos nominais e presença | API de dados abertos só com deputados, proposições e pessoal |
| ALAP (AP) | votos nominais e presença | portal do eLegis com a pauta de cada sessão, sem chamada nem voto |
| ALEMA (MA) | votos nominais e presença dos anos anteriores | sistema novo (ALEMALEGIS) com rotas públicas, mas só uma sessão registrada (07/10/2026) |
| ALECE (CE) | presença em Plenário | votações nominais em PDF (usamos); presença não publicada |
| ALEMS (MS) | votos nominais e presença | sistema legislativo com verificação contra acesso por programa (não contornamos) |
| ALERJ (RJ) | votos nominais, presença e proposições | processo legislativo num sistema antigo que não entrega listas |

**Canal:** SIC de cada Casa, pelo portal (confirmar o endereço do formulário na hora do envio).
**Base:** Lei 12.527/2011 (LAI), arts. 8º, §3º (dados abertos, legíveis por máquina) e 10 a 12;
Lei 13.460/2017.

---

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem
exerce função pública. Mostramos, na página de cada deputado, como votou e se estava presente,
com a fonte e a data da consulta.

[Casa] já publica dados abertos de [o que existe], e usamos esses dados. Mas **não encontramos,
em formato aberto, [o que falta]**.

**O que pedimos**
1. **Votos nominais em Plenário** de **01/02/2023 até hoje**: para cada votação, a data e a
   sessão, a matéria votada (tipo, número, ano e ementa), o deputado (nome parlamentar e partido)
   e o voto (sim, não, abstenção, obstrução, ausente etc.), mais o resultado final.
2. **Presença em Plenário** no mesmo período: por sessão e por deputado, com a situação
   (presente, ausente, ausência justificada, licença, em missão).
3. **Formato aberto:** CSV (UTF-8) ou JSON/XML, com dicionário de campos; nada de PDF ou imagem.
   Se já existir uma API ou arquivo com isso, basta indicar o link.
4. **Periodicidade:** atualização diária ou semanal, num endereço estável.
5. A licença de uso, para citarmos a fonte.

Não pedimos CPF, endereço nem qualquer dado pessoal além do nome parlamentar e do partido, que
já são públicos.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
