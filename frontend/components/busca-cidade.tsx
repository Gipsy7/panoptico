"use client";

/**
 * Busca da cidade pelo nome (home): campo com sugestões ao digitar, no padrão combobox da WAI-ARIA
 * (setas escolhem, Enter abre, Esc fecha). Escolher leva a "Quem te representa" da cidade. Sem
 * JavaScript o campo não aparece; o CEP e a lista de estados continuam funcionando.
 */
import { useRouter } from "next/navigation";
import { useEffect, useId, useRef, useState } from "react";

import { type Municipio, buscarMunicipios } from "@/lib/api";

type Estado = { termo: string; lista: Municipio[]; carregando: boolean; erro: boolean };

export function BuscaCidade({ rotulo = "Ou escolha a cidade" }: { rotulo?: string }) {
  const router = useRouter();
  const id = useId();
  const idLista = `${id}-lista`;
  const [texto, setTexto] = useState("");
  const [aberta, setAberta] = useState(false);
  const [ativo, setAtivo] = useState(-1);
  const [res, setRes] = useState<Estado>({ termo: "", lista: [], carregando: false, erro: false });
  const pedido = useRef(0);

  const termo = texto.trim();
  useEffect(() => {
    if (termo.length < 2) return;
    const n = ++pedido.current;
    const t = setTimeout(async () => {
      setRes((r) => ({ ...r, carregando: true }));
      const r = await buscarMunicipios(termo);
      if (n !== pedido.current) return; // já digitou outra coisa
      setRes({ termo, lista: r.ok ? r.dados : [], carregando: false, erro: !r.ok });
      setAtivo(-1);
    }, 200);
    return () => clearTimeout(t);
  }, [termo]);

  const lista = termo.length >= 2 && res.termo === termo ? res.lista : [];
  const mostrar = aberta && termo.length >= 2;

  function escolher(m: Municipio) {
    setAberta(false);
    setTexto(`${m.nome}, ${m.uf}`);
    router.push(`/representantes?municipio=${m.ibge}`);
  }

  function teclar(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" && lista.length) {
      e.preventDefault();
      setAberta(true);
      setAtivo((a) => (a + 1) % lista.length);
    } else if (e.key === "ArrowUp" && lista.length) {
      e.preventDefault();
      setAtivo((a) => (a <= 0 ? lista.length - 1 : a - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      const m = lista[ativo >= 0 ? ativo : 0];
      if (m) escolher(m);
    } else if (e.key === "Escape") {
      setAberta(false);
      setAtivo(-1);
    }
  }

  let aviso = "";
  if (termo.length >= 2 && res.termo === termo && !res.carregando) {
    if (res.erro) aviso = "Não deu para buscar agora. Tente de novo ou use o CEP.";
    else if (!lista.length) aviso = "Nenhuma cidade com esse nome.";
  }

  return (
    <div className="relative flex flex-col gap-1.5 text-left">
      <label htmlFor={id} className="text-sm font-medium text-muted-foreground">
        {rotulo}
      </label>
      <div className="relative">
        <svg aria-hidden viewBox="0 0 24 24" className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth="1.8">
          <circle cx="11" cy="11" r="6.5" />
          <path d="M16 16l4.5 4.5" />
        </svg>
        <input
          id={id}
          type="text"
          role="combobox"
          autoComplete="off"
          spellCheck={false}
          placeholder="Nome da cidade"
          aria-autocomplete="list"
          aria-expanded={mostrar && lista.length > 0}
          aria-controls={idLista}
          aria-activedescendant={ativo >= 0 && lista[ativo] ? `${idLista}-${ativo}` : undefined}
          value={texto}
          onChange={(e) => {
            setTexto(e.target.value);
            setAberta(true);
          }}
          onFocus={() => setAberta(true)}
          onBlur={() => setTimeout(() => setAberta(false), 150)}
          onKeyDown={teclar}
          className="campo h-12 w-full pl-10 text-base"
        />
      </div>
      <div
        id={idLista}
        role="listbox"
        aria-label="Cidades encontradas"
        hidden={!mostrar || lista.length === 0}
        className="absolute inset-x-0 top-full z-20 mt-1 flex flex-col rounded-[var(--raio)] border border-border bg-card shadow-[var(--sombra-menu)]"
      >
        {lista.map((m, i) => (
          // O teclado fica no campo (padrão combobox): setas e Enter escolhem a opção ativa.
          // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/interactive-supports-focus
          <div
            key={m.ibge}
            id={`${idLista}-${i}`}
            role="option"
            aria-selected={i === ativo}
            onMouseDown={(e) => e.preventDefault()}
            onClick={() => escolher(m)}
            className="flex min-h-11 cursor-pointer items-center justify-between gap-3 border-t border-border px-3 first:border-t-0 hover:bg-accent aria-selected:bg-accent"
          >
            <span>{m.nome}</span>
            <span className="text-sm text-muted-foreground">{m.uf}</span>
          </div>
        ))}
      </div>
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:hidden">
        {aviso}
      </p>
    </div>
  );
}
