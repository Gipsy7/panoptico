"use client";

/**
 * "Em poucas palavras": frases antes dos cartões, com a fonte e a data, e o botão que copia
 * o texto para colar no WhatsApp. Se o navegador negar a cópia, o texto aparece selecionável.
 */
import { useRef, useState } from "react";

import { LinhaNovidades } from "@/components/perfil/novidades-perfil";
import { formatarData } from "@/lib/formato";
import { montarTextoCompartilhar } from "@/lib/resumo-frases";
import { SITE_URL_CANONICO } from "@/lib/site";

export function FrasesResumo({
  titulo,
  cabecalho,
  frases,
  fontes,
  atualizadoEm,
}: {
  titulo: string;
  cabecalho: string;
  frases: string[];
  fontes: string[];
  atualizadoEm: string | null;
}) {
  const [aviso, setAviso] = useState("");
  const [textoManual, setTextoManual] = useState<string | null>(null);
  const areaRef = useRef<HTMLTextAreaElement>(null);

  async function copiar() {
    const url = `${SITE_URL_CANONICO}${window.location.pathname}`;
    const texto = montarTextoCompartilhar({
      cabecalho,
      frases,
      fontes,
      atualizadoEm,
      url,
    });
    try {
      await navigator.clipboard.writeText(texto);
      setTextoManual(null);
      setAviso("Texto copiado. Cole na conversa do WhatsApp.");
    } catch {
      setTextoManual(texto);
      setAviso("Não deu para copiar sozinho. O texto está selecionado: copie à mão.");
      requestAnimationFrame(() => areaRef.current?.select());
    }
  }

  return (
    <section aria-labelledby="em-poucas-palavras" className="flex flex-col gap-2">
      <h2 id="em-poucas-palavras" className="text-xl font-semibold">
        {titulo}
      </h2>
      <LinhaNovidades />
      <ul className="flex list-disc flex-col gap-1.5 pl-5">
        {frases.map((f) => (
          <li key={f}>{f}</li>
        ))}
      </ul>
      <p className="text-sm text-muted-foreground">
        Fonte: {fontes.join(", ")}
        {atualizadoEm && <> · atualizado em {formatarData(atualizadoEm)}</>}
      </p>
      <button type="button" onClick={copiar} className="botao-linha self-start">
        Copiar para o WhatsApp
      </button>
      <p role="status" className="text-sm text-muted-foreground">
        {aviso}
      </p>
      {textoManual && (
        <textarea
          ref={areaRef}
          readOnly
          value={textoManual}
          rows={7}
          aria-label="Texto para copiar à mão"
          className="w-full rounded-[var(--radius)] border border-border bg-card p-3 text-sm"
        />
      )}
    </section>
  );
}
