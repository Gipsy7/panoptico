# Marca do Panóptico

Arte oficial para divulgar o projeto: redes sociais, imprensa, apresentações.

Pode usar estes arquivos para falar do Panóptico. Não use o nome nem a logo para se passar pelo projeto
ou para sugerir que ele apoia alguém (pessoa, partido, campanha ou empresa).

## Cores e fontes

| Uso | Cor |
|---|---|
| Fundo (papel) | `#f4f1ea` |
| Texto | `#141414` |
| Texto de apoio | `#6a665f` |
| Bronze (sol, ".social", destaques) | `#9c6a2a` |
| Nome na logo (só na logo) | `#12263a` |
| Fundo escuro / bronze no escuro | `#1c1a17` / `#c9954a` |

Fontes: Newsreader (títulos) e Geist (texto), ambas do Google Fonts. Detalhes em `docs/DESIGN.md`, seção "Marca".

## Arquivos (`redes-sociais/`)

| Arquivo | Tamanho | Uso |
|---|---|---|
| `perfil-claro.png`, `perfil-escuro.png` | 1080×1080 | Foto de perfil (cabe no recorte redondo) |
| `youtube-banner.png` | 2560×1440 | Banner do canal (texto na área segura de 1546×423) |
| `youtube-marca-dagua-disco.png` | 300×300 | Marca d'água dos vídeos (recomendada) |
| `youtube-marca-dagua-vazada.png` | 300×300 | Marca d'água sem disco (só para vídeo escuro) |
| `youtube-miniatura-modelo.png` | 1280×720 | Modelo de miniatura de vídeo |
| `descricao-youtube.txt` | | Descrição do canal (até 1.000 caracteres) |
| `x-capa.png` | 1500×500 | Capa do X |
| `facebook-capa.png` | 1640×624 | Capa do Facebook |
| `linkedin-capa.png` | 1584×396 | Capa do LinkedIn |
| `post-apresentacao.png` | 1080×1350 | Post de apresentação (Instagram, Facebook) |
| `story.png` | 1080×1920 | Story e status do WhatsApp |
| `logo-claro.svg`, `logo-escuro.svg`, `marca-sol.svg` | vetor | Logo para impressão e apresentações |

## Regerar

As imagens saem de `scripts/gerar-pack-redes.mjs`, que lê a logo de `frontend/lib/logo-caminhos.ts`
(usa o Playwright do `frontend/`). Na raiz do repositório:

```bash
node scripts/gerar-pack-redes.mjs
```

Para mudar textos ou criar uma peça, edite a lista `pecas` no script. Faça commit só quando a arte estiver
fechada: cada versão dos PNGs fica no histórico.
