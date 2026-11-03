import { LinkExterno } from "@/components/link-externo";
import { linhaDeCobranca, type CasaFederal, type Esfera, type TemaCobranca } from "@/lib/como-cobrar";

/**
 * Linha curta no fim da gaveta de uma seção: o canal mais ligado àquele dado.
 * Os atalhos internos (#ver-como-cobrar) abrem a lista completa na aba Ficha.
 *
 * Uso: <CobrarLinha tema="gastos" esfera="federal" casa="camara" />
 */
export function CobrarLinha({
  tema,
  esfera,
  uf,
  casa,
}: {
  tema: TemaCobranca;
  esfera: Esfera;
  uf?: string | null;
  casa?: CasaFederal;
}) {
  const { pergunta, links } = linhaDeCobranca({ tema, esfera, uf, casa });
  return (
    <p className="text-sm text-muted-foreground">
      {pergunta}{" "}
      {links.map((l, i) => (
        <span key={l.rotulo}>
          {i > 0 && " · "}
          {l.externo ? (
            <LinkExterno href={l.href} className="alvo-link text-foreground underline underline-offset-2">
              {l.rotulo}
            </LinkExterno>
          ) : (
            <a href={l.href} className="alvo-link text-foreground underline underline-offset-2">
              {l.rotulo}
            </a>
          )}
        </span>
      ))}
    </p>
  );
}
