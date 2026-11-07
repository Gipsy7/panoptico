"use client";

/**
 * Selo "Ao vivo" do cabeçalho e a gaveta com o que acontece agora no Plenário da Câmara e do Senado
 * (Frente 4, versão C). O selo só aparece quando a rota /ao-vivo responde com uma sessão em
 * andamento ("Ao vivo") ou com a data da próxima sessão ("Próx. 10/11"); enquanto a resposta não
 * chega, ou se ela falhar, nada aparece e o cabeçalho não muda. A busca roda no navegador, depois da
 * hidratação, e se repete a cada 3 minutos com a aba à vista.
 *
 * A gaveta segue o padrão de components/termo-oficial.tsx: começa fechada, véu, foco preso, fundo
 * inerte, Esc fecha e devolve o foco ao selo. O vídeo não é incorporado: há só o link para o vídeo
 * oficial (TV Câmara, TV Senado).
 */
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { LinkExterno } from "@/components/link-externo";
import { getAoVivo } from "@/lib/api";
import {
  type AoVivo,
  type CasaAoVivo,
  NOME_CASA,
  NOME_PLENARIO,
  conferidoEm,
  diaEHora,
  horaLocal,
  seloDe,
} from "@/lib/ao-vivo";
import { tornarFundoInerte } from "@/lib/fundo-inerte";
import { cn } from "@/lib/utils";

const INTERVALO_MS = 3 * 60 * 1000;

export function AoVivoCabecalho() {
  const [dados, setDados] = useState<AoVivo | null>(null);
  const [aberto, setAberto] = useState(false);
  const botao = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    let ativo = true;
    const buscar = async () => {
      if (document.hidden) return;
      const novos = await getAoVivo();
      if (ativo && novos) setDados(novos);
    };
    void buscar();
    const relogio = setInterval(buscar, INTERVALO_MS);
    const aoVoltar = () => {
      if (!document.hidden) void buscar();
    };
    document.addEventListener("visibilitychange", aoVoltar);
    return () => {
      ativo = false;
      clearInterval(relogio);
      document.removeEventListener("visibilitychange", aoVoltar);
    };
  }, []);

  const selo = seloDe(dados);
  if (!selo || !dados) return null;
  const agora = selo.tipo === "agora";

  return (
    <>
      <button
        ref={botao}
        type="button"
        aria-haspopup="dialog"
        aria-expanded={aberto}
        data-ao-vivo
        onClick={() => setAberto(true)}
        className={cn(
          // Abaixo de 400 px só o ponto (o texto vai para o leitor de tela); o Buscar vira ícone.
          "ml-auto inline-flex min-h-11 w-11 shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-[2px] border px-0 text-[0.8125rem] whitespace-nowrap min-[25rem]:w-auto min-[25rem]:px-2.5 text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze",
          agora ? "border-bronze bg-[var(--realce)] font-semibold" : "border-[var(--borda-controle)] font-medium",
        )}
      >
        <span
          aria-hidden
          className={cn(
            "inline-block size-2.5 shrink-0 rounded-full",
            agora ? "bg-bronze shadow-[0_0_0_3px_var(--realce-forte)]" : "border-2 border-[var(--borda-controle)]",
          )}
        />
        <span aria-hidden className="hidden min-[25rem]:inline">
          {selo.rotulo}
        </span>
        <span className="sr-only">{selo.leitor}. Abre os detalhes</span>
      </button>
      {aberto &&
        createPortal(
          <GavetaPlenario
            dados={dados}
            aoFechar={() => {
              setAberto(false);
              botao.current?.focus();
            }}
          />,
          document.body,
        )}
    </>
  );
}

function GavetaPlenario({ dados, aoFechar }: { dados: AoVivo; aoFechar: () => void }) {
  const idTitulo = useId();
  const caixa = useRef<HTMLDivElement>(null);
  const folha = useRef<HTMLDivElement>(null);
  const desfazerInerte = useRef<(() => void) | null>(null);
  const fecharRef = useRef(aoFechar);
  useEffect(() => {
    fecharRef.current = aoFechar;
  });

  function fechar() {
    // Tira o inert antes de devolver o foco (um botão inerte não recebe foco).
    desfazerInerte.current?.();
    desfazerInerte.current = null;
    fecharRef.current();
  }

  useEffect(() => {
    const anterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    if (caixa.current) desfazerInerte.current = tornarFundoInerte(caixa.current);
    folha.current?.focus();
    const focaveis = () =>
      [...(folha.current?.querySelectorAll<HTMLElement>("a[href], button") ?? [])].filter((e) => e.offsetParent !== null);
    const aoTeclar = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        desfazerInerte.current?.();
        desfazerInerte.current = null;
        fecharRef.current();
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

  const alguemAgora = dados.casas.some((c) => c.situacao === "agora");

  return (
    <div ref={caixa} className="gaveta-termo-caixa">
      <div aria-hidden className="gaveta-termo-veu" onClick={fechar} />
      <div ref={folha} role="dialog" aria-modal="true" aria-labelledby={idTitulo} tabIndex={-1} className="gaveta-termo">
        <button type="button" onClick={fechar} aria-label="Fechar o Plenário agora" className="gaveta-termo-fechar">
          <svg aria-hidden viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </button>
        <p className="pr-12 text-xs font-medium tracking-[0.12em] text-bronze-texto uppercase">
          {alguemAgora ? "Acontecendo agora" : "Plenário"}
        </p>
        <h2 id={idTitulo} className="mt-1 pr-12 text-3xl leading-tight">
          {alguemAgora ? "Sessões no Plenário" : "Sem sessão agora"}
        </h2>
        <div className="mt-[var(--esp-3)] flex flex-col gap-[var(--esp-4)]">
          {dados.casas.map((c) => (
            <BlocoCasa key={c.casa} casa={c} />
          ))}
        </div>
        <p className="mt-[var(--esp-4)] text-sm text-muted-foreground">
          Fonte:{" "}
          <LinkExterno href={dados.fonte_url} className="underline underline-offset-2">
            {dados.fonte_nome}
          </LinkExterno>
          {dados.conferido_em && <> · conferido em {conferidoEm(dados.conferido_em)}</>}
        </p>
        <p className="mt-1 text-sm text-muted-foreground">
          A pauta pode estar alguns minutos atrasada. O Panóptico não guarda nem exibe o vídeo: o link abre o site oficial da
          Casa.
        </p>
      </div>
    </div>
  );
}

function BlocoCasa({ casa }: { casa: CasaAoVivo }) {
  const idTitulo = useId();
  const nome = NOME_CASA[casa.casa];
  return (
    <section aria-labelledby={idTitulo} className="rounded-xl bg-background p-4 ring-1 ring-foreground/10">
      <h3 id={idTitulo} className="text-lg leading-snug font-semibold">
        {nome}
      </h3>
      {casa.situacao === "agora" && <SessaoAgora casa={casa} />}
      {casa.situacao === "proxima" && casa.proxima && (
        <p className="mt-1 text-base">
          Sem sessão agora. Próxima: <span className="font-medium">{diaEHora(casa.proxima.inicio)}</span>
          <span className="block text-sm text-muted-foreground">{casa.proxima.titulo}</span>
        </p>
      )}
      {casa.situacao === "sem" && (
        <p className="mt-1 text-base">
          {casa.indisponivel
            ? "Não foi possível consultar a fonte oficial agora."
            : "Sem sessão agora e nenhuma marcada para os próximos 14 dias."}
        </p>
      )}
    </section>
  );
}

function SessaoAgora({ casa }: { casa: CasaAoVivo }) {
  const idLista = useId();
  return (
    <>
      <p className="mt-1 text-base">
        Sessão no {NOME_PLENARIO[casa.casa]} agora
        {casa.inicio && <>, desde as {horaLocal(casa.inicio)}</>}.
        {casa.titulo && <span className="block text-sm text-muted-foreground">{casa.titulo}</span>}
      </p>
      {casa.itens.length > 0 ? (
        <>
          <p id={idLista} className="mt-[var(--esp-3)] text-sm font-semibold">
            Pauta da sessão
          </p>
          <ol aria-labelledby={idLista} className="mt-1 list-decimal space-y-2 pl-6 text-base marker:text-muted-foreground">
            {casa.itens.map((item, i) => (
              <li key={`${item.rotulo}-${i}`}>
                <span className="font-medium tabular-nums">{item.rotulo}</span>
                {item.descricao && <span className="block text-sm text-muted-foreground">{item.descricao}</span>}
              </li>
            ))}
          </ol>
          {casa.total_itens > casa.itens.length && (
            <p className="mt-1 text-sm text-muted-foreground">
              Mostrando {casa.itens.length} de {casa.total_itens} itens da pauta.
            </p>
          )}
          <p className="mt-1 text-sm text-muted-foreground">
            A fonte não diz qual item está em votação neste minuto: o vídeo mostra.
          </p>
        </>
      ) : (
        <p className="mt-[var(--esp-3)] text-sm text-muted-foreground">A fonte não traz pauta para esta sessão.</p>
      )}
      {casa.url_video && (
        <LinkExterno
          href={casa.url_video}
          className="mt-[var(--esp-3)] flex min-h-12 w-full items-center justify-center gap-2 rounded-[2px] bg-primary px-4 text-center font-semibold text-primary-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-bronze"
        >
          Assistir na {casa.rotulo_video}
        </LinkExterno>
      )}
    </>
  );
}
