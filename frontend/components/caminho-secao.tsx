/**
 * "Caminho" do projeto: linha do tempo vertical. Cada passo mostra a etapa em linguagem do dia a
 * dia em destaque, o texto oficial em letra menor, a data e o órgão. Legível em 360 px: o fio
 * fica à esquerda e o texto quebra livremente.
 */
import { FonteRodape } from "@/components/fonte-rodape";
import { LinkExterno } from "@/components/link-externo";
import { TermoOficial } from "@/components/termo-oficial";
import type { FonteBloco, NormaItem, PassoDoCaminho } from "@/lib/api";
import { formatarData } from "@/lib/formato";

const ETAPA_GENERICA = "Outro andamento";
/** Acima disto, os passos mais antigos ficam recolhidos. */
const VISIVEIS = 12;

function Passo({ p }: { p: PassoDoCaminho }) {
  const generica = p.etapa === ETAPA_GENERICA;
  return (
    <li className="relative flex flex-col gap-0.5 pb-5 pl-6 last:pb-0">
      <span aria-hidden className="absolute top-1.5 left-0 size-2.5 -translate-x-1/2 rounded-full border-2 border-bronze bg-background" />
      <p className="text-sm text-muted-foreground tabular-nums">
        {formatarData(p.data)}
        {p.orgao && <> · {p.orgao}</>}
      </p>
      {generica ? (
        <p className="text-sm leading-relaxed">{p.descricao}</p>
      ) : (
        <>
          <p className="font-semibold">{p.etapa}</p>
          <p className="text-sm leading-relaxed text-muted-foreground">Texto oficial: {p.descricao}</p>
        </>
      )}
    </li>
  );
}

function Fio({ passos }: { passos: PassoDoCaminho[] }) {
  return (
    <ol className="relative ml-1 flex flex-col border-l border-border">
      {passos.map((p, i) => (
        <Passo key={`${p.data}-${i}`} p={p} />
      ))}
    </ol>
  );
}

export function CaminhoLinha({ itens }: { itens: PassoDoCaminho[] }) {
  if (itens.length === 0) {
    return <p className="text-muted-foreground">A fonte ainda não traz o andamento deste projeto.</p>;
  }
  if (itens.length <= VISIVEIS) return <Fio passos={itens} />;
  const antigos = itens.slice(0, itens.length - VISIVEIS);
  const recentes = itens.slice(itens.length - VISIVEIS);
  return (
    <div className="flex flex-col gap-3">
      <details>
        <summary className="flex min-h-11 cursor-pointer items-center text-sm font-medium underline underline-offset-4 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze">
          Ver os {antigos.length} passos anteriores
        </summary>
        <Fio passos={antigos} />
      </details>
      <Fio passos={recentes} />
    </div>
  );
}

/**
 * "Resultado" no alto do Caminho (versão B aprovada): a lei que o projeto virou, com a data, a
 * publicação no Diário Oficial (quando a Câmara a registra) e o botão para o texto oficial.
 */
export function ResultadoLei({ norma: n }: { norma: NormaItem & FonteBloco }) {
  const emenda = n.tipo === "EMC";
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-3 border border-bronze bg-[var(--realce)] p-[var(--esp-4)]">
        <p className="sobretitulo">Resultado</p>
        <p className="font-heading text-2xl leading-tight">Virou a {n.nome}</p>
        <p className="text-sm leading-relaxed">{n.ementa}</p>
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <div className="min-w-0">
            <dt className="text-muted-foreground">
              {emenda ? (
                <TermoOficial id="promulgacao">Promulgada</TermoOficial>
              ) : (
                <TermoOficial id="sancao">Data da lei</TermoOficial>
              )}
            </dt>
            <dd className="font-semibold tabular-nums">{formatarData(n.data)}</dd>
          </div>
          {n.data_publicacao && (
            <div className="min-w-0">
              <dt className="text-muted-foreground">Publicada em</dt>
              <dd className="font-semibold tabular-nums">{formatarData(n.data_publicacao)}</dd>
              <dd className="text-sm text-muted-foreground">Diário Oficial da União</dd>
            </div>
          )}
        </dl>
        <p className="text-sm text-muted-foreground">Texto oficial: {n.nome_oficial}</p>
        <LinkExterno href={n.url} className="botao w-full justify-center sm:w-auto sm:self-start">
          Ler o texto oficial da lei
        </LinkExterno>
      </div>
      <FonteRodape fonte={n.fonte_nome} url={n.fonte_url} atualizadoEm={n.atualizado_em} />
    </div>
  );
}
