# Senado Federal: valor mensal da verba dos gabinetes dos senadores

**Para:** Senado Federal, Serviço de Informação ao Cidadão (SIC), pelo formulário de acesso à informação do Portal da Transparência
**Base:** Lei 12.527/2011 (LAI), arts. 8º (divulgação ativa) e 10 a 12

Prezados,

O Panóptico (panoptico.social.br) é um projeto sem fins lucrativos de transparência sobre quem exerce mandato. Na página de cada senador mostramos quanto custa o mandato por mês: salário, cota (CEAPS), auxílio-moradia e verba para pagar a equipe do gabinete, cada valor com o ato que o fixa. Só registramos o número que o próprio Senado publica.

Para a Câmara, o valor da verba de gabinete está publicado (R$ 165.806,07, Ato da Mesa nº 243/2026). Para o Senado, não localizamos o valor em reais nas páginas de transparência nem na base de normas administrativas (o guia de gabinetes cita o "valor da verba do gabinete" sem o número). Pedimos:

1. **O valor mensal vigente** da verba destinada à composição de cargos em comissão de cada gabinete de senador (ou, se não houver valor em reais, o critério vigente e o custo mensal máximo que ele permite).
2. **O ato normativo** que o fixa (número, data, link e início da vigência) e o histórico desde 2023.
3. **A publicação permanente** desses dados na página de transparência dos senadores, ao lado da CEAPS e do auxílio-moradia.

Não pedimos dado pessoal de servidor.

Atenciosamente,
[nome], Panóptico (contato@panoptico.social.br)

## Controle

| Situação | Data de envio | Protocolo | Resposta |
|---|---|---|---|
| a enviar |  |  |  |

Quando o Senado responder, preencha a linha `senador,verba_gabinete` de `data/custo_mandato_congresso.csv`, copie para `backend/app/dados/` e rode `pytest tests/test_custo_mandato.py` (hoje `test_valores_conferidos_na_fonte` espera `None`).
