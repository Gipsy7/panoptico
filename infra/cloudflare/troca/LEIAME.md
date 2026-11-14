# Troca automática de origem (Cloudflare Worker)

Worker com Cron (1 min) que testa as origens e troca o destino dos CNAME do site (`@`) e da `api` pela API do Cloudflare. Não fica no caminho das requisições.

1. `npm install`
2. Criar o KV: `npx wrangler kv namespace create ESTADO` e colar o `id` em `wrangler.toml`.
3. Preencher em `wrangler.toml`: `ZONE_ID`, `API_RESERVA` (`<uuid>.cfargotunnel.com`), `TESTE_API_RESERVA` e conferir os demais destinos e URLs.
4. Segredos: `npx wrangler secret put CF_TOKEN` (token com Zone > DNS > Edit só nessa zona) e `npx wrangler secret put CHAVE_PAINEL`.
5. `npx wrangler deploy`

Regras: 2 falhas seguidas da principal levam à reserva (se ela estiver saudável); 10 sucessos seguidos trazem de volta. Falha = timeout de 8 s, status >= 500, 402, ou 403 com `DEPLOYMENT_DISABLED`/`Payment required`; na API, `/saude` com `banco` diferente de `ok`.

## Trocar o modo
Valores: `auto`, `principal`, `reserva`, `observar` (só registra no log, sem mexer no DNS). O estado fica numa chave só (`estado`) do KV:

```
npx wrangler kv key get estado --binding ESTADO
npx wrangler kv key put estado '{"site":{"ativo":"principal","falhas":0,"sucessos":0,"modo":"observar"},"api":{"ativo":"principal","falhas":0,"sucessos":0,"modo":"auto"}}' --binding ESTADO
```

Ao gravar, `ativo` deve refletir o DNS real.

## Ler o estado
`https://<worker>.workers.dev/estado?chave=<CHAVE_PAINEL>`, ou `npx wrangler tail` para o log.

Release (`release.panoptico.social.br`, `api-release.`): nunca entra na troca. O Worker não testa nem troca endereço de release; se algum aparecer em `wrangler.toml`, o cron não faz nada e `/preparar` recusa (`enderecosDeRelease`).

Testes: `npm test`; tipos: `npm run tipos`.

## Alertas por e-mail

O Worker avisa o dono nas viradas, nunca a cada minuto (`eventoDeAlerta` em `src/decisao.ts`):

- o site ou a API pararam e o endereço foi para a reserva;
- voltaram para a VPS;
- pararam e **não** houve troca (reserva fora do ar, ou modo `observar`, `principal`, `reserva`), e depois quando voltam a responder.

É o único aviso que funciona com a VPS inteira fora do ar; os outros (fluxo, cargas com erro, disco) saem da própria VPS (`deploy/vps/LEIAME.md`, "Alertas por e-mail ao dono").

O envio é por SMTP na porta 465, direto do Worker (`src/email.ts`, sem biblioteca). Um alerta que falha só escreve no log; a troca não depende dele. Sem as variáveis abaixo, o Worker funciona como antes e só registra no log o que teria avisado.

```
npx wrangler secret put SMTP_SENHA         # senha de aplicativo da conta que envia (nunca a da conta)
npx wrangler secret put SMTP_USUARIO       # a conta que envia
npx wrangler secret put ALERTA_EMAIL_PARA  # quem recebe
npm run deploy
```

`SMTP_HOST` é opcional (padrão `smtp.zoho.com`). Depois do deploy, espere cerca de 1 minuto antes de mexer no modo. Para ver os alertas no log: `npx wrangler tail` e procure por `alerta`.

Ainda não foi testado contra o servidor de e-mail de verdade (só com um servidor de mentira nos testes): o primeiro envio real é a conferência.
