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

Testes: `npm test`; tipos: `npm run tipos`.
