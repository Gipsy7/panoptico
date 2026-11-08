import type { Metadata } from "next";
import Link from "next/link";

import { CopiarPix } from "@/components/copiar-pix";
import { CONTATO_EMAIL } from "@/lib/site";

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

// Atualizado em out/2026, com a mudança para o servidor próprio (ver docs/DECISOES.md).
const CUSTOS = [
  {
    item: "Servidor principal (VPS Locaweb, em São Paulo)",
    valor: "R$ 79,90 por mês",
    nota: "Banco de dados, API, site e atualização diária dos dados, numa máquina só.",
  },
  {
    item: "Cópia de reserva (Vercel e banco Neon)",
    valor: "cerca de R$ 5 por mês",
    nota: "Uma versão do site guardada para entrar no ar sozinha se o servidor principal cair. Cobrada pelo uso.",
  },
  {
    item: "Proteção, cache e endereço (Cloudflare)",
    valor: "R$ 0",
    nota: "Plano gratuito.",
  },
  {
    item: "Backup diário do banco (Oracle Cloud)",
    valor: "R$ 0",
    nota: "Plano gratuito.",
  },
  {
    item: "Domínio panoptico.social.br (Registro.br)",
    valor: "cerca de R$ 40 por ano",
    nota: "",
  },
];

// Formas de ajudar além do dinheiro (protótipo 3 do redesenho): cada uma com a cor de um assunto.
const FORMAS = [
  {
    tema: "dinheiro",
    titulo: "Pix",
    texto: "Qualquer valor, uma vez ou todo mês. O código e a chave estão logo abaixo.",
    acao: "Doar por Pix",
    href: "#pix",
  },
  {
    tema: "votos",
    titulo: "Divulgue",
    texto: "Ache quem representa a sua cidade e mande o cartão nos grupos de WhatsApp.",
    acao: "Achar a minha cidade",
    href: "/#cep",
  },
  {
    tema: "escolas",
    titulo: "Ajude nos dados",
    texto: "Viu um número errado? Toda seção tem \"Avisar um erro\". Veja também o que cada fonte cobre e o que falta.",
    acao: "Ver as fontes",
    href: "/sobre-as-fontes",
  },
  {
    tema: "eleicoes",
    titulo: "Código aberto",
    texto: "O código é livre (AGPL) e os dados são abertos: dá para contribuir ou reusar.",
    acao: "Ver no GitHub",
    href: "https://github.com/Gipsy7/panoptico",
  },
] as const;

export default function ApoiePage() {
  return (
    <article data-largura="larga" className="pagina-secoes">
      <header className="flex max-w-3xl flex-col gap-2">
        <p className="sobretitulo">Apoie</p>
        <h1 className="titulo-pagina">Um site público precisa de gente pública</h1>
        <p className="text-muted-foreground">
          O Panóptico é gratuito, sem anúncios e sem cadastro, e vai continuar assim. Se ele foi
          útil para você, há quatro jeitos de ajudar, e só um deles é dinheiro.
        </p>
      </header>

      <div className="grid grid-cols-1 items-start gap-[var(--esp-10)] lg:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)] lg:gap-10">
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {FORMAS.map((f) => (
            <li
              key={f.titulo}
              className="flex flex-col gap-2 rounded-[var(--raio)] border border-t-4 border-border bg-card p-4"
              style={{ borderTopColor: `var(--tema-${f.tema})` }}
            >
              <h2 className="text-xl">{f.titulo}</h2>
              <p className="text-sm text-muted-foreground">{f.texto}</p>
              {f.href.startsWith("http") ? (
                <a href={f.href} className="botao-linha mt-auto self-start" rel="noopener">
                  {f.acao}
                </a>
              ) : (
                <Link href={f.href} className="botao-linha mt-auto self-start">
                  {f.acao}
                </Link>
              )}
            </li>
          ))}
        </ul>

        <section
          aria-labelledby="custos-titulo"
          className="flex flex-col gap-3 rounded-[var(--raio)] border border-t-4 border-border bg-card p-4"
          style={{ borderTopColor: "var(--tema-dinheiro)" }}
        >
          <h2 id="custos-titulo" className="text-xl">
            Quanto custa manter
          </h2>
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
      </div>

      <section id="pix" className="flex scroll-mt-24 flex-col gap-3">
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
        <p className="text-sm text-muted-foreground">
          Quer ter o seu nome na{" "}
          <Link href="/apoiadores" className="underline underline-offset-2">
            lista de apoiadores
          </Link>
          ? Escreva para{" "}
          <a href={`mailto:${CONTATO_EMAIL}`} className="underline underline-offset-2">
            {CONTATO_EMAIL}
          </a>{" "}
          autorizando. Sem essa autorização, nenhum nome é publicado.
        </p>
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
