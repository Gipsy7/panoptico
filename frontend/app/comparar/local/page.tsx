import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { FotoVereador } from "@/components/camara-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import {
  type ComparacaoLocal,
  type LadoLocal,
  getAssembleia,
  getCamara,
  getComparacaoLocal,
  getVereador,
} from "@/lib/api";
import { formatarData } from "@/lib/formato";

const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);
const PCT = (v: number) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;

export async function generateMetadata({ searchParams }: PageProps<"/comparar/local">): Promise<Metadata> {
  const sp = await searchParams;
  const a = texto(sp.a);
  const b = texto(sp.b);
  if (!a || !b) return { title: "Comparar vereadores e deputados estaduais" };
  const resultado = await getComparacaoLocal(a, b);
  if (!resultado.ok) return { title: "Comparar vereadores e deputados estaduais" };
  const titulo = `${resultado.dados.a.nome} × ${resultado.dados.b.nome}`;
  return {
    title: titulo,
    description: `Projetos, presença e votos de ${resultado.dados.a.nome} e ${resultado.dados.b.nome}, lado a lado, com dados da própria casa.`,
  };
}

export default function CompararLocalPage({ searchParams }: PageProps<"/comparar/local">) {
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl tracking-tight">Comparar na mesma casa</h1>
        <p className="text-muted-foreground">
          Dois vereadores da mesma câmara, ou dois deputados da mesma assembleia, lado a lado. Só
          na mesma casa, porque é onde a pauta e as votações são as mesmas.
        </p>
      </header>
      <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
        {searchParams.then((sp) => (
          <Conteudo a={texto(sp.a)} b={texto(sp.b)} />
        ))}
      </Revelacao>
    </div>
  );
}

async function Conteudo({ a, b }: { a?: string; b?: string }) {
  if (!a) {
    return (
      <p className="text-muted-foreground">
        Abra o perfil de um vereador ou deputado estadual e use &quot;Comparar com outro desta
        casa&quot;. Você encontra os perfis pela{" "}
        <Link href="/" className="underline underline-offset-2">
          busca por CEP ou por nome
        </Link>
        .
      </p>
    );
  }
  if (!b) return <Escolher a={a} />;
  const resultado = await getComparacaoLocal(a, b);
  if (!resultado.ok) return <AvisoErro titulo="Não deu para comparar" mensagem={resultado.mensagem} />;
  return <Resultado dados={resultado.dados} />;
}

/** Com o primeiro escolhido, a lista dos colegas da mesma casa. */
async function Escolher({ a }: { a: string }) {
  const primeiro = await getVereador(a);
  if (!primeiro.ok) return <AvisoErro titulo="Não encontrado" mensagem={primeiro.mensagem} />;
  const v = primeiro.dados;
  const casa =
    v.casa === "camara" && v.municipio_ibge ? await getCamara(v.municipio_ibge) : await getAssembleia(v.uf);
  const colegas = casa.ok ? casa.dados.itens.filter((c) => c.id !== v.id) : [];
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <FotoVereador vereador={v} tamanho={48} />
        <div>
          <p className="font-semibold">{v.nome}</p>
          <p className="text-sm text-muted-foreground">{v.partido}</p>
        </div>
      </div>
      <h2 className="text-xl">Com quem você quer comparar?</h2>
      <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
        {colegas.map((c) => (
          <li key={c.id} className="border-b border-border">
            <Link
              href={`/comparar/local?a=${v.id}&b=${c.id}`}
              className="flex items-center gap-3 py-2 hover:bg-accent/50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
            >
              <FotoVereador vereador={c} tamanho={36} />
              <span className="min-w-0">
                <span className="block truncate font-medium">{c.nome}</span>
                <span className="text-xs text-muted-foreground">
                  {[c.partido, c.titular ? null : "suplente"].filter(Boolean).join(" · ")}
                </span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

type Linha = { rotulo: string; a: string; b: string };

function linhas(a: LadoLocal, b: LadoLocal): Linha[] {
  const presenca = (l: LadoLocal) => (l.presenca ? `${l.presenca.presencas} de ${l.presenca.sessoes}` : "—");
  const pessoal = (l: LadoLocal, campo: "grau_instrucao" | "ocupacao") => l.pessoais?.[campo] ?? "—";
  return [
    { rotulo: "Projetos", a: String(a.projetos), b: String(b.projetos) },
    { rotulo: "Proposições", a: String(a.proposicoes), b: String(b.proposicoes) },
    { rotulo: "Presença nas sessões", a: presenca(a), b: presenca(b) },
    { rotulo: "Votações nominais em que votou", a: String(a.votacoes), b: String(b.votacoes) },
    {
      rotulo: "Votos recebidos na eleição",
      a: a.votos_recebidos?.toLocaleString("pt-BR") ?? "—",
      b: b.votos_recebidos?.toLocaleString("pt-BR") ?? "—",
    },
    {
      rotulo: "Idade",
      a: a.pessoais?.idade != null ? `${a.pessoais.idade} anos` : "—",
      b: b.pessoais?.idade != null ? `${b.pessoais.idade} anos` : "—",
    },
    { rotulo: "Escolaridade", a: pessoal(a, "grau_instrucao"), b: pessoal(b, "grau_instrucao") },
    { rotulo: "Ocupação declarada", a: pessoal(a, "ocupacao"), b: pessoal(b, "ocupacao") },
  ];
}

function Tabela({ titulo, id, a, b, itens }: { titulo: string; id: string; a: LadoLocal; b: LadoLocal; itens: Linha[] }) {
  return (
    <section aria-labelledby={id} className="revelar flex flex-col gap-3">
      <h2 id={id} className="text-2xl">
        {titulo}
      </h2>
      <table className="w-full text-sm">
        <thead className="sr-only">
          <tr>
            <th scope="col">Item</th>
            <th scope="col">{a.nome}</th>
            <th scope="col">{b.nome}</th>
          </tr>
        </thead>
        <tbody>
          {itens.map((l) => (
            <tr key={l.rotulo} className="border-b border-border">
              <th scope="row" className="py-2 pr-3 text-left font-normal text-muted-foreground">
                {l.rotulo}
              </th>
              <td className="py-2 pr-3 tabular-nums">{l.a}</td>
              <td className="py-2 tabular-nums">{l.b}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function Resultado({ dados }: { dados: ComparacaoLocal }) {
  const { a, b } = dados;
  const rota = dados.casa === "camara" ? "vereador" : "deputado-estadual";
  const nomeCasa = dados.casa === "camara" ? "câmara" : "assembleia";
  const percentual = dados.votacoes_em_comum > 0 ? (100 * dados.iguais) / dados.votacoes_em_comum : 0;
  return (
    <>
      <div className="grid grid-cols-2 gap-4 border-b border-foreground pb-4">
        {[a, b].map((p, i) => (
          <div key={p.id} className="flex flex-col items-center gap-2 text-center">
            <Link href={`/${rota}/${p.id}`} className="flex flex-col items-center gap-2 hover:opacity-80">
              <FotoVereador vereador={p} tamanho={56} />
              <span className="font-semibold leading-tight">{p.nome}</span>
            </Link>
            <span className="text-xs text-muted-foreground">{p.partido}</span>
            <Link href={`/comparar/local?a=${i === 0 ? b.id : a.id}`} className="text-xs underline underline-offset-2">
              Trocar
            </Link>
          </div>
        ))}
      </div>

      <CompartilharWhatsApp
        caminho={`/comparar/local?a=${a.id}&b=${b.id}`}
        texto={`Compare ${a.nome} e ${b.nome}, com dados da própria ${nomeCasa}:`}
      />

      <Tabela titulo="Lado a lado" id="numeros-titulo" a={a} b={b} itens={linhas(a, b)} />
      <p className="-mt-3 text-xs text-muted-foreground">
        Projetos, proposições, presença e votações: ano atual e anterior, como a {nomeCasa} publica.
        Dados pessoais e votos recebidos: declarados ao TSE.
      </p>

      <section aria-labelledby="votos-titulo" className="revelar flex flex-col gap-3">
        <h2 id="votos-titulo" className="text-2xl">
          Votos em comum
        </h2>
        {dados.votacoes_em_comum === 0 ? (
          <p className="text-muted-foreground">
            Não há votação nominal registrada em que os dois tenham votado.
          </p>
        ) : (
          <>
            <div className="figura">
              <p className="text-sm text-muted-foreground">Votaram igual em</p>
              <p className="numero text-3xl">
                {dados.iguais} de {dados.votacoes_em_comum} votações
              </p>
              <p className="text-sm text-muted-foreground tabular-nums">
                {PCT(percentual)} das votações nominais em que os dois registraram voto
              </p>
              <div
                role="meter"
                aria-label="Votações em que votaram igual"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={Math.round(percentual)}
                className="mt-3 h-2 w-full rounded-full bg-muted"
              >
                <div className="h-2 rounded-full bg-chart-1" style={{ width: `${percentual}%` }} />
              </div>
            </div>
            {dados.divergencias.length > 0 && (
              <details className="painel">
                <summary className="cursor-pointer font-medium">Onde votaram diferente (mais recentes)</summary>
                <ul className="mt-3 lista-fios flex flex-col">
                  {dados.divergencias.map((d, i) => (
                    <li key={i} className="flex flex-col gap-1 py-3 text-sm">
                      <span className="text-xs text-muted-foreground">
                        {[d.data && formatarData(d.data), d.resultado].filter(Boolean).join(" · ")}
                      </span>
                      {d.url ? (
                        <a href={d.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                          {d.materia}
                        </a>
                      ) : (
                        <span className="font-medium">{d.materia}</span>
                      )}
                      <dl className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <dt className="text-muted-foreground">{a.nome}</dt>
                          <dd className="font-semibold">{d.voto_a}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">{b.nome}</dt>
                          <dd className="font-semibold">{d.voto_b}</dd>
                        </div>
                      </dl>
                    </li>
                  ))}
                </ul>
              </details>
            )}
          </>
        )}
      </section>

      {dados.proposicoes_por_tipo.length > 0 && (
        <Tabela
          titulo="Proposições por tipo"
          id="tipos-titulo"
          a={a}
          b={b}
          itens={dados.proposicoes_por_tipo.map((t) => ({ rotulo: t.tipo, a: String(t.a), b: String(t.b) }))}
        />
      )}

      <FonteRodape fonte={dados.fonte_nome} url={dados.fonte_url} atualizadoEm={dados.atualizado_em} />
    </>
  );
}
