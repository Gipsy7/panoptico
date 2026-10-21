# ALAP: gastos da CEAP (cota para o exercício da atividade parlamentar) em formato aberto e confirmação do robots.txt

**Para:** Assembleia Legislativa do Estado do Amapá (ALAP), Serviço de Informação ao Cidadão (e-SIC) e Portal da Transparência
**Canal:** formulário do SIC no portal da Casa (https://www.al.ap.gov.br, "Transparência"; confirmar o endereço na hora do envio)
**Base:** Lei 12.527/2011 (LAI), arts. 8º, §3º (dados abertos, legíveis por máquina) e 10 a 12; Lei 13.460/2017

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce função pública. Mostramos, na página de cada deputado, o que ele gasta, com a fonte e a data da consulta.

O Portal da Transparência da ALAP publica a CEAP por gabinete e mês (`www.al.ap.gov.br/transparencia`, tela "CEAP"), mas **só em página**, escolhendo gabinete e mês um a um. E o endereço `https://www.al.ap.gov.br/robots.txt` responde **403 (Acesso negado)**: não conseguimos saber se a Casa autoriza a leitura automatizada dessas páginas. Como a regra do projeto é não contornar nenhum bloqueio, **não coletamos** essa tela até recebermos orientação.

**O que pedimos**
1. **Autorização expressa** (ou a indicação do canal próprio) para a leitura automatizada, com pausa entre as requisições, das páginas da CEAP no Portal da Transparência; e a correção do `robots.txt` (hoje 403) para que ele publique a política da Casa.
2. Preferencialmente, **o mesmo conteúdo em arquivo aberto**: CSV (UTF-8) ou JSON, com dicionário de campos, de **01/01/2025 até hoje**, uma linha por despesa com: mês e ano de competência, gabinete/deputado (nome parlamentar), **tipo de despesa (a rubrica da CEAP)**, data do documento e valor. Não precisamos do CPF nem do CNPJ do fornecedor; o nome do fornecedor só se for pessoa jurídica.
3. Atualização mensal, em endereço estável.
4. A licença de uso, para citarmos a fonte.

Não pedimos CPF, endereço nem qualquer dado pessoal além do nome parlamentar, que já é público.

Atenciosamente,
[nome], Panóptico — contato@panoptico.social.br
