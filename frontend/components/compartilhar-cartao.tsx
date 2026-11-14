"use client";

import { useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { SITE_URL } from "@/lib/site";
import {
  decidirModo,
  nomeArquivoCartao,
  textoComLink,
  urlCartao,
  type ModoCompartilhar,
} from "@/lib/compartilhar";

type Estado = "parado" | "preparando" | "pronto" | "erro";

const ARQUIVO_TESTE = () => new File([""], "teste.png", { type: "image/png" });

/** Lê o que o navegador sabe fazer. No servidor (e antes de hidratar) vale só o link do WhatsApp. */
function modoDoNavegador(): ModoCompartilhar {
  const compartilha = typeof navigator.share === "function" && typeof navigator.canShare === "function";
  let compartilhaArquivos = false;
  if (compartilha) {
    try {
      compartilhaArquivos = navigator.canShare({ files: [ARQUIVO_TESTE()] });
    } catch {
      compartilhaArquivos = false;
    }
  }
  return decidirModo({ compartilha, compartilhaArquivos, podeBaixar: typeof URL.createObjectURL === "function" });
}

const semAssinatura = () => () => {};
const modoNoServidor = (): ModoCompartilhar => "whatsapp";

function IconeCompartilhar() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="5" r="3" />
      <circle cx="6" cy="12" r="3" />
      <circle cx="18" cy="19" r="3" />
      <path d="m8.6 13.5 6.8 4M15.4 6.5l-6.8 4" />
    </svg>
  );
}

function IconeBaixar() {
  return (
    <svg aria-hidden viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 4v11m0 0-4-4m4 4 4-4M5 20h14" />
    </svg>
  );
}

/**
 * Compartilhar com o cartão em imagem. Sem JavaScript, ou num navegador que não envia arquivos,
 * o link do WhatsApp (`children`) continua ali. No celular com compartilhamento próprio, um só botão
 * abre a folha do aparelho com a imagem, a frase e o link; no computador, o botão baixa a imagem.
 */
export function CompartilharCartao({
  caminho,
  cartao,
  texto,
  nomeArquivo,
  rotulo = "Compartilhar",
  children,
}: {
  /** Caminho da página que será compartilhada (vira o link no texto). */
  caminho: string;
  /** Caminho base da imagem, sem o formato (ex.: `/parlamentar/12/cartao`). */
  cartao: string;
  texto: string;
  /** Nome da pessoa ou do lugar, usado no nome do arquivo baixado. */
  nomeArquivo: string;
  /** Texto do botão no celular (o padrão é "Compartilhar"). */
  rotulo?: string;
  /** O link do WhatsApp renderizado no servidor. */
  children: ReactNode;
}) {
  const modo = useSyncExternalStore(semAssinatura, modoDoNavegador, modoNoServidor);
  const [estado, setEstado] = useState<Estado>("parado");
  const [aviso, setAviso] = useState("");

  // A imagem começa a ser buscada quando o dedo ou o foco chega ao botão, para o toque responder logo.
  const pedido = useRef<Promise<File> | null>(null);
  function obterArquivo(): Promise<File> {
    if (!pedido.current) {
      pedido.current = buscarArquivo().catch((e) => {
        pedido.current = null;
        throw e;
      });
    }
    return pedido.current;
  }

  async function buscarArquivo(): Promise<File> {
    const resp = await fetch(urlCartao(cartao, "feed"));
    if (!resp.ok) throw new Error(`cartao ${resp.status}`);
    const blob = await resp.blob();
    if (!blob.type.startsWith("image/")) throw new Error("cartao sem imagem");
    return new File([blob], nomeArquivoCartao(nomeArquivo, "feed"), { type: "image/png" });
  }

  function baixar(arquivo: File) {
    const href = URL.createObjectURL(arquivo);
    const a = document.createElement("a");
    a.href = href;
    a.download = arquivo.name;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(href), 1000);
  }

  async function aoClicar() {
    setEstado("preparando");
    setAviso("Preparando a imagem…");
    try {
      const arquivo = await obterArquivo();
      if (modo === "nativo") {
        const url = new URL(caminho, SITE_URL).toString();
        const dados = { files: [arquivo], text: textoComLink(texto, url) };
        if (!navigator.canShare(dados)) throw new Error("sem suporte");
        await navigator.share(dados);
        setEstado("parado");
        setAviso("");
      } else {
        baixar(arquivo);
        setEstado("pronto");
        setAviso(`Imagem baixada (${arquivo.name}). Abra o WhatsApp ou o Instagram e escolha a foto na galeria.`);
      }
    } catch (e) {
      if (e instanceof DOMException && e.name === "AbortError") {
        setEstado("parado");
        setAviso("");
        return;
      }
      setEstado("erro");
      setAviso("Não deu para preparar a imagem agora. Use o link do WhatsApp ou tente de novo em instantes.");
    }
  }

  const ocupado = estado === "preparando";
  const nativo = modo === "nativo";
  // No celular com compartilhamento próprio o botão único substitui o WhatsApp; se der erro, o link volta.
  const mostraWhatsApp = !nativo || estado === "erro";

  return (
    <div className="flex flex-col items-start gap-2">
      {modo !== "whatsapp" && (
        <button
          type="button"
          onClick={aoClicar}
          onPointerEnter={() => void obterArquivo().catch(() => {})}
          onFocus={() => void obterArquivo().catch(() => {})}
          disabled={ocupado}
          aria-busy={ocupado}
          className="botao-linha self-start disabled:opacity-60"
        >
          {nativo ? <IconeCompartilhar /> : <IconeBaixar />}
          {ocupado ? "Preparando…" : nativo ? rotulo : rotulo === "Compartilhar" ? "Baixar imagem" : `${rotulo} (baixar imagem)`}
        </button>
      )}
      {mostraWhatsApp && children}
      <p
        role="status"
        className={aviso ? "max-w-prose text-sm text-muted-foreground" : "sr-only"}
      >
        {aviso}
      </p>
    </div>
  );
}
