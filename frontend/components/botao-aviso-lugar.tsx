"use client";

/**
 * "Receber avisos de Gaspar" (cidade, estado ou Brasil): um toque liga o lugar (todos os assuntos)
 * neste aparelho. Ligada a cidade, sugere também o estado e o Brasil. Afinar por assunto e escolher
 * a frequência ficam em "Meus avisos" (/avisos). Sem chave pública no build, não aparece; a
 * permissão do navegador só é pedida no toque. Sem e-mail nem telefone.
 */
import Link from "next/link";
import { useEffect, useState } from "react";

import { IconeAssunto } from "@/components/icone-assunto";
import { type AlvoAcompanhado, type Suporte, chaveLugar, instrucaoSemSuporte } from "@/lib/avisos";
import { AVISOS_LIGADOS } from "@/lib/avisos-config";
import { ativar, consultarMinhas, inscricaoAtual, lerPermissao, lerSuporte, mudarAlvo } from "@/lib/avisos-navegador";

const NOMES_UF: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AP: "Amapá", AM: "Amazonas", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MT: "Mato Grosso", MS: "Mato Grosso do Sul",
  MG: "Minas Gerais", PA: "Pará", PB: "Paraíba", PR: "Paraná", PE: "Pernambuco", PI: "Piauí",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RS: "Rio Grande do Sul", RO: "Rondônia", RR: "Roraima",
  SC: "Santa Catarina", SP: "São Paulo", SE: "Sergipe", TO: "Tocantins",
};

type Estado = "carregando" | "pronto" | "pedindo" | "ativo" | "negado" | "sem-suporte" | "indisponivel";

function Sino({ cheio = false }: { cheio?: boolean }) {
  return (
    <svg aria-hidden viewBox="0 0 24 24" width="20" height="20" fill={cheio ? "currentColor" : "none"} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
      <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
    </svg>
  );
}

export function BotaoAvisoLugar({ uf, ibge, nome }: { uf: string | null; ibge?: string | null; nome: string }) {
  const chave = chaveLugar(uf, ibge);
  const [estado, setEstado] = useState<Estado>("carregando");
  const [suporte, setSuporte] = useState<Suporte>("suportado");
  const [seguidos, setSeguidos] = useState<Set<string>>(new Set());
  const [mensagem, setMensagem] = useState("");
  const [instrucao, setInstrucao] = useState(false);

  useEffect(() => {
    if (!AVISOS_LIGADOS) return;
    let vivo = true;
    (async () => {
      const s = lerSuporte();
      let lista: AlvoAcompanhado[] = [];
      let indisponivel = false;
      if (s === "suportado" && lerPermissao() === "granted") {
        const sub = await inscricaoAtual();
        if (sub) {
          const r = await consultarMinhas(sub);
          if (r.ok) lista = r.dados.alvos;
          else if (r.status === 503) indisponivel = true;
        }
      }
      if (!vivo) return;
      const lugares = new Set(lista.filter((a) => a.alvo_tipo === "lugar").map((a) => a.alvo_chave));
      setSuporte(s);
      setSeguidos(lugares);
      setEstado(indisponivel ? "indisponivel" : s !== "suportado" ? "sem-suporte" : lugares.has(chave) ? "ativo" : "pronto");
    })();
    return () => {
      vivo = false;
    };
  }, [chave]);

  if (!AVISOS_LIGADOS || estado === "indisponivel") return null;
  if (estado === "carregando") return <div aria-hidden className="min-h-11" />;

  async function seguir(alvo: string, rotulo: string) {
    setMensagem("");
    const jaInscrito = lerPermissao() === "granted" ? await inscricaoAtual() : null;
    const r = jaInscrito ? await mudarAlvo(jaInscrito, "lugar", alvo, "adicionar") : await ativar("lugar", alvo);
    if (r.ok) {
      setSeguidos((s) => new Set(s).add(alvo));
      if (alvo === chave) setEstado("ativo");
      setMensagem(`Avisos de ${rotulo} ligados.`);
      return true;
    }
    if ("motivo" in r && r.motivo === "negado") setEstado("negado");
    else setMensagem(r.mensagem);
    return false;
  }

  async function alternar() {
    if (estado === "ativo") {
      setEstado("pedindo");
      const sub = await inscricaoAtual();
      const r = sub ? await mudarAlvo(sub, "lugar", chave, "remover") : null;
      if (r?.ok) {
        setSeguidos((s) => {
          const n = new Set(s);
          n.delete(chave);
          return n;
        });
        setEstado("pronto");
        setMensagem(`Avisos de ${nome} desligados.`);
      } else {
        setEstado("ativo");
        setMensagem(r ? r.mensagem : "Não foi possível desligar agora. Tente de novo.");
      }
      return;
    }
    setEstado("pedindo");
    if (!(await seguir(chave, nome))) setEstado((e) => (e === "negado" ? e : "pronto"));
  }

  if (estado === "sem-suporte") {
    if (suporte === "sem-suporte") return null;
    return (
      <div className="flex flex-col gap-2">
        <button type="button" onClick={() => setInstrucao((v) => !v)} aria-expanded={instrucao} className="botao-linha self-start">
          <Sino /> Receber avisos de {nome}
        </button>
        {instrucao && suporte !== "suportado" && <p className="max-w-prose text-sm text-muted-foreground">{instrucaoSemSuporte(suporte)}</p>}
      </div>
    );
  }

  const sugestoes = estado === "ativo" && ibge
    ? [
        ...(uf && !seguidos.has(`uf:${uf}`) ? [{ alvo: `uf:${uf}`, rotulo: NOMES_UF[uf] ?? uf }] : []),
        ...(!seguidos.has("br") ? [{ alvo: "br", rotulo: "Brasil" }] : []),
      ]
    : [];

  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={alternar}
          disabled={estado === "pedindo" || estado === "negado"}
          aria-busy={estado === "pedindo"}
          aria-pressed={estado === "ativo"}
          className={`${estado === "ativo" ? "botao-linha !border-2 !border-foreground" : "botao-linha"} !h-auto min-h-11 py-2 disabled:opacity-60`}
        >
          <Sino cheio={estado === "ativo"} />
          {estado === "pedindo" ? "Aguarde…" : estado === "ativo" ? `Recebendo avisos de ${nome}` : `Receber avisos de ${nome}`}
        </button>
        {estado === "ativo" && (
          <Link href="/avisos" className="text-sm underline underline-offset-4">
            Escolher assuntos e frequência
          </Link>
        )}
      </div>
      {sugestoes.length > 0 && (
        <p className="flex flex-wrap items-center gap-1.5 text-sm">
          <span className="text-muted-foreground">Também:</span>
          {sugestoes.map((s) => (
            <button
              key={s.alvo}
              type="button"
              onClick={() => seguir(s.alvo, s.rotulo)}
              className="inline-flex min-h-9 items-center gap-1 rounded-full border border-dashed border-muted-foreground px-3 hover:border-solid hover:border-foreground"
            >
              <IconeAssunto assunto="lugar" className="size-4 text-bronze" />
              {s.rotulo}
            </button>
          ))}
        </p>
      )}
      <p role="status" className={mensagem ? "text-sm font-medium" : "sr-only"}>
        {mensagem}
      </p>
      {estado === "negado" && (
        <p className="max-w-prose text-sm text-muted-foreground">
          O navegador está bloqueando os avisos deste site. Libere as notificações do Panóptico nas configurações do navegador e
          volte a esta página.
        </p>
      )}
      {estado === "pronto" && (
        <p className="max-w-prose text-xs text-muted-foreground">
          Um aviso por dia, só quando houver novidade: obras, emendas pagas, leis, votações e dados novos. Sem e-mail nem
          telefone.
        </p>
      )}
    </div>
  );
}
