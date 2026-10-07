import type { Metadata } from "next";

import { CopiarPix } from "@/components/copiar-pix";

export const metadata: Metadata = {
  title: "Apoie",
  description: "Quanto custa manter o Panóptico no ar e como ajudar, se quiser.",
};

const CHAVE_PIX = "4c02a34c-095e-4990-9bdb-0fe161608f8c";

const CUSTOS = [
  {
    item: "Banco de dados (Neon)",
    valor: "R$ 5 a 20 por mês",
    nota: "Cobrado pelo uso. Há um teto de cerca de R$ 110 por mês mesmo com muito acesso.",
  },
  {
    item: "Hospedagem do site e da API (Vercel)",
    valor: "R$ 0",
    nota: "Plano gratuito.",
  },
  {
    item: "Domínio panoptico.social.br (Registro.br)",
    valor: "cerca de R$ 40 por ano",
    nota: "",
  },
];

export default function ApoiePage() {
  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <p className="sobretitulo">Apoie</p>
        <h1 className="text-3xl tracking-tight">Um site pequeno, com custos pequenos</h1>
        <p className="text-muted-foreground">
          O Panóptico é gratuito, sem anúncios e sem cadastro, e vai continuar assim. Se ele foi
          útil para você, uma doação ajuda a pagar os custos de manter tudo no ar.
        </p>
      </header>

      <section className="flex flex-col gap-3">
        <h2 className="text-2xl">Quanto custa</h2>
        <ul className="lista-fios flex flex-col">
          {CUSTOS.map((c) => (
            <li key={c.item} className="flex flex-col gap-0.5 py-3">
              <div className="flex flex-wrap items-baseline justify-between gap-x-4">
                <span>{c.item}</span>
                <span className="numero">{c.valor}</span>
              </div>
              {c.nota && <span className="text-sm text-muted-foreground">{c.nota}</span>}
            </li>
          ))}
        </ul>
        <p className="text-sm text-muted-foreground">
          O trabalho de desenvolvimento é voluntário. O que entrar de doação vai primeiro para
          esses custos, e o que sobrar fica guardado para os próximos meses.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        <h2 className="text-2xl">Doe por Pix</h2>
        <p className="text-muted-foreground">
          Qualquer valor ajuda. A chave é aleatória: copie e cole na opção &quot;Pix com
          chave&quot; do app do seu banco.
        </p>
        <CopiarPix chave={CHAVE_PIX} />
      </section>

      <section className="nota flex flex-col gap-2 text-sm text-muted-foreground">
        <h2 className="text-lg text-foreground">Independência</h2>
        <p>
          Doações não mudam nada no que o site mostra. Os dados vêm das fontes oficiais, com link
          para cada uma, e a metodologia e o código são públicos.
        </p>
        <p>
          Não aceitamos doações de partidos, mandatos, gabinetes ou campanhas eleitorais. Se
          uma doação assim chegar, ela será devolvida.
        </p>
      </section>
    </article>
  );
}
