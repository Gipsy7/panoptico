"use client";

/**
 * Campos de filtro que dependem um do outro (precisam de JavaScript; sem ele, viram selects
 * comuns e o servidor descarta combinações inválidas):
 * - ordenação: ao trocar o critério, a ordem passa para a natural dele (nome de A a Z, números
 *   do maior para o menor), como nos atalhos;
 * - estado e cidade: ao trocar o estado, a cidade escolhida sai e a lista de cidades é buscada
 *   de novo; uma busca por texto encurta a lista quando ela é longa.
 */
import { useEffect, useId, useMemo, useState } from "react";

import type { Opcao } from "@/components/ui/campos-filtro";
import { semAcento } from "@/lib/projetos";

const ROTULO = "flex min-w-0 flex-col gap-[var(--esp-1)] text-sm font-medium";
const CAMPO = "campo-filtro font-normal";

export function CamposOrdenacao({
  criterios,
  ordenar,
  ordem,
  textuais,
}: {
  criterios: Opcao[];
  ordenar: string;
  ordem: "asc" | "desc";
  /** Critérios de texto (ordem natural de A a Z); os demais são números (do maior para o menor). */
  textuais: string[];
}) {
  const [criterio, setCriterio] = useState(ordenar);
  const [sentido, setSentido] = useState(ordem);
  const texto = textuais.includes(criterio);
  return (
    <>
      <label className={ROTULO}>
        Ordenar por
        <select
          name="ordenar"
          value={criterio}
          onChange={(e) => {
            setCriterio(e.target.value);
            setSentido(textuais.includes(e.target.value) ? "asc" : "desc");
          }}
          className={CAMPO}
        >
          {criterios.map((c) => (
            <option key={c.valor} value={c.valor}>
              {c.rotulo}
            </option>
          ))}
        </select>
      </label>
      <label className={ROTULO}>
        Ordem
        <select name="ordem" value={sentido} onChange={(e) => setSentido(e.target.value as "asc" | "desc")} className={CAMPO}>
          <option value="asc">{texto ? "De A a Z" : "Do menor para o maior"}</option>
          <option value="desc">{texto ? "De Z a A" : "Do maior para o menor"}</option>
        </select>
      </label>
    </>
  );
}

type Cidade = { ibge: string; nome: string };

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const LIMITE_SEM_BUSCA = 40;

export function CamposUfCidade({
  ufs,
  uf,
  municipio,
  cidades,
}: {
  ufs: Opcao[];
  uf?: string;
  municipio?: string;
  /** Cidades do estado que veio na URL (carregadas no servidor). */
  cidades: Cidade[];
}) {
  const [estado, setEstado] = useState(uf ?? "");
  const [cidade, setCidade] = useState(municipio ?? "");
  const [lista, setLista] = useState<{ uf: string; cidades: Cidade[] | null }>({ uf: uf ?? "", cidades });
  const [procura, setProcura] = useState("");
  const idProcura = useId();

  // Estado novo: busca as cidades dele (a API é pública e fica em cache na CDN).
  useEffect(() => {
    if (!estado || estado === lista.uf) return;
    const controle = new AbortController();
    fetch(`${API}/municipios?uf=${encodeURIComponent(estado)}`, { signal: controle.signal })
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((dados: Cidade[]) => setLista({ uf: estado, cidades: dados }))
      .catch((e) => {
        if (e?.name !== "AbortError") setLista({ uf: estado, cidades: null });
      });
    return () => controle.abort();
  }, [estado, lista.uf]);

  const prontas = estado && lista.uf === estado ? lista.cidades : undefined;
  const visiveis = useMemo(() => {
    if (!prontas) return [];
    const termo = semAcento(procura.trim());
    if (!termo) return prontas;
    return prontas.filter((c) => semAcento(c.nome).includes(termo) || c.ibge === cidade);
  }, [prontas, procura, cidade]);

  return (
    <>
      <label className={ROTULO}>
        Estado
        <select
          name="uf"
          value={estado}
          onChange={(e) => {
            setEstado(e.target.value);
            setCidade("");
            setProcura("");
          }}
          className={CAMPO}
        >
          <option value="">Todos os estados</option>
          {ufs.map((u) => (
            <option key={u.valor} value={u.valor}>
              {u.rotulo}
            </option>
          ))}
        </select>
      </label>

      <div className="flex min-w-0 flex-col gap-[var(--esp-2)]">
        {!estado ? (
          <>
            <span className="text-sm font-medium">Cidade</span>
            <p className="text-sm text-muted-foreground">Escolha um estado para ver as cidades.</p>
          </>
        ) : prontas === undefined ? (
          <>
            <span className="text-sm font-medium">Cidade</span>
            <p className="text-sm text-muted-foreground" aria-live="polite">
              Carregando as cidades…
            </p>
          </>
        ) : prontas === null ? (
          <>
            <span className="text-sm font-medium">Cidade</span>
            <p className="text-sm text-muted-foreground" aria-live="polite">
              Não deu para carregar as cidades. Aplique o estado e escolha a cidade depois.
            </p>
          </>
        ) : (
          <>
            {prontas.length > LIMITE_SEM_BUSCA && (
              <label htmlFor={idProcura} className={ROTULO}>
                Procurar cidade
                <input
                  id={idProcura}
                  type="search"
                  value={procura}
                  onChange={(e) => setProcura(e.target.value)}
                  placeholder="Digite parte do nome"
                  className={CAMPO}
                  // Sem `name`: só encurta a lista abaixo, não vai para a URL.
                />
                {procura.trim() && (
                  <span className="font-normal text-muted-foreground" aria-live="polite">
                    {visiveis.length === 1 ? "1 cidade na lista abaixo" : `${visiveis.length} cidades na lista abaixo`}
                  </span>
                )}
              </label>
            )}
            <label className={ROTULO}>
              Cidade
              <select name="municipio" value={cidade} onChange={(e) => setCidade(e.target.value)} className={CAMPO}>
                <option value="">Todas as cidades</option>
                {visiveis.map((c) => (
                  <option key={c.ibge} value={c.ibge}>
                    {c.nome}
                  </option>
                ))}
              </select>
            </label>
          </>
        )}
      </div>
    </>
  );
}
