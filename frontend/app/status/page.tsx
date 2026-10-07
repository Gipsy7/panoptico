import type { Metadata } from "next";
import { Suspense } from "react";

import { getSaude } from "@/lib/api";

export const metadata: Metadata = { title: "Status" };

export default function StatusPage() {
  return (
    <div className="flex flex-col gap-2">
      <h1 className="text-2xl font-bold">Status</h1>
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
