import Link from "next/link";

import { FonteRodape } from "@/components/fonte-rodape";
import { LinkExterno } from "@/components/link-externo";
import type { Acao, Mensagem } from "@/lib/argos/tipos";

const BOTAO =
  "min-h-11 max-w-full rounded-[2px] border border-borda-controle px-3 py-2 text-left text-sm break-words hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze-texto disabled:opacity-60";

/** Uma resposta do Argos: texto, linhas de apoio, links, botões de sugestão e a fonte com a data. */
export function ArgosMensagem({
  mensagem,
  aoEscolher,
  aoNavegar,
  ocupado,
}: {
  mensagem: Mensagem;
  aoEscolher: (frase: string, acao?: Acao) => void;
  aoNavegar?: () => void;
  ocupado: boolean;
}) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-base break-words">{mensagem.texto}</p>
      {mensagem.detalhes?.map((d) => (
        <p key={d} className="text-sm break-words text-muted-foreground">
          {d}
        </p>
      ))}
      {mensagem.links.length > 0 && (
        <ul className="flex flex-col">
          {mensagem.links.map((l) => (
            <li key={l.href}>
              {l.href.startsWith("http") ? (
                <LinkExterno href={l.href} className="alvo-link font-medium underline underline-offset-2 hover:text-foreground">
                  {l.rotulo}
                </LinkExterno>
              ) : (
                <Link
                  href={l.href}
                  onClick={aoNavegar}
                  className="alvo-link font-medium underline underline-offset-2 hover:text-foreground"
                >
                  {l.rotulo}
                </Link>
              )}
            </li>
          ))}
        </ul>
      )}
      {mensagem.botoes.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {mensagem.botoes.map((b) => (
            <li key={b.rotulo} className="max-w-full">
              <button type="button" disabled={ocupado} onClick={() => aoEscolher(b.frase, b.acao)} className={BOTAO}>
                {b.rotulo}
              </button>
            </li>
          ))}
        </ul>
      )}
      {mensagem.fonte && (
        <FonteRodape fonte={mensagem.fonte.nome} url={mensagem.fonte.url} atualizadoEm={mensagem.fonte.atualizadoEm} />
      )}
    </div>
  );
}
