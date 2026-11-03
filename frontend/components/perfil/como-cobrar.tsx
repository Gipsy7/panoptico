import { LinkExterno } from "@/components/link-externo";
import {
  VERIFICADO_EM,
  canaisParaCobrar,
  type CanalCidade,
  type CasaFederal,
  type Esfera,
} from "@/lib/como-cobrar";
import { formatarData } from "@/lib/formato";

/**
 * "Como cobrar": para onde levar uma dúvida, um pedido de informação ou uma queixa sobre quem
 * exerce o mandato, por esfera. Fica na aba Ficha, junto do contato do gabinete. O texto diz o
 * que cada órgão faz; não avalia a pessoa nem promete resultado.
 */
export function ComoCobrar({
  esfera,
  uf,
  casa,
  canaisCidade,
  email,
  telefone,
}: {
  esfera: Esfera;
  uf?: string | null;
  casa?: CasaFederal;
  canaisCidade?: CanalCidade[];
  email?: string | null;
  telefone?: string | null;
}) {
  const canais = canaisParaCobrar({ esfera, uf, casa, canaisCidade });
  return (
    <section aria-labelledby="como-cobrar-titulo" className="flex flex-col gap-3">
      <div>
        <h2 id="como-cobrar-titulo" className="text-2xl">
          Como cobrar
        </h2>
        <p className="text-sm text-muted-foreground">
          Onde tirar uma dúvida, pedir informação ou registrar uma reclamação sobre o mandato e o uso do dinheiro público.
        </p>
      </div>
      <ul className="lista-fios flex flex-col">
        {(email || telefone) && (
          <li className="flex flex-col gap-1 py-3">
            <span className="font-medium">Gabinete do parlamentar</span>
            <span className="text-sm text-muted-foreground">Contato direto, para falar sobre um voto, um projeto ou um gasto.</span>
            <span className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              {email && (
                <a href={`mailto:${email}`} className="alvo-link break-all underline underline-offset-2">
                  {email}
                </a>
              )}
              {telefone && (
                <a href={`tel:${telefone.replace(/\D/g, "")}`} className="alvo-link underline underline-offset-2">
                  {telefone}
                </a>
              )}
            </span>
          </li>
        )}
        {canais.map((c) => (
          <li key={c.id} className="flex flex-col gap-1 py-3">
            <span className="font-medium">
              {c.url ? (
                <LinkExterno href={c.url} className="alvo-link underline underline-offset-2">
                  {c.nome}
                </LinkExterno>
              ) : (
                c.nome
              )}
            </span>
            <span className="text-sm text-muted-foreground">{c.oQueFaz}</span>
            {!c.url && (
              <span className="text-sm text-muted-foreground">Endereço oficial não conferido ainda; procure o site do órgão.</span>
            )}
          </li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        Os links levam ao site de cada órgão, onde fica o formulário ou o telefone.
      </p>
      <p className="text-sm text-muted-foreground">
        Fonte: sites oficiais de cada órgão · endereços conferidos em {formatarData(VERIFICADO_EM)}
      </p>
    </section>
  );
}
