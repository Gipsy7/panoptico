"use client";

// Busca de cidade pelo nome. O índice (nome, UF, código) vem das 27 listas de /municipios,
// pedidas só quando a pessoa toca no campo.

import { type KeyboardEvent, useId, useMemo, useRef, useState } from "react";

import { type Municipio, getMunicipios } from "@/lib/api";
import { moverOpcao, textoResultados } from "@/lib/opcao-ativa";
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
  const [ativo, setAtivo] = useState(-1);
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

  const lista = aberto && termo.length >= 2;
  const ativa = lista && ativo >= 0 && ativo < achados.length ? ativo : -1;
  const idLista = `${id}-lista`;
  const idOpcao = (i: number) => `${id}-op-${i}`;

  function escolher(m: Municipio) {
    setTexto("");
    setAberto(false);
    setAtivo(-1);
    onEscolher(m.uf, m.ibge);
  }

  function aoTeclar(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      if (achados.length === 0) return;
      e.preventDefault();
      setAberto(true);
      setAtivo(moverOpcao(ativa, achados.length, e.key));
    } else if ((e.key === "Home" || e.key === "End") && lista && achados.length > 0) {
      e.preventDefault();
      setAtivo(moverOpcao(ativa, achados.length, e.key));
    } else if (e.key === "Enter") {
      if (ativa >= 0) {
        e.preventDefault();
        escolher(achados[ativa]);
      }
    } else if (e.key === "Escape") {
      if (lista) {
        e.preventDefault();
        setAberto(false);
        setAtivo(-1);
      } else if (texto) {
        e.preventDefault();
        setTexto("");
      }
    }
  }

  const aviso = !lista
    ? ""
    : achados.length > 0
      ? textoResultados(achados.length, "")
      : todos.length === 0
        ? "Carregando a lista de cidades"
        : "Nenhuma cidade encontrada";

  return (
    <div className={`relative ${classe ?? ""}`}>
      <label htmlFor={id} className="sr-only">
        Buscar cidade pelo nome
      </label>
      <input
        id={id}
        type="search"
        role="combobox"
        aria-expanded={lista && achados.length > 0}
        aria-controls={idLista}
        aria-autocomplete="list"
        aria-activedescendant={ativa >= 0 ? idOpcao(ativa) : undefined}
        value={texto}
        onChange={(e) => {
          setTexto(e.target.value);
          setAberto(true);
          setAtivo(-1);
        }}
        onFocus={() => {
          pedir();
          setAberto(true);
        }}
        onKeyDown={aoTeclar}
        onBlur={() => {
          // As opções não recebem foco (mousedown é barrado): sair do campo é sair do componente.
          setAberto(false);
          setAtivo(-1);
        }}
        placeholder="Buscar cidade"
        autoComplete="off"
        className="campo min-h-[38px] w-full text-base"
      />
      <p role="status" className="sr-only">
        {aviso}
      </p>
      {lista && (
        <div className="absolute inset-x-0 top-full z-50 mt-1 max-h-72 overflow-auto border border-border bg-card shadow-[var(--sombra-menu)]">
          {/* Padrão combobox do APG: o foco fica no campo; o teclado é tratado nele (aoTeclar). */}
          {/* eslint-disable jsx-a11y/no-noninteractive-element-to-interactive-role, jsx-a11y/click-events-have-key-events */}
          <ul id={idLista} role="listbox" aria-label="Cidades encontradas" className={achados.length ? "" : "hidden"}>
            {achados.map((m, i) => (
              <li
                key={m.ibge}
                id={idOpcao(i)}
                role="option"
                aria-selected={i === ativa}
                ref={(el) => {
                  if (el && i === ativa) el.scrollIntoView({ block: "nearest" });
                }}
                className={`flex min-h-11 cursor-pointer items-center justify-between gap-2 px-3 text-sm hover:bg-accent ${
                  i === ativa ? "bg-accent outline outline-2 -outline-offset-2 outline-bronze-texto" : ""
                }`}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => escolher(m)}
              >
                <span>{m.nome}</span>
                <span className="text-muted-foreground">{m.uf}</span>
              </li>
            ))}
          </ul>
          {/* eslint-enable jsx-a11y/no-noninteractive-element-to-interactive-role, jsx-a11y/click-events-have-key-events */}
          {achados.length === 0 && (
            <p className="p-3 text-sm text-muted-foreground">
              {todos.length === 0 ? "Carregando a lista de cidades…" : "Nenhuma cidade com esse nome."}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
