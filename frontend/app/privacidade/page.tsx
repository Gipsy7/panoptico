import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacidade",
  description: "Como o Panóptico trata os seus dados.",
};

export default function PrivacidadePage() {
  return (
    <article className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold tracking-tight">Privacidade</h1>
        <p className="text-muted-foreground">
          Resumo: o Panóptico funciona sem cadastro e não guarda quem você é nem onde você mora.
        </p>
      </header>

      <Secao titulo="O que acontece com o seu CEP">
        O CEP é usado só para descobrir sua cidade e seu estado. Para isso, ele é enviado ao
        ViaCEP, um serviço público de consulta de CEP. O Panóptico não grava o CEP em banco de
        dados, não o associa a você e não o usa para nenhuma outra finalidade. O resultado da
        consulta fica em memória por até 24 horas apenas para não repetir a mesma consulta, e
        depois é descartado.
      </Secao>

      <Secao titulo="Cadastro e cookies">
        Não há cadastro, login nem cookies de rastreamento ou publicidade. O endereço da página
        (por exemplo, com o CEP buscado) fica no histórico do seu próprio navegador, como em
        qualquer site.
      </Secao>

      <Secao titulo="Registros técnicos">
        Como qualquer servidor na internet, o nosso pode registrar temporariamente dados técnicos
        de acesso (endereço IP, data e hora, página acessada) para segurança e para corrigir
        erros. Esses registros não são usados para identificar pessoas e são apagados
        periodicamente.
      </Secao>

      <Secao titulo="Dados dos parlamentares">
        Os dados dos parlamentares são informações públicas, publicadas pelos próprios órgãos
        oficiais em cumprimento à Lei de Acesso à Informação (Lei nº 12.527/2011). Cada dado tem
        link para a fonte.
      </Secao>

      <Secao titulo="Seus direitos">
        Como não coletamos dados pessoais de quem usa o site, não há dados seus para consultar,
        corrigir ou apagar. Em caso de dúvida sobre a Lei Geral de Proteção de Dados (Lei nº
        13.709/2018), use o link de contato no rodapé do site.
      </Secao>

      <p className="text-xs text-muted-foreground">Última atualização: outubro de 2026.</p>
    </article>
  );
}

function Secao({ titulo, children }: { titulo: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-1">
      <h2 className="text-lg font-semibold">{titulo}</h2>
      <p className="text-muted-foreground">{children}</p>
    </section>
  );
}
