"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import {
  type MinhasAvisos,
  type Suporte,
  TEXTO_O_QUE_AVISA,
  TEXTO_O_QUE_GUARDA,
  caminhoSeguro,
  instrucaoSemSuporte,
  mensagemDeFalha,
} from "@/lib/avisos";
import { cancelarTodos, consultarMinhas, inscricaoAtual, lerSuporte, mudarAlvo } from "@/lib/avisos-navegador";
import { formatarData } from "@/lib/formato";

type Tela =
  | { tipo: "carregando" }
  | { tipo: "sem-suporte"; suporte: Exclude<Suporte, "suportado"> }
  | { tipo: "vazio"; aviso?: string }
  | { tipo: "erro"; mensagem: string }
  | { tipo: "lista"; minhas: MinhasAvisos };

/** Página /avisos: o que ESTE aparelho acompanha, as novidades recentes e o cancelamento. */
export function AvisosAparelho() {
  const [tela, setTela] = useState<Tela>({ tipo: "carregando" });
  const [mensagem, setMensagem] = useState("");
  const [ocupado, setOcupado] = useState(false);

  async function carregar() {
    const suporte = lerSuporte();
    if (suporte !== "suportado") return setTela({ tipo: "sem-suporte", suporte });
    const sub = await inscricaoAtual();
    if (!sub) return setTela({ tipo: "vazio" });
    const r = await consultarMinhas(sub);
    if (r.ok) return setTela({ tipo: "lista", minhas: r.dados });
    // 404: o servidor não conhece mais esta inscrição (já cancelada ou apagada).
    if (r.status === 404) return setTela({ tipo: "vazio" });
    setTela({ tipo: "erro", mensagem: r.mensagem });
  }

  useEffect(() => {
    // Só pode ler o navegador depois da hidratação.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void carregar();
  }, []);

  async function parar(alvoTipo: "parlamentar" | "projeto", alvoChave: string, nome: string) {
    setOcupado(true);
    setMensagem("");
    const sub = await inscricaoAtual();
    const r = sub ? await mudarAlvo(sub, alvoTipo, alvoChave, "remover") : null;
    if (r?.ok) {
      await carregar();
      setMensagem(`Avisos desligados para ${nome}.`);
    } else {
      setMensagem(r ? r.mensagem : mensagemDeFalha(404));
    }
    setOcupado(false);
  }

  async function cancelar() {
    setOcupado(true);
    setMensagem("");
    const sub = await inscricaoAtual();
    const r = sub ? await cancelarTodos(sub) : null;
    if (r?.ok) {
      setTela({ tipo: "vazio", aviso: "Avisos cancelados. O endereço técnico deste aparelho foi apagado do servidor." });
    } else {
      setMensagem(r ? r.mensagem : mensagemDeFalha(404));
    }
    setOcupado(false);
  }

  return (
    <div className="flex flex-col gap-[var(--esp-6)]">
      <p role="status" className="text-sm font-medium">
        {mensagem}
      </p>

      {tela.tipo === "carregando" && <p className="text-muted-foreground">Carregando…</p>}

      {tela.tipo === "sem-suporte" && <p className="max-w-prose text-muted-foreground">{instrucaoSemSuporte(tela.suporte)}</p>}

      {tela.tipo === "erro" && <p className="max-w-prose text-muted-foreground">{tela.mensagem}</p>}

      {tela.tipo === "vazio" && (
        <div className="flex max-w-prose flex-col gap-2 text-muted-foreground">
          {tela.aviso && <p className="font-medium text-foreground">{tela.aviso}</p>}
          <p>Este aparelho não acompanha ninguém. Para ativar, abra o perfil de um deputado, de um senador ou de um projeto de lei federal e toque em &ldquo;Avisar sobre novidades&rdquo;.</p>
          <Link href="/parlamentares" className="alvo-link self-start underline underline-offset-4">
            Ver os parlamentares
          </Link>
        </div>
      )}

      {tela.tipo === "lista" && (
        <>
          <section aria-labelledby="titulo-acompanha" className="flex flex-col gap-2">
            <h2 id="titulo-acompanha" className="text-lg font-semibold">
              O que este aparelho acompanha
            </h2>
            {tela.minhas.alvos.length === 0 ? (
              <p className="text-muted-foreground">Nenhum parlamentar nem projeto no momento.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {tela.minhas.alvos.map((a) => {
                  const caminho = caminhoSeguro(a.caminho);
                  return (
                    <li
                      key={`${a.alvo_tipo}:${a.alvo_chave}`}
                      className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-card p-4 ring-1 ring-foreground/10"
                    >
                      {caminho ? (
                        <Link href={caminho} className="alvo-link font-medium underline underline-offset-4">
                          {a.nome}
                        </Link>
                      ) : (
                        <span className="font-medium">{a.nome}</span>
                      )}
                      <button
                        type="button"
                        disabled={ocupado}
                        onClick={() => parar(a.alvo_tipo, a.alvo_chave, a.nome)}
                        className="botao-linha !h-auto min-h-11 py-2 disabled:opacity-60"
                      >
                        Parar de avisar sobre {a.nome}
                      </button>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section aria-labelledby="titulo-novidades" className="flex flex-col gap-2">
            <h2 id="titulo-novidades" className="text-lg font-semibold">
              Novidades recentes
            </h2>
            {tela.minhas.novidades.length === 0 ? (
              <p className="text-muted-foreground">Nenhuma novidade registrada desde que você ativou os avisos.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {tela.minhas.novidades.map((n, i) => {
                  const caminho = caminhoSeguro(n.caminho);
                  return (
                    <li key={`${n.caminho}-${n.detectado_em}-${i}`} className="flex flex-col gap-1 rounded-xl bg-card p-4 ring-1 ring-foreground/10">
                      {caminho ? (
                        <Link href={caminho} className="font-medium underline underline-offset-4">
                          {n.titulo}
                        </Link>
                      ) : (
                        <span className="font-medium">{n.titulo}</span>
                      )}
                      <p className="text-sm text-muted-foreground">
                        Fonte: {n.fonte}. Fato de {formatarData(n.data_fato)}; visto pelo Panóptico em {formatarData(n.detectado_em)}.
                      </p>
                    </li>
                  );
                })}
              </ul>
            )}
            <p className="text-sm text-muted-foreground">
              Só aparecem fatos recentes dos que este aparelho acompanha. Cada fato vem da fonte oficial indicada.
            </p>
          </section>

          <section aria-labelledby="titulo-cancelar" className="flex flex-col gap-2">
            <h2 id="titulo-cancelar" className="text-lg font-semibold">
              Cancelar
            </h2>
            <p className="max-w-prose text-muted-foreground">
              Cancelar apaga agora, do servidor, o endereço técnico deste aparelho e tudo o que ele acompanha.
            </p>
            <button type="button" disabled={ocupado} onClick={cancelar} className="botao-linha self-start disabled:opacity-60">
              Cancelar todos os avisos
            </button>
          </section>
        </>
      )}

      <section aria-labelledby="titulo-como" className="flex max-w-prose flex-col gap-2">
        <h2 id="titulo-como" className="text-lg font-semibold">
          Como funciona
        </h2>
        <p className="text-muted-foreground">{TEXTO_O_QUE_AVISA}</p>
        <p className="text-muted-foreground">{TEXTO_O_QUE_GUARDA}</p>
        <p className="text-muted-foreground">
          Detalhes e prazos na página de{" "}
          <Link href="/privacidade#avisos" className="underline underline-offset-4">
            privacidade
          </Link>
          .
        </p>
      </section>
    </div>
  );
}
