import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import {
  type Cobertura,
  type CoberturaContagem,
  type CoberturaPedido,
  type CoberturaSecao,
  getCobertura,
} from "@/lib/api";
import { idDaCasa } from "@/lib/cobertura";
import { UFS } from "@/lib/ufs";

export const metadata: Metadata = {
  title: "O que existe e o que falta",
  description:
    "Para cada estado e cada cargo, o que o Panóptico mostra, o que a fonte não permite buscar e o que ainda falta, com o motivo.",
};

type Situacao = CoberturaSecao["situacao"];

// Ícones só de forma (sem cor de bom/ruim): o texto diz a situação por extenso.
const SITUACAO: Record<Situacao, { icone: string; curto: string }> = {
  sim: { icone: "●", curto: "Tem" },
  parcial: { icone: "◐", curto: "Em parte" },
  bloqueado: { icone: "⊘", curto: "A fonte bloqueia acesso automático" },
  pedido: { icone: "✉", curto: "Pedido de acesso redigido" },
  sem_fonte: { icone: "○", curto: "O órgão não publica" },
};
const ORDEM: Situacao[] = ["sim", "parcial", "bloqueado", "pedido", "sem_fonte"];

const SECOES: Record<string, string> = {
  gastos: "Gastos do gabinete",
  votos: "Como votou",
  presenca: "Presença em votações",
  projetos: "Projetos de lei",
  emendas: "Dinheiro de emendas",
  salario: "Salário",
  agenda: "Agenda",
  atos: "Atos oficiais publicados",
  bens_campanha: "Bens e campanha",
};

const NOME_UF = new Map(UFS.map((u) => [u.sigla, u.nome]));

function lerUf(sp: { [k: string]: string | string[] | undefined }): string | undefined {
  const bruto = Array.isArray(sp.uf) ? sp.uf[0] : sp.uf;
  const uf = bruto?.toUpperCase();
  return uf && /^[A-Z]{2}$/.test(uf) ? uf : undefined;
}

export default function CoberturaPage({ searchParams }: PageProps<"/sobre-as-fontes/cobertura">) {
  return (
    <article className="pagina-secoes">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Método</p>
        <h1 className="titulo-pagina">O que existe e o que falta</h1>
        <p className="text-muted-foreground">
          O Panóptico só mostra o que as fontes oficiais publicam. Quando um dado não aparece, o
          motivo está aqui: o órgão não publica, bloqueia acesso automático, o acesso foi pedido e
          ainda não chegou, ou o Panóptico ainda não lê essa fonte. A mesma regra vale para todos
          os estados e para todos os partidos. Aqui está a situação de cada cargo e de cada tipo
          de dado, do mesmo jeito para todos.
        </p>
        <p className="text-sm text-muted-foreground">
          Voltar para{" "}
          <Link href="/sobre-as-fontes" className="underline underline-offset-2">
            Sobre as fontes
          </Link>
          .
        </p>
      </header>

      <Revelacao fallback={<EsqueletoSecao rotulo="Carregando…" secoes={2} />}>
        {searchParams.then((sp) => (
          <Conteudo uf={lerUf(sp)} />
        ))}
      </Revelacao>
    </article>
  );
}

async function Conteudo({ uf }: { uf?: string }) {
  const resultado = await getCobertura(uf);
  if (!resultado.ok) {
    return <AvisoErro titulo="Não foi possível carregar" mensagem={resultado.mensagem} />;
  }
  const d = resultado.dados;
  return (
    <>
      <section aria-labelledby="nacional-titulo" className="revelar flex flex-col gap-3">
        <h2 id="nacional-titulo" className="text-2xl">
          No Brasil inteiro
        </h2>
        <Contagens c={d.nacional} unidade="combinações de cargo e tipo de dado" />
        <Legenda />
      </section>

      <section aria-labelledby="estado-titulo" className="revelar flex flex-col gap-3">
        <h2 id="estado-titulo" className="text-2xl">
          {d.uf ? `Em ${NOME_UF.get(d.uf) ?? d.uf}` : "Escolha um estado"}
        </h2>
        <SeletorUf ufs={d.ufs} atual={d.uf} />
        {d.uf && d.resumo_uf && (
          <>
            <Contagens
              c={d.resumo_uf}
              unidade={`combinações de cargo e tipo de dado em ${NOME_UF.get(d.uf) ?? d.uf}, incluindo Câmara dos Deputados e Senado`}
            />
            <ul className="flex flex-col gap-4">
              {d.casas.map((casa) => (
                <CartaoCasa key={`${casa.casa}-${casa.cargo}`} casa={casa} />
              ))}
            </ul>
          </>
        )}
        <FonteRodape fonte={d.fonte_nome} url={d.fonte_url} atualizadoEm={d.atualizado_em} />
      </section>
    </>
  );
}

function SeletorUf({ ufs, atual }: { ufs: string[]; atual: string | null }) {
  return (
    <form key={atual ?? ""} method="get" className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <label className="flex min-w-0 flex-col gap-1 text-sm font-medium sm:w-72">
        Estado
        <select
          name="uf"
          defaultValue={atual ?? ""}
          className="campo-filtro font-normal"
        >
          <option value="" disabled>
            Escolha…
          </option>
          {ufs.map((u) => (
            <option key={u} value={u}>
              {NOME_UF.get(u) ?? u}
            </option>
          ))}
        </select>
      </label>
      <button type="submit" className="botao">
        Ver o estado
      </button>
    </form>
  );
}

function Contagens({ c, unidade }: { c: CoberturaContagem; unidade: string }) {
  return (
    <div className="flex flex-col gap-2">
      <ul className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        {ORDEM.map((s) => (
          <li key={s} className="rounded-xl bg-card p-3 ring-1 ring-foreground/10">
            <span className="block text-2xl tabular-nums">{c[s]}</span>
            <span className="text-sm text-muted-foreground">
              <span aria-hidden="true">{SITUACAO[s].icone} </span>
              {SITUACAO[s].curto}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        Total: {c.total} {unidade}.
      </p>
    </div>
  );
}

function Legenda() {
  return (
    <details className="text-sm text-muted-foreground">
      <summary className="cursor-pointer">O que cada situação quer dizer</summary>
      <ul className="mt-2 flex flex-col gap-1">
        <li>Tem: o dado aparece no site, com fonte e data.</li>
        <li>Em parte: aparece só uma parte (um recorte, ou nem todas as cidades).</li>
        <li>
          A fonte bloqueia acesso automático: o órgão impede a coleta por programa. Não
          contornamos o bloqueio.
        </li>
        <li>Pedido de acesso redigido: o pedido ao órgão (com a lei de acesso à informação) está escrito e aberto ao público; a data é a de quando foi redigido.</li>
        <li>O órgão não publica: não encontramos esse dado em formato aberto.</li>
      </ul>
    </details>
  );
}

function CartaoCasa({ casa }: { casa: Cobertura["casas"][number] }) {
  return (
    <li
      id={idDaCasa(casa.casa)}
      className="scroll-mt-20 flex flex-col gap-2 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
    >
      <h3 className="font-medium">
        {casa.casa} <span className="text-sm text-muted-foreground">({casa.cargo})</span>
      </h3>
      <ul className="lista-fios flex flex-col">
        {casa.secoes.map((s) => (
          <LinhaSecao key={s.secao} s={s} />
        ))}
      </ul>
    </li>
  );
}

function LinhaSecao({ s }: { s: CoberturaSecao }) {
  const { icone, curto } = SITUACAO[s.situacao];
  return (
    <li className="flex flex-col gap-0.5 py-2">
      <span className="flex flex-wrap items-baseline justify-between gap-x-3">
        <span className="font-medium">{SECOES[s.secao] ?? s.secao}</span>
        <span className="text-sm">
          <span aria-hidden="true">{icone} </span>
          {s.situacao === "pedido" ? textoPedido(s.pedidos) : curto}
        </span>
      </span>
      {s.motivo && s.situacao !== "sim" && (
        <span className="text-sm text-muted-foreground">{s.motivo}</span>
      )}
      {s.pedidos.length > 0 && (
        <span className="text-sm text-muted-foreground">
          Pedido:{" "}
          {s.pedidos.map((p, i) => (
            <span key={p.arquivo}>
              {i > 0 && "; "}
              <a
                href={p.url}
                target="_blank"
                rel="noopener noreferrer"
                className="underline underline-offset-2"
              >
                {p.orgao}
              </a>
            </span>
          ))}
        </span>
      )}
    </li>
  );
}

function textoPedido(pedidos: CoberturaPedido[]): string {
  const data = pedidos.find((p) => p.data)?.data;
  return data ? `Pedido de acesso redigido em ${data}` : "Pedido de acesso redigido";
}
