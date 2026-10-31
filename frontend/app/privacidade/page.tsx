import type { Metadata } from "next";

import { CONTATO_EMAIL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Privacidade",
  description: "Como o Panóptico trata os seus dados.",
};

export default function PrivacidadePage() {
  return (
    <article className="pagina-secoes">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Seus dados</p>
        <h1 className="titulo-pagina">Privacidade</h1>
        <p className="text-muted-foreground">
          Resumo: o Panóptico funciona sem cadastro e não guarda quem você é nem onde você mora. A
          única exceção é opcional: se você ativar avisos no celular (nos ambientes em que existirem),
          guardamos um endereço técnico do aparelho, descrito abaixo.
        </p>
      </header>

      <Secao titulo="O que acontece com o seu CEP">
        O CEP é usado só para descobrir sua cidade e seu estado. Para isso, ele é enviado ao
        ViaCEP, um serviço público de consulta de CEP. O Panóptico não grava o CEP em banco de
        dados, não o associa a você e não o usa para nenhuma outra finalidade. O resultado da
        consulta fica em memória por até 24 horas apenas para não repetir a mesma consulta, e
        depois é descartado.
      </Secao>

      <Secao titulo="Se você usar a localização">
        O botão &ldquo;Usar minha localização&rdquo; é opcional. A localização é processada no seu
        aparelho, só para achar a sua cidade nos mapas do IBGE. Ela não é enviada a nenhum
        servidor, nem ao Panóptico nem a terceiros, e não é guardada nem aparece no endereço da
        página. Depois de achar a cidade, só o estado e a cidade (o código dela no IBGE) seguem para a busca, que também alimenta, na página inicial, o exemplo de comparação do seu estado e alguns números da sua cidade. Nada disso é guardado no seu navegador.
      </Secao>

      <Secao titulo="Cadastro e cookies">
        Quem visita não precisa de cadastro nem de login, e não há cookies de rastreamento ou publicidade. O endereço da página
        (por exemplo, com o CEP buscado) fica no histórico do seu próprio navegador, como em
        qualquer site.
      </Secao>

      <Secao titulo="O que fica guardado no seu aparelho">
        Em cada perfil de parlamentar, o seu navegador guarda a data da sua última visita e os
        números que apareciam na tela, só para marcar o que mudou quando você voltar. Isso fica
        apenas no seu aparelho (armazenamento local do navegador): não é enviado ao Panóptico nem a
        terceiros. Para apagar, limpe os dados do site no navegador.
      </Secao>

      <Secao titulo="Registros técnicos">
        Como qualquer servidor na internet, o nosso pode registrar temporariamente dados técnicos
        de acesso (endereço IP, data e hora, página acessada) para segurança e para corrigir
        erros. Esses registros não são usados para identificar pessoas e são apagados
        periodicamente.
      </Secao>

      <Secao id="argos" titulo="O Argos, o assistente de perguntas">
        O Argos é um assistente de respostas prontas; não é uma inteligência artificial e não opina.
        O que ele guarda, sem identificar você: (1) as frases que ele não entendeu, para a equipe
        ensiná-lo a entender mais; (2) a sua resposta a &ldquo;Isso ajudou?&rdquo; (sim ou não), com o
        assunto da pergunta e o dia; (3) se você responder &ldquo;Não&rdquo; e depois &ldquo;Pode
        guardar&rdquo;, a conversa daquela tela (até 30 mensagens, as suas e as do Argos).
        Antes de sair do seu aparelho, e de novo no servidor, o texto é limpo: CEP, CPF, telefone,
        e-mail, endereços de internet e qualquer número com 5 ou mais dígitos são apagados. O que
        ele não guarda: endereço IP, identificador de conversa ou de navegador, hora exata (só o dia),
        nome, cadastro ou localização. Os registros servem só para melhorar o assistente, são lidos
        apenas pela equipe, nunca são publicados nem entram nos dados abertos, e são apagados depois
        de 180 dias. Como não há identificação, não dá para saber quais registros são seus: se você
        escreveu algo que não queria ter escrito, mande a frase por e-mail para{" "}
        <a href={`mailto:${CONTATO_EMAIL}`} className="underline underline-offset-2">
          {CONTATO_EMAIL}
        </a>{" "}
        e ela será apagada. A posição do botão do Argos na tela fica só no seu navegador, como
        preferência, e não é enviada a ninguém.
      </Secao>

      <Secao id="avisos" titulo="Avisos no celular (quando disponíveis)">
        Alguns ambientes do site podem oferecer avisos no celular. Eles só existem se você tocar em
        &ldquo;Avisar sobre novidades&rdquo; e permitir as notificações no navegador; quem não ativa
        não tem nada guardado. Se você ativar, guardamos (1) o endereço técnico que o seu navegador
        fornece para receber o aviso, com as duas chaves que o acompanham, e (2) a lista do que o
        aparelho acompanha (parlamentares, projetos federais e lugares, como uma cidade, um estado
        ou o Brasil, com os assuntos e a frequência escolhidos). O lugar seguido é o que você
        escolheu acompanhar, não a sua localização: não guardamos nome, telefone, e-mail, CEP nem
        posição do aparelho. O fundamento é o seu consentimento (Lei nº 13.709/2018, art.
        7º, inciso I), que você retira quando quiser. O aviso passa pelo serviço de notificações do
        seu navegador (por exemplo, o do Google, da Mozilla, da Apple ou da Microsoft), que o entrega
        ao aparelho. Enviamos no máximo 1 aviso por dia (ou 1 por semana), com votos, andamento de
        projetos e registros oficiais e, dos lugares seguidos, obras, emendas pagas, leis, votações
        e dados novos publicados pelas fontes. Para cancelar, use o
        botão do próprio perfil ou a página &ldquo;Avisos neste aparelho&rdquo; (que só existe onde
        os avisos estão ligados): o cancelamento apaga na hora o endereço e a
        lista, sem cópia. Uma inscrição que fica 180 dias sem receber nenhum aviso é apagada, e esses
        dados ficam fora das cópias de segurança (backups).
      </Secao>

      <Secao id="avisar-erro" titulo="Avisar um erro e pedir direito de resposta">
        Em cada perfil há o botão &ldquo;Achou um erro neste número?&rdquo; e o pedido de resposta
        de quem é citado. O que guardamos: o texto que você escreve, a página e a seção a que ele
        se refere, o tipo de erro e a data. O e-mail ou telefone é opcional no aviso de erro e serve
        só para responder; no pedido de resposta serve para confirmar a identidade pelo canal
        oficial. Esse contato é apagado em 180 dias, fica fora das cópias de segurança (backups) e
        nunca é publicado. Não guardamos o seu IP (o limite de 5 avisos por hora usa apenas uma
        contagem temporária, que não identifica ninguém). Não escreva CPF, endereço ou dados de
        terceiros. Uma pessoa lê cada aviso e confere com a fonte oficial; nada muda no site
        sem essa conferência. Cada correção feita aparece em &ldquo;Sobre as fontes&rdquo;, sem
        dizer quem avisou. A resposta de quem é citado só é publicada depois de revisão e de
        confirmar a identidade, sem edição além de tirar dados pessoais.
      </Secao>

      <Secao id="contagem" titulo="Contagem de acessos">
        Para saber se o site está sendo útil, contamos acessos de forma agregada: só totais por dia.
        Contamos (1) quantas visitas houve, (2) quais páginas foram abertas, só o endereço da
        página, nunca o que vem depois do ponto de interrogação, como o CEP, (3) de que tipo de
        lugar a pessoa veio (WhatsApp, Google, outros buscadores, redes sociais, outro site ou
        direto), (4) se o aparelho é de toque (celular ou tablet) ou computador, e (5) quantas vezes
        alguns recursos foram usados (busca por CEP, uso da localização, abrir o Argos, compartilhar
        no WhatsApp, copiar o Pix), só o nome do recurso. Não guardamos o CEP, o endereço IP, o
        navegador, a hora, nem qualquer identificador seu; a &ldquo;visita&rdquo; é marcada só na
        memória da aba do navegador, sem cookie, e some quando você fecha a aba. Por isso uma visita
        não equivale a uma pessoa. Não contamos robôs, quem pede &ldquo;Não rastrear&rdquo; ao navegador
        (ou usa o Global Privacy Control) nem quem bloqueia scripts. Os totais são lidos apenas pelo
        dono do site, numa área protegida por senha, e não são publicados.
      </Secao>

      <Secao titulo="Dados dos parlamentares">
        Os dados dos parlamentares são informações públicas, publicadas pelos próprios órgãos
        oficiais em cumprimento à Lei de Acesso à Informação (Lei nº 12.527/2011). Cada dado tem
        link para a fonte.
      </Secao>

      <Secao titulo="Seus direitos">
        Quem não ativa os avisos não tem dados pessoais guardados pelo site, então não há dados seus
        para consultar, corrigir ou apagar. Quem ativa pode ver o que o aparelho acompanha e apagar
        tudo a qualquer momento, pelo cancelamento descrito acima. Em caso de dúvida sobre a Lei Geral de Proteção de Dados (Lei nº
        13.709/2018), escreva para{" "}
        <a href={`mailto:${CONTATO_EMAIL}`} className="underline underline-offset-2">
          {CONTATO_EMAIL}
        </a>
        .
      </Secao>

      <p className="text-sm text-muted-foreground">Última atualização: novembro de 2026.</p>
    </article>
  );
}

function Secao({ titulo, children, id }: { titulo: string; children: React.ReactNode; id?: string }) {
  return (
    <section id={id} className="flex scroll-mt-20 flex-col gap-1">
      <h2 className="text-lg font-semibold">{titulo}</h2>
      <p className="text-muted-foreground">{children}</p>
    </section>
  );
}
