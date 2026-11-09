"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { IconeAssunto } from "@/components/icone-assunto";
import { Segmentado } from "@/components/segmentado";
import {
  ASSUNTOS_AVISO,
  type AlvoAcompanhado,
  type AlvoTipo,
  type AssuntoAviso,
  type Frequencia,
  type MinhasAvisos,
  type Suporte,
  TEXTO_O_QUE_AVISA,
  TEXTO_O_QUE_GUARDA,
  caminhoSeguro,
  instrucaoSemSuporte,
  mensagemDeFalha,
} from "@/lib/avisos";
import { cancelarTodos, consultarMinhas, inscricaoAtual, lerSuporte, mudarAlvo, mudarFrequencia } from "@/lib/avisos-navegador";
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

  async function parar(alvoTipo: AlvoTipo, alvoChave: string, nome: string) {
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

  async function alternarAssunto(a: AlvoAcompanhado, assunto: AssuntoAviso) {
    const atuais = new Set(a.assuntos ?? ASSUNTOS_AVISO.map((x) => x.id));
    if (atuais.has(assunto)) atuais.delete(assunto);
    else atuais.add(assunto);
    if (atuais.size === 0) return setMensagem("Deixe ao menos um assunto, ou pare de avisar sobre o lugar.");
    // Todos marcados = sem filtro (o servidor guarda nulo).
    const lista = atuais.size === ASSUNTOS_AVISO.length ? null : [...atuais];
    setOcupado(true);
    setMensagem("");
    const sub = await inscricaoAtual();
    const r = sub ? await mudarAlvo(sub, "lugar", a.alvo_chave, "adicionar", lista) : null;
    if (r?.ok) {
      await carregar();
      setMensagem(`Assuntos de ${a.nome} atualizados.`);
    } else setMensagem(r ? r.mensagem : mensagemDeFalha(404));
    setOcupado(false);
  }

  async function frequencia(f: Frequencia) {
    setOcupado(true);
    setMensagem("");
    const sub = await inscricaoAtual();
    const r = sub ? await mudarFrequencia(sub, f) : null;
    if (r?.ok) {
      await carregar();
      setMensagem(f === "dia" ? "Avisos uma vez por dia." : "Avisos uma vez por semana, aos domingos.");
    } else setMensagem(r ? r.mensagem : mensagemDeFalha(404));
    setOcupado(false);
  }

  const minhas = tela.tipo === "lista" ? tela.minhas : null;
  const lugares = (minhas?.alvos ?? []).filter((a) => a.alvo_tipo === "lugar");
  const pessoas = (minhas?.alvos ?? []).filter((a) => a.alvo_tipo !== "lugar");
  // Novidades em camadas: um grupo por lugar (na ordem dos lugares) e um para pessoas e projetos.
  const nomeDoLugar = new Map(lugares.map((a) => [a.alvo_chave, a.nome]));
  const grupos: [string, MinhasAvisos["novidades"]][] = [];
  for (const n of minhas?.novidades ?? []) {
    const g = n.alvo_tipo === "lugar" ? (nomeDoLugar.get(n.alvo_chave ?? "") ?? "Lugar") : "Pessoas e projetos";
    const atual = grupos.find(([x]) => x === g);
    if (atual) atual[1].push(n);
    else grupos.push([g, [n]]);
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
          <p>
            Este aparelho não recebe avisos. Para ativar, abra a sua cidade (ou o seu estado) e toque em &ldquo;Receber avisos&rdquo;;
            ou abra o perfil de um deputado, de um senador ou de um projeto de lei federal.
          </p>
          <Link href="/parlamentares" className="alvo-link self-start underline underline-offset-4">
            Ver os parlamentares
          </Link>
        </div>
      )}

      {tela.tipo === "lista" && (
        <>
          <section aria-labelledby="titulo-frequencia" className="flex flex-col gap-2">
            <h2 id="titulo-frequencia" className="text-lg font-semibold">
              Com que frequência
            </h2>
            <Segmentado
              rotulo="Frequência dos avisos"
              opcoes={[
                { valor: "dia", rotulo: "1 por dia" },
                { valor: "semana", rotulo: "1 por semana" },
              ]}
              valor={tela.minhas.frequencia ?? "dia"}
              aoMudar={(f) => void frequencia(f)}
            />
            <p className="text-sm text-muted-foreground">
              {(tela.minhas.frequencia ?? "dia") === "dia"
                ? "Um resumo por dia, só quando houver novidade."
                : "Um resumo aos domingos com tudo da semana."}{" "}
              O envio roda uma vez por dia; não há aviso no instante em que o fato sai.
            </p>
          </section>

          <section aria-labelledby="titulo-lugares" className="flex flex-col gap-2">
            <h2 id="titulo-lugares" className="text-lg font-semibold">
              Lugares
            </h2>
            {lugares.length === 0 ? (
              <p className="text-muted-foreground">
                Nenhum lugar. Abra a sua cidade (ou o seu estado) e toque em &ldquo;Receber avisos&rdquo;.
              </p>
            ) : (
              <ul className="flex flex-col gap-2">
                {lugares.map((a) => {
                  const caminho = caminhoSeguro(a.caminho);
                  const marcados = new Set(a.assuntos ?? ASSUNTOS_AVISO.map((x) => x.id));
                  return (
                    <li key={a.alvo_chave} className="flex flex-col gap-2 border border-l-4 border-border bg-card p-3" style={{ borderLeftColor: "var(--bronze)" }}>
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        {caminho ? (
                          <Link href={caminho} className="font-medium underline underline-offset-4">
                            {a.nome}
                          </Link>
                        ) : (
                          <span className="font-medium">{a.nome}</span>
                        )}
                        <button
                          type="button"
                          disabled={ocupado}
                          onClick={() => parar("lugar", a.alvo_chave, a.nome)}
                          className="botao-linha !h-auto min-h-10 py-1.5 text-sm disabled:opacity-60"
                        >
                          Parar de avisar sobre {a.nome}
                        </button>
                      </div>
                      <fieldset className="flex flex-col gap-1">
                        <legend className="text-xs text-muted-foreground">Assuntos de {a.nome} (toque para ligar ou desligar)</legend>
                        <div className="flex flex-wrap gap-1.5">
                          {ASSUNTOS_AVISO.map((x) => (
                            <button
                              key={x.id}
                              type="button"
                              aria-pressed={marcados.has(x.id)}
                              disabled={ocupado}
                              onClick={() => void alternarAssunto(a, x.id)}
                              className={`inline-flex min-h-9 items-center gap-1.5 rounded-full border px-3 text-sm disabled:opacity-60 ${
                                marcados.has(x.id) ? "border-foreground font-semibold" : "border-border text-muted-foreground"
                              }`}
                            >
                              <span style={{ color: `var(--tema-${x.tema})` }}>
                                <IconeAssunto assunto={x.icone} className="size-4" />
                              </span>
                              {x.nome}
                            </button>
                          ))}
                        </div>
                      </fieldset>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          <section aria-labelledby="titulo-acompanha" className="flex flex-col gap-2">
            <h2 id="titulo-acompanha" className="text-lg font-semibold">
              Pessoas e projetos
            </h2>
            {pessoas.length === 0 ? (
              <p className="text-muted-foreground">Nenhum parlamentar nem projeto no momento.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {pessoas.map((a) => {
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
              <div className="flex flex-col gap-2">
                {grupos.map(([grupo, itens], g) => (
                  <details key={grupo} open={g === 0} className="border border-border bg-card">
                    <summary className="flex min-h-11 cursor-pointer items-center justify-between gap-2 px-3 font-medium">
                      {grupo}
                      <span className="text-sm text-muted-foreground">{itens.length}</span>
                    </summary>
                    <ul className="flex flex-col gap-2 px-3 pb-3">
                      {itens.map((n, i) => {
                        const caminho = caminhoSeguro(n.caminho);
                        const assunto = ASSUNTOS_AVISO.find((x) => x.id === n.categoria);
                        return (
                          <li
                            key={`${n.caminho}-${n.detectado_em}-${i}`}
                            className="flex flex-col gap-1 border-l-4 bg-background p-2.5"
                            style={{ borderLeftColor: assunto ? `var(--tema-${assunto.tema})` : "var(--border)" }}
                          >
                            {assunto && (
                              <span className="text-xs font-semibold tracking-wider uppercase" style={{ color: `var(--tema-${assunto.tema})` }}>
                                {assunto.nome}
                              </span>
                            )}
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
                  </details>
                ))}
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              Só aparecem fatos recentes do que este aparelho acompanha. Cada fato vem da fonte oficial indicada.
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
