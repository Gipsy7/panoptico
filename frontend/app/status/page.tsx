import type { Metadata } from "next";
import { Suspense } from "react";

import { getSaude } from "@/lib/api";

export const metadata: Metadata = { title: "Status" };

export default function StatusPage() {
  return (
    <div className="flex flex-col gap-[var(--esp-2)]">
      <p className="sobretitulo">Sistema</p>
      <h1 className="titulo-pagina">Status</h1>
      <p className="text-muted-foreground">Estado da API e do banco de dados neste momento.</p>
      <Suspense fallback={<p>Verificando…</p>}>
        <Saude />
      </Suspense>
    </div>
  );
}

async function Saude() {
  const resultado = await getSaude();
  if (!resultado.ok) return <p>API indisponível: {resultado.mensagem}</p>;
  return (
    <p>
      API ok · banco {resultado.dados.banco === "ok" ? "ok" : "indisponível"}
    </p>
  );
}
