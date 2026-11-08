import { EntradaItem } from "@/components/avisar-erro/entradas";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import { FonteRodape } from "@/components/fonte-rodape";
import { PorQueFalta } from "@/components/por-que-falta";
import type { Checklist } from "@/lib/checklist-perfil";

/** Id da seção na aba Ficha; o cartão abre a gaveta `#ver-checklist`. */
export const DESTINO_CHECKLIST = "checklist";

/** Cartão "Este perfil tem N de M dados", logo abaixo dos números principais. */
export function CartaoChecklist({ checklist }: { checklist: Checklist }) {
  if (checklist.total === 0) return null;
  return (
    <div>
    <GradeCartoes rotulo="Dados que este perfil tem">
      <CartaoNumero
        destino={DESTINO_CHECKLIST}
        rotulo="Este perfil tem"
        valor={String(checklist.tem)}
        complemento={`de ${checklist.total} dados`}
        apoio="Ver o que está e o que não está"
        largo
      />
    </GradeCartoes>
    </div>
  );
}

/**
 * "O que está e o que não está neste perfil": cada dado com a fonte (quando há) ou o motivo
 * (quando falta). Falta de dado diz da fonte, não da pessoa.
 */
export function ChecklistPerfil({
  checklist,
  uf,
  casa,
  atualizadoEm,
}: {
  checklist: Checklist;
  uf?: string | null;
  /** Nome da casa como na matriz de cobertura ("Câmara dos Deputados", "ALSC"...). */
  casa?: string;
  atualizadoEm?: string | null;
}) {
  if (checklist.total === 0) return null;
  const faltam = checklist.itens.some((i) => !i.tem);
  return (
    <section aria-labelledby="checklist-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="checklist-titulo" className="text-2xl">
          O que está e o que não está neste perfil
        </h2>
        <p className="text-sm text-muted-foreground">
          Este perfil tem {checklist.tem} de {checklist.total} dados. O que falta não diz nada sobre a pessoa: é dado que a
          fonte oficial não publica ou que ainda não chegou.
        </p>
      </div>
      <ul className="lista-fios flex flex-col">
        {checklist.itens.map((i) => (
          <li key={i.id} className="flex items-start gap-3 py-3">
            <span aria-hidden className="w-5 shrink-0 text-center font-medium">
              {i.tem ? "✓" : "—"}
            </span>
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="font-medium">
                {i.destino && i.tem ? (
                  <a href={`#ver-${i.destino}`} className="alvo-link underline underline-offset-2">
                    {i.rotulo}
                  </a>
                ) : (
                  i.rotulo
                )}
                <span className="sr-only">{i.tem ? ": tem" : ": não tem"}</span>
              </span>
              <span className="text-sm text-muted-foreground">
                {i.tem ? `Fonte: ${i.fonte ?? "órgão oficial"}` : i.motivo}
              </span>
            </span>
            <EntradaItem rotulo={i.rotulo} />
          </li>
        ))}
      </ul>
      {faltam && <PorQueFalta uf={uf} casa={casa} />}
      <FonteRodape fonte="a fonte de cada dado está na lista acima" atualizadoEm={atualizadoEm} semAviso />
    </section>
  );
}
