"use client";

/**
 * Como votou cada parlamentar numa votação: agrupado por partido (na ordem do tamanho da
 * bancada nesta votação) ou por estado (alfabética), com busca por nome, partido ou UF.
 * Sem JavaScript, a lista inteira aparece agrupada por partido.
 */
import Link from "next/link";
import { useDeferredValue, useMemo, useState } from "react";

import { CompartilharWhatsApp } from "@/components/compartilhar";
import { CompartilharCartao } from "@/components/compartilhar-cartao";
import { PlacarPorUf } from "@/components/placar-por-uf";
import { Segmentado } from "@/components/segmentado";
import { PilulasAtivas, SemResultados } from "@/components/ui/campos-filtro";
import { SeletorUf, useUfEscolhida } from "@/components/uf-escolhida";
import type { ParlamentarNaVotacao, PorUf } from "@/lib/api";
import { caminhoCartaoVotacao, fraseCompartilhar, gruposDoEstado, totalDosGrupos } from "@/lib/cartao-votacao";
import { UFS } from "@/lib/ufs";

function chave(texto: string) {
  return texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
}

export function VotacaoParlamentares({
  parlamentares,
  ordemPartidos,
  casa,
  porUf = [],
  ufInicial = null,
  cartao,
}: {
  parlamentares: ParlamentarNaVotacao[];
  ordemPartidos: string[];
  casa: "camara" | "senado";
  /** Placar por estado (Sim, Não, outros), quando a API traz. */
  porUf?: PorUf[];
  /** Estado vindo de `?uf=`; sem ele, vale o que o aparelho lembrou. */
  ufInicial?: string | null;
  /** Dados para o cartão em imagem do estado escolhido; sem eles (votação secreta), sem botão. */
  cartao?: { id: string; proposicao: string | null };
}) {
  const [uf, escolherUf] = useUfEscolhida(ufInicial);
  const [busca, setBusca] = useState("");
  const [agrupar, setAgrupar] = useState<"partido" | "uf">("partido");
  const termo = chave(useDeferredValue(busca).trim());

  const grupos = useMemo(() => {
    const doEstado = uf ? parlamentares.filter((p) => p.uf === uf) : parlamentares;
    const filtrados = termo
      ? doEstado.filter((p) => chave(`${p.nome} ${p.partido} ${p.uf}`).includes(termo))
      : doEstado;
    const mapa = new Map<string, ParlamentarNaVotacao[]>();
    for (const p of filtrados) {
      const g = agrupar === "partido" ? p.partido : p.uf;
      if (!mapa.has(g)) mapa.set(g, []);
      mapa.get(g)!.push(p);
    }
    const ordem =
      agrupar === "partido"
        ? ordemPartidos.filter((g) => mapa.has(g))
        : [...mapa.keys()].sort((a, b) => a.localeCompare(b, "pt-BR"));
    return { total: filtrados.length, lista: ordem.map((g) => ({ nome: g, itens: mapa.get(g)! })) };
  }, [parlamentares, ordemPartidos, termo, agrupar, uf]);

  const quem = casa === "camara" ? "deputado" : "senador";
  const limpar = () => {
    setBusca("");
    escolherUf(null);
  };
  const nomeUf = uf ? (UFS.find((u) => u.sigla === uf)?.nome ?? uf) : null;
  const gruposUf = useMemo(() => (uf ? gruposDoEstado(parlamentares, uf) : null), [parlamentares, uf]);

  return (
    <div className="flex flex-col gap-4">
      <SeletorUf id="uf-votacao" uf={uf} onChange={escolherUf} rotulo="Ver só quem é do meu estado" />
      <PlacarPorUf porUf={porUf} uf={uf} />
      {cartao && uf && gruposUf && totalDosGrupos(gruposUf) > 0 && (
        // `key`: ao trocar de estado, a imagem já buscada deixa de valer.
        <CompartilharCartao
          key={uf}
          caminho={`/votacao/${casa}/${cartao.id}?uf=${uf}#ver-parlamentares`}
          cartao={caminhoCartaoVotacao(casa, cartao.id, uf)}
          nomeArquivo={`${cartao.proposicao ?? "votacao"} ${uf}`}
          rotulo={`Compartilhar como votou ${uf}`}
          texto={fraseCompartilhar(casa, uf, cartao.proposicao, gruposUf)}
        >
          <CompartilharWhatsApp
            caminho={`/votacao/${casa}/${cartao.id}?uf=${uf}#ver-parlamentares`}
            texto={fraseCompartilhar(casa, uf, cartao.proposicao, gruposUf)}
          />
        </CompartilharCartao>
      )}
      <div className="flex flex-col gap-[var(--esp-4)] sm:flex-row sm:items-end">
        <label className="flex min-w-0 flex-1 flex-col gap-[var(--esp-1)] text-sm font-medium">
          Buscar por nome, partido ou estado
          <input
            type="search"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder={`Ex.: nome do ${quem}, PT, SP`}
            enterKeyHint="search"
            className="campo-filtro font-normal"
          />
        </label>
        <fieldset className="flex flex-col gap-[var(--esp-1)] text-sm">
          <legend className="mb-1 font-medium">Agrupar por</legend>
          <Segmentado
            rotulo="Agrupar por"
            opcoes={[
              { valor: "partido", rotulo: "Partido" },
              { valor: "uf", rotulo: "Estado" },
            ]}
            valor={agrupar}
            aoMudar={setAgrupar}
            esticar
          />
        </fieldset>
      </div>
      <PilulasAtivas
        itens={[
          ...(nomeUf ? [{ rotulo: `Estado: ${nomeUf}`, aoRemover: () => escolherUf(null) }] : []),
          ...(termo ? [{ rotulo: `Busca: ${busca.trim()}`, aoRemover: () => setBusca("") }] : []),
        ]}
        aoLimpar={limpar}
      />
      <p className="text-sm font-medium" aria-live="polite">
        {grupos.total.toLocaleString("pt-BR")} {grupos.total === 1 ? "registro" : "registros"}
        {nomeUf && ` de ${nomeUf}`}
        {termo && ` para "${busca.trim()}"`}
      </p>
      {grupos.total === 0 && (
        <SemResultados mensagem={`Nenhum ${quem} encontrado com esses filtros.`} aoLimpar={limpar} />
      )}
      {grupos.lista.map((g) => (
        <section key={g.nome} aria-label={g.nome} className="flex flex-col gap-1">
          <h4 className="text-base font-semibold">
            {g.nome} <span className="font-normal text-muted-foreground">({g.itens.length})</span>
          </h4>
          <ul className="lista-fios">
            {g.itens.map((p) => (
              <li key={p.parlamentar_id} className="flex min-h-11 items-center justify-between gap-3 py-2">
                <span className="flex min-w-0 flex-col">
                  <Link href={`/parlamentar/${p.parlamentar_id}`} className="truncate underline underline-offset-2">
                    {p.nome}
                  </Link>
                  <span className="text-sm text-muted-foreground">
                    {agrupar === "partido" ? p.uf : p.partido}
                  </span>
                </span>
                <span className={`shrink-0 text-right text-sm ${p.efetivo ? "font-semibold" : "text-muted-foreground"}`}>
                  {p.registro}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
