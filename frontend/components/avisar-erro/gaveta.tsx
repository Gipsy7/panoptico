"use client";
/* eslint-disable jsx-a11y/label-has-associated-control -- os campos estão dentro do label e o texto vem de variáveis */

/**
 * Gaveta de baixo "Avisar um erro" / "Sou a pessoa deste perfil" (Frente 7). Mesmo padrão da gaveta
 * do dicionário (components/termo-oficial.tsx): véu, foco preso, fundo inerte, Esc fecha e devolve
 * o foco. O pai a monta ao abrir e a desmonta ao fechar.
 *
 * Erro: três passos (o que parece errado, o texto, contato opcional) e a confirmação com o
 * protocolo. Resposta: um pedido só, com o canal de confirmação da identidade.
 */
import Link from "next/link";
import { type FormEvent, useEffect, useId, useRef, useState } from "react";

import type { PerfilAviso } from "@/components/avisar-erro/contexto";
import { postSugestao } from "@/lib/api";
import {
  CATEGORIAS,
  CONFIRMACOES,
  type CategoriaErro,
  type Confirmacao,
  LIMITES,
  TEXTO_APAGAMENTO,
  TEXTO_REVISAO,
  type TipoAviso,
  limiteTexto,
  montarCorpo,
  validarConfirmacao,
  validarContato,
  validarTexto,
} from "@/lib/avisar-erro";
import { tornarFundoInerte } from "@/lib/fundo-inerte";
import { cn } from "@/lib/utils";

type Passo = 1 | 2 | 3;

/** Títulos das seções da página (h2 de cada `section[aria-labelledby]` do perfil). */
function coletarSecoes(): string[] {
  const nomes: string[] = [];
  document.querySelectorAll("[data-perfil] section[aria-labelledby]:not([data-sem-aviso])").forEach((s) => {
    const id = s.getAttribute("aria-labelledby");
    const t = id ? document.getElementById(id)?.textContent?.trim() : "";
    if (t && !nomes.includes(t)) nomes.push(t);
  });
  return nomes;
}

const OPCAO =
  "flex min-h-11 cursor-pointer items-start gap-3 rounded-md border border-border p-3 has-[:checked]:border-foreground has-[:checked]:bg-accent has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-[var(--bronze)]";
const CAMPO_TEXTO =
  "w-full rounded-[2px] border border-muted-foreground bg-background p-3 text-base text-foreground placeholder:text-muted-foreground focus-visible:border-foreground focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-[var(--bronze)] aria-invalid:border-foreground aria-invalid:border-2";

export function GavetaAvisar({
  modoInicial,
  secaoInicial,
  perfil,
  pagina,
  aoFechar,
}: {
  modoInicial: TipoAviso;
  secaoInicial: string | null;
  perfil: PerfilAviso;
  pagina: string;
  aoFechar: (devolverFoco: boolean) => void;
}) {
  const idTitulo = useId();
  const idErroTexto = useId();
  const idErroContato = useId();
  const idErroConf = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const titulo = useRef<HTMLHeadingElement>(null);
  const campoTexto = useRef<HTMLTextAreaElement>(null);
  const campoContato = useRef<HTMLInputElement>(null);
  const desfazerInerte = useRef<(() => void) | null>(null);
  const fecharRef = useRef(aoFechar);
  useEffect(() => {
    fecharRef.current = aoFechar;
  });

  const [secoes] = useState(coletarSecoes);
  const [modo, setModo] = useState<TipoAviso>(modoInicial);
  const [passo, setPasso] = useState<Passo>(1);
  const [categoria, setCategoria] = useState<CategoriaErro | null>(null);
  const [secao, setSecao] = useState<string>(secaoInicial ?? "");
  const [texto, setTexto] = useState("");
  const [contato, setContato] = useState("");
  const [confirmacao, setConfirmacao] = useState<Confirmacao | null>(null);
  const [erros, setErros] = useState<{ categoria?: string; texto?: string; contato?: string; confirmacao?: string }>({});
  const [enviando, setEnviando] = useState(false);
  const [falha, setFalha] = useState<string | null>(null);
  const [protocolo, setProtocolo] = useState<string | null>(null);
  const feito = protocolo !== null;

  function fechar(devolverFoco: boolean) {
    // Tira o inert antes de devolver o foco (um botão inerte não recebe foco).
    desfazerInerte.current?.();
    desfazerInerte.current = null;
    fecharRef.current(devolverFoco);
  }

  useEffect(() => {
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (caixa.current) desfazerInerte.current = tornarFundoInerte(caixa.current);
    folha.current?.focus();
    const focaveis = () =>
      [...(folha.current?.querySelectorAll<HTMLElement>("a[href], button, input, select, textarea") ?? [])].filter(
        (e) => e.offsetParent !== null && !(e as HTMLInputElement).disabled,
      );
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        desfazerInerte.current?.();
        desfazerInerte.current = null;
        fecharRef.current(true);
      } else if (e.key === "Tab") {
        const lista = focaveis();
        if (!lista.length) return;
        const [primeiro, ultimo] = [lista[0], lista[lista.length - 1]];
        const atual = document.activeElement;
        if (e.shiftKey && (atual === primeiro || atual === folha.current)) {
          e.preventDefault();
          ultimo.focus();
        } else if (!e.shiftKey && atual === ultimo) {
          e.preventDefault();
          primeiro.focus();
        }
      }
    };
    document.addEventListener("keydown", aoTeclar);
    return () => {
      document.body.style.overflow = anterior;
      document.removeEventListener("keydown", aoTeclar);
      desfazerInerte.current?.();
      desfazerInerte.current = null;
    };
  }, []);

  // A cada mudança de passo (ou de modo), o foco vai para o título novo: o leitor de tela o anuncia.
  const primeira = useRef(true);
  useEffect(() => {
    if (primeira.current) {
      primeira.current = false;
      return;
    }
    titulo.current?.focus();
  }, [passo, modo, feito]);

  const rascunho = { tipo: modo, categoria, texto, contato, confirmacao, secao: secao || null };
  const nomeCategoria = CATEGORIAS.find((c) => c.id === categoria)?.rotulo;

  function continuarDoPasso1() {
    if (!categoria) {
      setErros({ categoria: "Escolha o que parece errado." });
      return;
    }
    setErros({});
    setPasso(2);
  }

  function continuarDoPasso2() {
    const e = validarTexto("erro", texto);
    if (e) {
      setErros({ texto: e });
      campoTexto.current?.focus();
      return;
    }
    setErros({});
    setPasso(3);
  }

  async function enviar(ev?: FormEvent) {
    ev?.preventDefault();
    const novos = {
      texto: validarTexto(modo, texto) ?? undefined,
      contato: validarContato(modo, contato) ?? undefined,
      confirmacao: validarConfirmacao(modo, confirmacao) ?? undefined,
    };
    if (novos.texto || novos.contato || novos.confirmacao) {
      setErros(novos);
      if (novos.texto) campoTexto.current?.focus();
      else if (novos.confirmacao) folha.current?.querySelector<HTMLInputElement>('input[name="confirmacao"]')?.focus();
      else campoContato.current?.focus();
      if (modo === "erro" && novos.texto) setPasso(2);
      return;
    }
    setErros({});
    setFalha(null);
    setEnviando(true);
    const r = await postSugestao(montarCorpo(rascunho, { pagina, perfilTipo: perfil.tipo, perfilId: perfil.id }));
    setEnviando(false);
    if (r.ok) setProtocolo(r.protocolo);
    else setFalha(r.mensagem);
  }

  function trocarModo(novo: TipoAviso) {
    setErros({});
    setFalha(null);
    setPasso(1);
    setModo(novo);
  }

  const tituloAtual = feito
    ? modo === "erro"
      ? "Aviso recebido"
      : "Pedido de resposta recebido"
    : modo === "resposta"
      ? "Sou a pessoa deste perfil"
      : passo === 1
        ? "O que parece errado?"
        : passo === 2
          ? "Conte o que você viu"
          : "Quer receber uma resposta?";

  const campoSecao = (
    <div className="flex flex-col gap-1">
      <label htmlFor={`${idTitulo}-secao`} className="text-sm font-medium">
        A que parte do perfil se refere
      </label>
      <select id={`${idTitulo}-secao`} value={secao} onChange={(e) => setSecao(e.target.value)} className="campo-filtro">
        <option value="">O perfil inteiro</option>
        {secaoInicial && !secoes.includes(secaoInicial) && <option value={secaoInicial}>{secaoInicial}</option>}
        {secoes.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
    </div>
  );

  const max = limiteTexto(modo);
  const campoDoTexto = (rotulo: string, ajuda: string) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={`${idTitulo}-texto`} className="text-sm font-medium">
        {rotulo}
      </label>
      <p id={`${idTitulo}-ajuda`} className="text-sm text-muted-foreground">
        {ajuda}
      </p>
      <textarea
        id={`${idTitulo}-texto`}
        ref={campoTexto}
        value={texto}
        onChange={(e) => setTexto(e.target.value)}
        rows={5}
        maxLength={max + 200}
        aria-invalid={erros.texto ? true : undefined}
        aria-describedby={`${idTitulo}-ajuda ${erros.texto ? idErroTexto : ""}`.trim()}
        className={CAMPO_TEXTO}
      />
      <div className="flex items-start justify-between gap-3 text-sm">
        <p id={idErroTexto} className="font-medium">
          {erros.texto}
        </p>
        <p className={cn("shrink-0 tabular-nums text-muted-foreground", texto.trim().length > max && "font-medium text-foreground")}>
          {texto.trim().length}/{max}
        </p>
      </div>
    </div>
  );

  const campoDoContato = (rotulo: string) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={`${idTitulo}-contato`} className="text-sm font-medium">
        {rotulo}
      </label>
      <input
        id={`${idTitulo}-contato`}
        ref={campoContato}
        type="text"
        autoComplete="off"
        value={contato}
        onChange={(e) => setContato(e.target.value)}
        maxLength={LIMITES.contatoMax + 50}
        aria-invalid={erros.contato ? true : undefined}
        aria-describedby={`${idTitulo}-lgpd ${erros.contato ? idErroContato : ""}`.trim()}
        className="campo-filtro"
      />
      <p id={idErroContato} className="text-sm font-medium">
        {erros.contato}
      </p>
      <p id={`${idTitulo}-lgpd`} className="explicacao-termo-exemplo !mt-0 text-sm">
        {TEXTO_APAGAMENTO}
      </p>
    </div>
  );

  const alertaFalha = falha && (
    <p role="alert" className="rounded-md border-2 border-foreground p-3 text-sm">
      {falha}
    </p>
  );

  return (
    <div ref={caixa} className="gaveta-termo-caixa">
      <div aria-hidden className="gaveta-termo-veu" onClick={() => fechar(true)} />
      <div ref={folha} role="dialog" aria-modal="true" aria-labelledby={idTitulo} tabIndex={-1} className="gaveta-termo">
        <button type="button" onClick={() => fechar(true)} aria-label="Fechar" className="gaveta-termo-fechar">
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>

        {!feito && modo === "erro" && (
          <p className="pr-12 text-xs font-medium tracking-[0.12em] text-bronze-texto uppercase">Passo {passo} de 3</p>
        )}
        <h2 id={idTitulo} ref={titulo} tabIndex={-1} className="pr-12 text-2xl leading-tight outline-none">
          {tituloAtual}
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Perfil de {perfil.nome}
          {secao && !feito ? ` · ${secao}` : ""}
        </p>

        {feito ? (
          <div role="status" className="mt-[var(--esp-3)] flex flex-col gap-[var(--esp-3)]">
            {protocolo && (
              <p className="text-base">
                Protocolo: <strong className="tabular-nums">{protocolo}</strong>
              </p>
            )}
            <p className="text-base leading-relaxed">
              {modo === "erro"
                ? "Obrigado. Um humano confere com a fonte oficial. Se o número do site estiver diferente da fonte, corrigimos e a correção aparece em “Sobre as fontes”."
                : "Recebemos o pedido. Vamos confirmar quem está pedindo pelo canal escolhido. Depois da revisão, a resposta é publicada no fim do perfil, como chegou."}
            </p>
            <p className="text-sm text-muted-foreground">{TEXTO_REVISAO}</p>
            <div className="grid grid-cols-1 gap-[var(--esp-2)] min-[22rem]:grid-cols-2">
              <button type="button" onClick={() => fechar(true)} className="botao w-full">
                Fechar
              </button>
              <Link href="/sobre-as-fontes#correcoes" onClick={() => fechar(false)} className="botao-linha w-full">
                Ver as correções feitas
              </Link>
            </div>
          </div>
        ) : modo === "erro" ? (
          <form onSubmit={(e) => (passo === 3 ? enviar(e) : (e.preventDefault(), passo === 1 ? continuarDoPasso1() : continuarDoPasso2()))} noValidate className="mt-[var(--esp-3)] flex flex-col gap-[var(--esp-3)]">
            {passo === 1 && (
              <>
                <fieldset className="flex flex-col gap-2" aria-describedby={erros.categoria ? `${idTitulo}-ecat` : undefined}>
                  <legend className="sr-only">Tipo de erro</legend>
                  {CATEGORIAS.map((c) => (
                    <label key={c.id} className={OPCAO}>
                      <input
                        type="radio"
                        name="categoria"
                        value={c.id}
                        checked={categoria === c.id}
                        onChange={() => setCategoria(c.id)}
                        className="mt-1 size-4 accent-[var(--bronze-texto)]"
                      />
                      <span className="flex flex-col">
                        <span className="font-medium">{c.rotulo}</span>
                        <span className="text-sm text-muted-foreground">{c.apoio}</span>
                      </span>
                    </label>
                  ))}
                </fieldset>
                {erros.categoria && (
                  <p id={`${idTitulo}-ecat`} role="alert" className="text-sm font-medium">
                    {erros.categoria}
                  </p>
                )}
                <button type="button" onClick={() => trocarModo("resposta")} className="alvo-link self-start text-left text-sm underline underline-offset-4">
                  Sou a pessoa deste perfil ou da assessoria
                </button>
                <button type="submit" className="botao w-full">
                  Continuar
                </button>
              </>
            )}
            {passo === 2 && (
              <>
                {campoSecao}
                {campoDoTexto(
                  `${nomeCategoria ?? "O erro"}: o que você viu`,
                  "Diga o que o site mostra e o que a fonte oficial mostra, se souber. Não escreva CPF, endereço nem dados de terceiros.",
                )}
                <div className="grid grid-cols-2 gap-[var(--esp-2)]">
                  <button type="button" onClick={() => setPasso(1)} className="botao-linha w-full">
                    Voltar
                  </button>
                  <button type="submit" className="botao w-full">
                    Continuar
                  </button>
                </div>
              </>
            )}
            {passo === 3 && (
              <>
                <p className="text-base leading-relaxed">
                  Se quiser saber o que foi conferido, deixe um e-mail ou telefone. Pode deixar em branco: o aviso vale do mesmo jeito.
                </p>
                {campoDoContato("E-mail ou telefone (opcional)")}
                <p className="text-sm text-muted-foreground">{TEXTO_REVISAO}</p>
                {alertaFalha}
                <div className="grid grid-cols-2 gap-[var(--esp-2)]">
                  <button type="button" onClick={() => setPasso(2)} className="botao-linha w-full">
                    Voltar
                  </button>
                  <button type="submit" disabled={enviando} className="botao w-full disabled:opacity-60">
                    {enviando ? "Enviando…" : "Enviar aviso"}
                  </button>
                </div>
              </>
            )}
          </form>
        ) : (
          <form onSubmit={enviar} noValidate className="mt-[var(--esp-3)] flex flex-col gap-[var(--esp-3)]">
            <p className="text-base leading-relaxed">
              Aqui a pessoa citada ou a assessoria pode pedir que uma resposta fique no fim do perfil. O Panóptico publica o
              texto como chegou, sem editar (só tiramos dados pessoais), e não concorda nem discorda dele. Os números
              continuam os da fonte oficial.
            </p>
            {campoSecao}
            {campoDoTexto("Sua resposta", "Escreva o que gostaria que aparecesse, de 10 a 3000 letras.")}
            <fieldset className="flex flex-col gap-2" aria-describedby={erros.confirmacao ? idErroConf : undefined}>
              <legend className="text-sm font-medium">Como confirmamos que é você</legend>
              {CONFIRMACOES.map((c) => (
                <label key={c.id} className={OPCAO}>
                  <input
                    type="radio"
                    name="confirmacao"
                    value={c.id}
                    checked={confirmacao === c.id}
                    onChange={() => setConfirmacao(c.id)}
                    className="mt-1 size-4 accent-[var(--bronze-texto)]"
                  />
                  <span className="flex flex-col">
                    <span className="font-medium">{c.rotulo}</span>
                    <span className="text-sm text-muted-foreground">{c.apoio}</span>
                  </span>
                </label>
              ))}
              {erros.confirmacao && (
                <p id={idErroConf} className="text-sm font-medium">
                  {erros.confirmacao}
                </p>
              )}
            </fieldset>
            {campoDoContato("E-mail ou telefone para a confirmação")}
            <p className="text-sm text-muted-foreground">
              Uma pessoa confere a identidade antes de publicar. Se não der para confirmar, a resposta não é publicada.
            </p>
            {alertaFalha}
            <div className="grid grid-cols-2 gap-[var(--esp-2)]">
              <button type="button" onClick={() => trocarModo("erro")} className="botao-linha w-full">
                Voltar
              </button>
              <button type="submit" disabled={enviando} className="botao w-full disabled:opacity-60">
                {enviando ? "Enviando…" : "Pedir resposta"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
