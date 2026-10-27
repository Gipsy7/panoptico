# Reserva da API (Oracle Always Free + Cloudflare Tunnel)

API FastAPI em Docker numa VM Ubuntu 24.04 (AMD micro hoje; ARM64 quando houver vaga), exposta por um túnel nomeado da Cloudflare (nenhuma porta aberta). Usa o Neon de produção pela string com pooling. A migração do banco nunca roda aqui: quem migra é o workflow Publicar.

1. Entre na VM: `ssh -i ~/.ssh/panoptico_oracle ubuntu@<IP-DA-VM>`
2. Instale: `curl -fsSL https://raw.githubusercontent.com/Gipsy7/panoptico/main/deploy/reserva/instalar.sh | bash` (ou, com o repositório clonado, `bash deploy/reserva/instalar.sh`). Instala Docker, swap de 2 GB, o código em `/opt/panoptico` e o timer `panoptico-atualizar` (10 em 10 min).
3. Crie o `.env` (a partir de `.env.exemplo`, em `/opt/panoptico/deploy/reserva`) com `DATABASE_URL`, `CORS_ORIGINS` e `TUNNEL_TOKEN`. O dono grava o arquivo por um comando que lê os valores sem exibi-los; ninguém os imprime nem os lê.
4. Suba: `docker compose up -d --build`
5. Teste: `curl localhost:8000/saude`

Logs da atualização: `journalctl -u panoptico-atualizar`. O túnel sobe com `--url http://api:8000` (o `cloudflared` está na mesma rede do compose), então não é preciso configurar hostname no painel da Cloudflare. A VM atual é a micro AMD de 1 GB (`API_WORKERS=2`); a visão geral está em `docs/DEPLOY_GRATUITO.md`.
