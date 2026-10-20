"use client";

// Busca de cidade pelo nome. O índice (nome, UF, código) vem das 27 listas de /municipios,
// pedidas só quando a pessoa toca no campo.

import { useId, useMemo, useRef, useState } from "react";

import { type Municipio, getMunicipios } from "@/lib/api";
import { UFS } from "@/lib/ufs";

const semAcento = (s: string) =>
  s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();

let indice: Promise<Municipio[]> | null = null;
function carregarIndice() {
  indice ??= Promise.all(UFS.map((u) => getMunicipios(u.sigla))).then((rs) => {
    const todos = rs.flatMap((r) => (r.ok ? r.dados : []));
    if (todos.length === 0) indice = null; // nada veio: tenta de novo no próximo toque
    return todos;
  });
  return indice;
}

export function BuscaCidade({
  onEscolher,
  classe,
}: {
  onEscolher: (uf: string, ibge: string) => void;
  classe?: string;
}) {
  const id = useId();
  const [texto, setTexto] = useState("");
  const [todos, setTodos] = useState<(Municipio & { chave: string })[]>([]);
  const [aberto, setAberto] = useState(false);
  const pediu = useRef(false);

  function pedir() {
    if (pediu.current) return;
    pediu.current = true;
    carregarIndice().then((l) => {
      if (l.length === 0) pediu.current = false;
      setTodos(l.map((m) => ({ ...m, chave: semAcento(m.nome) })));
    });
  }

  const termo = semAcento(texto.trim());
  const achados = useMemo(() => {
    if (termo.length < 2) return [];
    const comeca = todos.filter((m) => m.chave.startsWith(termo));
    const contem = todos.filter((m) => !m.chave.startsWith(termo) && m.chave.includes(termo));
    return [...comeca, ...contem].slice(0, 8);
  }, [termo, todos]);

  return (
    <div className={`relative ${classe ?? ""}`}>
      <label htmlFor={id} className="sr-only">
        Buscar cidade pelo nome
      </label>
      <input
        id={id}
        type="search"
        value={texto}
        onChange={(e) => {
          setTexto(e.target.value);
          setAberto(true);
        }}
        onFocus={() => {
          pedir();
          setAberto(true);
        }}
        onBlur={() => setTimeout(() => setAberto(false), 150)}
        placeholder="Buscar cidade"
        autoComplete="off"
        className="campo min-h-[38px] w-full text-base"
      />
      {aberto && termo.length >= 2 && (
        <ul
          aria-label="Cidades encontradas"
          className="absolute inset-x-0 top-full z-50 mt-1 max-h-72 overflow-auto border border-border bg-card shadow-[var(--sombra-menu)]"
        >
          {achados.length === 0 && (
            <li className="p-3 text-sm text-muted-foreground">
              {todos.length === 0 ? "Carregando a lista de cidades…" : "Nenhuma cidade com esse nome."}
            </li>
          )}
          {achados.map((m) => (
            <li key={m.ibge}>
              <button
                type="button"
                className="flex min-h-11 w-full items-center justify-between gap-2 px-3 text-left text-sm hover:bg-accent focus-visible:bg-accent focus-visible:outline-none"
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => {
                  setTexto("");
                  setAberto(false);
                  onEscolher(m.uf, m.ibge);
                }}
              >
                <span>{m.nome}</span>
                <span className="text-muted-foreground">{m.uf}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
