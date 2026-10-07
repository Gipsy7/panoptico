import type { Metadata } from "next";

import { CopiarPix } from "@/components/copiar-pix";

export const metadata: Metadata = {
  title: "Apoie",
  description: "Quanto custa manter o Panóptico no ar e como ajudar, se quiser.",
};

const CHAVE_PIX = "4c02a34c-095e-4990-9bdb-0fe161608f8c";
// BR Code estático (padrão do Banco Central), sem valor definido: quem doa escolhe o valor.
// O QR code em public/pix-qr.svg foi gerado a partir deste mesmo texto; se a chave mudar,
// é preciso gerar os dois de novo (o final "6304XXXX" é um CRC16 do restante).
const PIX_COPIA_E_COLA =
  "00020126580014br.gov.bcb.pix01364c02a34c-095e-4990-9bdb-0fe161608f8c" +
  "5204000053039865802BR5916MIKAEL FRANCISCO6008BLUMENAU62070503***63044E2F";

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
          Qualquer valor ajuda. Aponte a câmera do app do seu banco para o código ou, no
          celular, copie o código &quot;Pix copia e cola&quot;.
        </p>
        <div className="flex flex-col gap-6 sm:flex-row sm:items-start">
          {/* eslint-disable-next-line @next/next/no-img-element -- SVG estático e pequeno */}
          <img
            src="/pix-qr.svg"
            alt="QR code para doar ao Panóptico por Pix"
            width={200}
            height={200}
            className="size-50 border border-border"
          />
          <div className="flex flex-col gap-5">
            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted-foreground">Pix copia e cola</span>
              <CopiarPix texto={PIX_COPIA_E_COLA} rotulo="Copiar código" />
            </div>
            <div className="flex flex-col gap-2">
              <span className="text-sm text-muted-foreground">Ou pela chave aleatória</span>
              <span className="numero text-sm break-all select-all">{CHAVE_PIX}</span>
              <CopiarPix texto={CHAVE_PIX} rotulo="Copiar chave" />
            </div>
            <p className="text-sm text-muted-foreground">
              Na confirmação, o app mostra o nome do responsável pelo projeto, Mikael Francisco.
            </p>
          </div>
        </div>
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
