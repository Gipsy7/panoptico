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

O Worker avisa o dono pelo estado, não a cada virada (`alertar` em `src/decisao.ts`):

- **queda:** o site ou a API estão na reserva, ou com 3 falhas seguidas sem troca (reserva fora do ar, ou modo `observar`, `principal`, `reserva`). No máximo um e-mail de queda por hora por serviço; se a queda continuar depois disso sem aviso, ele sai nessa hora;
- **volta:** só para quem recebeu o aviso de queda, e só com 10 sucessos seguidos (é também quando o DNS volta da reserva).

Com a VPS oscilando, a regra antiga (um e-mail a cada virada) mandou 37 e-mails em 18/11/2026.

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

## Defesa contra varreduras (firewall)

O `/configurar` grava a fase inteira de regras personalizadas (`gravarFirewall`, até 4 das 5 do plano Free):

1. **Robôs bloqueados** (`ROBOS_BLOQUEADOS`): 403 pelo User-Agent.
2. **Brasil primeiro:** no site (não na API), quem vem de fora do Brasil, não é robô conhecido (`cf.client.bot`) e não é um dos liberados (`ROBOS_SEMPRE_LIBERADOS` em `src/defesa.ts`: buscadores, prévias de link do WhatsApp e redes, IAs que respondem com link) recebe o desafio gerenciado.
3. **Países** (`PAISES_COM_DESAFIO` mais os do vigia): desafio em site e API, menos para robôs conhecidos.
4. **Robôs do vigia:** desafio pelo User-Agent exato, mesmo para robô conhecido.

O campo `cf.bot_management.verified_bot` é do plano pago e não vale nas regras personalizadas (vale só no rate limit).

**Vigia** (`vigiar` em `src/defesa.ts`, a cada 10 minutos no cron): lê a última hora do Analytics. Um país (fora o Brasil) ou User-Agent (fora os liberados) com pelo menos 3.000 pedidos e 30% do total entra no desafio por 24 horas, e o dono recebe um e-mail. Itens ativos são renovados enquanto o volume continuar; vencidos saem sozinhos.

```bash
K=$(cat ~/.panoptico/chave_painel); W=https://panoptico-troca.mikael-dev.workers.dev
curl -s "$W/defesa?chave=$K"                       # o que o vigia pôs no desafio
curl -s "$W/defesa/simular?chave=$K"               # o que ele faria agora, sem gravar
curl -s -X POST "$W/defesa/remover?chave=$K&item=pais:CN"   # ou item=robo:<User-Agent exato, codificado>
```

Depois de `npx wrangler deploy`, a versão nova pode levar um ou dois minutos para responder; um `/configurar` nesse intervalo roda o código anterior.
