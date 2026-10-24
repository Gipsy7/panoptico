import Link from "next/link";

import { Foto } from "@/components/parlamentar-card";
import type { Comparacao, ParlamentarNaLista, ParlamentarResumo } from "@/lib/api";
import { type CasaExemplo, rotuloCasaExemplo } from "@/lib/exemplo";
import { formatarGastos } from "@/lib/formato";
import { doEstado } from "@/lib/ufs";

/** Card do exemplo de comparação da home (dupla sorteada no navegador). */
export function ExemploCard({
  uf,
  casa,
  a,
  b,
  comparacao,
}: {
  uf: string;
  casa: CasaExemplo;
  a: ParlamentarResumo;
  b: ParlamentarResumo;
  comparacao: Comparacao;
}) {
  const { numeros_a: na, numeros_b: nb, convergencia, ano } = comparacao;
  if (!na || !nb) return null;

  const linhas: { rotulo: string; a: string; b: string }[] = [
    { rotulo: `Gastos do gabinete em ${ano}`, a: formatarGastos(na.gastos, true), b: formatarGastos(nb.gastos, true) },
    { rotulo: "Votou nas votações", a: presenca(na), b: presenca(nb) },
    { rotulo: "Projetos como autor", a: String(na.projetos), b: String(nb.projetos) },
  ];

  return (
    <aside aria-labelledby="exemplo-titulo" className="flex flex-col gap-3">
      <p id="exemplo-titulo" className="sobretitulo flex items-center gap-2">
        <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-bronze" />
        Exemplo de comparação: {rotuloCasaExemplo(casa)} {doEstado(uf)}
      </p>
      <div className="flex flex-col rounded-[2px] border border-border bg-card">
        <div className="grid grid-cols-2 gap-3 border-b border-foreground p-4 sm:gap-4 sm:p-5">
          <Pessoa p={a} />
          <Pessoa p={b} />
        </div>
        <dl className="flex flex-col px-4 sm:px-5">
          {linhas.map((l) => (
            <div key={l.rotulo} className="grid grid-cols-2 gap-x-3 gap-y-1 border-b border-border py-3 sm:gap-x-4">
              <dt className="col-span-2 text-sm text-muted-foreground">{l.rotulo}</dt>
              <dd className="numero text-xl">{l.a}</dd>
              <dd className="numero text-xl">{l.b}</dd>
            </div>
          ))}
        </dl>
        {convergencia && convergencia.votacoes_em_comum > 0 && (
          <div className="flex flex-col gap-2 px-4 pt-4 sm:px-5">
            <p className="text-sm">
              Votaram igual em{" "}
              <span className="numero text-lg">
                {convergencia.iguais} de {convergencia.votacoes_em_comum}
              </span>{" "}
              votações em {ano}
            </p>
            <div aria-hidden className="h-1.5 w-full rounded-full bg-muted">
              <div className="h-1.5 rounded-full bg-chart-1" style={{ width: `${convergencia.percentual ?? 0}%` }} />
            </div>
          </div>
        )}
        <div className="flex flex-wrap items-center justify-between gap-3 p-4 sm:p-5">
          <Link href={`/comparar?a=${a.id}&b=${b.id}`} className="botao-linha">
            Ver a comparação completa
          </Link>
          <Link href="/comparar" className="alvo-link text-sm underline underline-offset-4">
            Comparar outros
          </Link>
        </div>
      </div>
    </aside>
  );
}

function presenca(n: ParlamentarNaLista) {
  return n.presenca === null ? "—" : `${n.presenca_votou} de ${n.presenca_total}`;
}

function Pessoa({ p }: { p: ParlamentarResumo }) {
  return (
    <Link href={`/parlamentar/${p.id}`} className="flex min-w-0 items-center gap-3 hover:opacity-80">
      <Foto parlamentar={p} largura={44} />
      <span className="flex min-w-0 flex-col gap-1">
        <span className="line-clamp-2 break-words text-sm font-semibold leading-tight">{p.nome_parlamentar}</span>
        <span className="flex flex-wrap gap-1">
          {p.partido && <span className="pilula">{p.partido}</span>}
          <span className="pilula">{p.uf}</span>
        </span>
      </span>
    </Link>
  );
}
