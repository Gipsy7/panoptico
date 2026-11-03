import Link from "next/link";
import { Suspense } from "react";

import { getConfiancaDoPerfil, type TipoDePerfil } from "@/lib/api";
import { formatarData } from "@/lib/formato";

async function Linhas({ tipo, id }: { tipo: TipoDePerfil; id: string }) {
  const r = await getConfiancaDoPerfil(tipo, id);
  if (!r.ok) return null;
  const { conferido_em, fonte, ultimo_registro, parecidos } = r.dados;
  if (!conferido_em && parecidos.length === 0) return null;

  return (
    <div className="flex flex-col gap-1 text-sm text-muted-foreground">
      {conferido_em && (
        <p>
          Nome, partido e cargo conferidos com a fonte oficial ({fonte}) em{" "}
          <span className="tabular-nums">{formatarData(conferido_em)}</span>
          {ultimo_registro && (
            <>
              {" "}
              · último registro oficial: {ultimo_registro.tipo} em{" "}
              <span className="tabular-nums">{formatarData(ultimo_registro.data)}</span>
            </>
          )}
        </p>
      )}
      {parecidos.length > 0 && (
        <p>
          Não confundir com{" "}
          {parecidos.map((o, i) => (
            <span key={o.href}>
              {i > 0 && "; "}
              <Link href={o.href} className="underline underline-offset-2">
                {o.nome}
              </Link>{" "}
              ({o.cargo} em {o.lugar})
            </span>
          ))}
        </p>
      )}
    </div>
  );
}

/** Duas linhas discretas logo abaixo de nome e partido: quando o cadastro foi conferido
 * com a fonte oficial e quem tem nome muito parecido. Some quando não há o que dizer. */
export function CabecalhoConfianca({ tipo, id }: { tipo: TipoDePerfil; id: string }) {
  return (
    <Suspense fallback={null}>
      <Linhas tipo={tipo} id={id} />
    </Suspense>
  );
}
