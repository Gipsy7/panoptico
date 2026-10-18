# Notas da curadoria: CPMI do 8 de Janeiro (rascunho)

**Para a revisão humana (cerca de 40 a 60 min, e só depende de acesso manual):** baixar o PDF do Relatório Final pelo navegador (a verificação de segurança do Senado bloqueia o acesso automático e não foi contornada), ler a seção de pedidos de indiciamento (61 nomes segundo a Agência Senado) e extrair a fila com `ingestion.congresso.cpi_indiciamentos`. Só então ligar quem estiver na base com vínculo forte. Nenhuma pessoa foi ligada nesta rodada, porque nenhum documento da CPMI pôde ser lido.

Conferido em 2026-10-11 (página oficial da comissão e página da 23ª Reunião, HTTP 200) e reconferido em 2026-10-18 (uma requisição por vez, User-Agent do projeto).

## Limites encontrados
- **PDF do Relatório Final** (https://legis.senado.leg.br/sdleg-getter/documento?dm=9484688&ts=1697682413143&disposition=inline): em 2026-10-18 ainda devolve a página "Verificação de segurança — Senado Federal" (HTML de 9 KB, sem o PDF). Não contornei. Os anexos da reunião (pauta, ata, resultado) tinham o mesmo bloqueio em 2026-10-11. Por isso a carga automática não extraiu indiciamentos (`cpi_indiciamento_sugestao` não tem a CPMI).
- A página da reunião registra "Aprovado o Relatório Final da comissão"; não registra placar nem a lista de indiciados.

## Pistas (NÃO são fonte; só para achar o documento oficial)
- Agência Senado, 17/10/2023 (https://www12.senado.leg.br/noticias/materias/2023/10/17/relatora-da-cpmi-pede-indiciamento-de-bolsonaro-e-de-mais-60-pessoas) e 18/10/2023 (https://www12.senado.leg.br/noticias/materias/2023/10/18/cpmi-com-20-votos-favoraveis-e-11-contrarios-cpmi-aprova-relatorio-de-eliziane): são notícias do Senado, não o relatório. Informam 61 pedidos de indiciamento no parecer da relatora, Eliziane Gama; aprovação por 20 votos a 11, sem abstenção, em 18/10/2023; envio ao PGR, à Polícia Federal e ao STF; e votos em separado da oposição (não vencidos), que pedem outros indiciamentos. A notícia traz a lista nominal do parecer apresentado em 17/10. O texto aprovado em 18/10 pode diferir (a notícia da votação não diz que houve mudança na lista).
- Nomes da lista da notícia que podem estar na base, para o revisor procurar primeiro no PDF: Jair Bolsonaro, Walter Braga Netto, Augusto Heleno, Luiz Eduardo Ramos, Paulo Sérgio Nogueira, Anderson Torres, Silvinei Vasques, Filipe G. Martins, Carla Zambelli, Antônio Elcio Franco Filho, Tércio Arnaud Tomaz. Não há ligação feita: sem o relatório, nenhum documento oficial lido nomeia essas pessoas neste caso.

## Falta conferir à mão
- Ler o PDF (lista, tipos penais por nome, versão votada) e ligar só quem estiver na base com vínculo forte e citado no texto aprovado. Votos em separado não valem como conclusão da CPMI.
- Encaminhamentos ao MPF/PGR e ao STF e o desfecho de cada um: não confirmado em documento oficial para nenhuma pessoa.
- Os processos do STF sobre os atos de 8 de janeiro (denúncias da PGR, ações penais) são outro conjunto de documentos; só entram aqui se um documento oficial ligar a pessoa a este caso. O portal do STF bloqueia acesso automático.
