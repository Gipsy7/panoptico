"use client";

/**
 * Painel privado de acessos (docs/DECISOES.md, 2026-10-31). Só cliente: o servidor nunca renderiza
 * dado daqui. O token (12 h) fica no sessionStorage da aba, não em cookie. Só totais agregados.
 */
import { useCallback, useEffect, useId, useState, useSyncExternalStore } from "react";

import { CHAVE_SEM_CONTAGEM } from "@/lib/metricas";
import { formatarData } from "@/lib/formato";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CHAVE_TOKEN = "panoptico-painel-token";

type Item = { chave: string; total: number };
type Periodo = { rotulo: string; dias: number; visitas: number; paginas_vistas: number };
type Dia = { dia: string; visitas: number; paginas_vistas: number };
type Resumo = {
  hoje: string;
  inicio_da_contagem: string | null;
  periodos: Periodo[];
  por_dia: Dia[];
  dias_do_recorte: number;
  paginas: Item[];
  recursos: Item[];
  origens: Item[];
  dispositivos: Item[];
};

const ORIGENS: Record<string, string> = {
  direto: "Direto (endereço digitado ou sem origem)",
  whatsapp: "WhatsApp",
  google: "Google",
  buscadores: "Outros buscadores",
  redes: "Redes sociais",
  outro_site: "Link de outro site",
};
const DISPOSITIVOS: Record<string, string> = { celular: "Celular ou tablet", computador: "Computador" };
const RECURSOS: Record<string, string> = {
  cep: "Busca por CEP",
  localizacao: "Uso da localização",
  argos: "Abriu o Argos",
  compartilhar: "Compartilhou no WhatsApp",
  pix: "Copiou o Pix",
};

const num = (n: number) => n.toLocaleString("pt-BR");

// O token vive só no sessionStorage da aba; este "store" faz o React reler quando ele muda.
const ouvintes = new Set<() => void>();
function lerToken(): string | null {
  try {
    return sessionStorage.getItem(CHAVE_TOKEN);
  } catch {
    return null;
  }
}
function guardarToken(t: string | null) {
  try {
    if (t) sessionStorage.setItem(CHAVE_TOKEN, t);
    else sessionStorage.removeItem(CHAVE_TOKEN);
  } catch {}
  ouvintes.forEach((f) => f());
}
function assinar(f: () => void) {
  ouvintes.add(f);
  return () => void ouvintes.delete(f);
}

export function PainelAcessos() {
  // undefined = ainda no servidor/hidratando (nada é desenhado).
  const token = useSyncExternalStore(assinar, lerToken, () => undefined);
  const pronto = token !== undefined;

  useEffect(() => {
    try {
      // O aparelho de quem abre o painel deixa de ser contado.
      localStorage.setItem(CHAVE_SEM_CONTAGEM, "1");
    } catch {}
  }, []);

  const sair = useCallback(() => guardarToken(null), []);

  if (!pronto) return null;
  return (
    <div className="pagina-secoes">
      <header className="flex flex-col gap-[var(--esp-2)]">
        <p className="sobretitulo">Área privada</p>
        <h1 className="titulo-pagina">Painel de acessos</h1>
      </header>
      {token ? (
        <Dados token={token} sair={sair} />
      ) : (
        <Entrar
          aoEntrar={guardarToken}
        />
      )}
    </div>
  );
}

function Entrar({ aoEntrar }: { aoEntrar: (token: string) => void }) {
  const id = useId();
  const [usuario, setUsuario] = useState("");
  const [senha, setSenha] = useState("");
  const [erro, setErro] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e: React.FormEvent) {
    e.preventDefault();
    setErro("");
    setEnviando(true);
    try {
      const r = await fetch(`${API}/painel/entrar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, senha }),
      });
      if (r.ok) {
        aoEntrar((await r.json()).token);
        return;
      }
      setSenha("");
      setErro(
        r.status === 429
          ? "Muitas tentativas. Tente de novo em alguns minutos."
          : r.status === 503
            ? "O painel não está configurado neste ambiente."
            : "Usuário ou senha incorretos.",
      );
    } catch {
      setErro("Não deu para falar com o servidor. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  const campo = "w-full rounded-lg border border-border bg-card px-3 py-2 text-base";
  return (
    <form onSubmit={enviar} className="flex max-w-sm flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1">
        <label htmlFor={`${id}-u`} className="text-sm font-medium">
          Usuário
        </label>
        <input
          id={`${id}-u`}
          value={usuario}
          onChange={(e) => setUsuario(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `${id}-e` : undefined}
          className={campo}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label htmlFor={`${id}-s`} className="text-sm font-medium">
          Senha
        </label>
        <input
          id={`${id}-s`}
          type="password"
          value={senha}
          onChange={(e) => setSenha(e.target.value)}
          autoComplete="current-password"
          required
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro ? `${id}-e` : undefined}
          className={campo}
        />
      </div>
      {erro && (
        <p id={`${id}-e`} role="alert" className="text-sm font-medium text-foreground">
          {erro}
        </p>
      )}
      <button type="submit" className="botao" disabled={enviando}>
        {enviando ? "Entrando..." : "Entrar"}
      </button>
    </form>
  );
}

const JANELAS = [7, 30, 90];

function Dados({ token, sair }: { token: string; sair: () => void }) {
  const [dias, setDias] = useState(30);
  const [resumo, setResumo] = useState<Resumo | null>(null);
  const [erro, setErro] = useState("");

  useEffect(() => {
    let vivo = true;
    fetch(`${API}/painel/resumo?dias=${dias}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    })
      .then(async (r) => {
        if (!vivo) return;
        if (r.status === 401) return sair();
        if (!r.ok) return setErro("Não deu para carregar os números agora.");
        setResumo(await r.json());
        setErro("");
      })
      .catch(() => vivo && setErro("Não deu para falar com o servidor."));
    return () => {
      vivo = false;
    };
  }, [dias, token, sair]);

  return (
    <>
      <div className="flex flex-wrap items-center gap-3">
        <div role="group" aria-label="Período do gráfico e das listas" className="flex gap-2">
          {JANELAS.map((j) => (
            <button
              key={j}
              type="button"
              aria-pressed={dias === j}
              onClick={() => setDias(j)}
              className={dias === j ? "botao" : "botao-linha"}
            >
              {j} dias
            </button>
          ))}
        </div>
        <button type="button" onClick={sair} className="botao-linha">
          Sair
        </button>
      </div>
      <p role="status" className="sr-only">
        {resumo ? "Números carregados." : erro || "Carregando."}
      </p>
      {erro && <p className="text-sm font-medium">{erro}</p>}
      {!resumo && !erro && <p className="text-muted-foreground">Carregando...</p>}
      {resumo && <Conteudo r={resumo} />}
    </>
  );
}

function Conteudo({ r }: { r: Resumo }) {
  return (
    <>
      <section aria-labelledby="p-periodos" className="flex flex-col gap-3">
        <h2 id="p-periodos" className="text-lg font-semibold">
          Visitas e páginas vistas
        </h2>
        <div className="grid grid-cols-1 gap-3 min-[420px]:grid-cols-3">
          {r.periodos.map((p) => (
            <div key={p.dias} className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
              <p className="text-sm text-muted-foreground">{p.rotulo}</p>
              <p className="font-serif text-3xl tabular-nums">{num(p.visitas)}</p>
              <p className="text-sm text-muted-foreground">visitas</p>
              <p className="mt-1 text-sm tabular-nums">{num(p.paginas_vistas)} páginas vistas</p>
            </div>
          ))}
        </div>
      </section>

      <GraficoDias dias={r.por_dia} />

      <Ranking
        id="p-paginas"
        titulo="Páginas mais acessadas"
        legenda="Páginas vistas no período"
        itens={r.paginas}
        rotulo={(c) => c}
        mono
      />
      <Ranking
        id="p-recursos"
        titulo="Recursos mais usados"
        legenda="Usos no período"
        itens={r.recursos}
        rotulo={(c) => RECURSOS[c] ?? c}
      />
      <Ranking
        id="p-origem"
        titulo="De onde vieram"
        legenda="Visitas no período, por origem"
        itens={r.origens}
        rotulo={(c) => ORIGENS[c] ?? c}
      />
      <Ranking
        id="p-aparelho"
        titulo="Celular ou computador"
        legenda="Visitas no período, por aparelho"
        itens={r.dispositivos}
        rotulo={(c) => DISPOSITIVOS[c] ?? c}
      />

      <section aria-labelledby="p-limites" className="flex flex-col gap-2 text-sm text-muted-foreground">
        <h2 id="p-limites" className="text-lg font-semibold text-foreground">
          O que estes números são
        </h2>
        <p>
          {r.inicio_da_contagem
            ? `A contagem começou em ${formatarData(r.inicio_da_contagem)}. Nada antes disso foi medido.`
            : "A contagem ainda não registrou nenhum acesso."}{" "}
          Uma visita é uma sequência de páginas numa mesma aba do navegador. Ela não é uma pessoa: quem
          volta amanhã, ou abre numa aba nova, conta de novo.
        </p>
        <p>
          Ficam de fora quem bloqueia scripts ou anúncios, quem pede para não ser rastreado, robôs e
          programas automáticos, e este aparelho. Por isso os números são um piso, não o total real.
        </p>
        <p>
          Nada identifica ninguém: sem IP, sem cookie, sem hora. O CEP digitado nunca é enviado, só o
          fato de a busca ter sido usada. Dia conforme o horário de Brasília.
        </p>
      </section>
    </>
  );
}

function GraficoDias({ dias }: { dias: Dia[] }) {
  const max = Math.max(1, ...dias.map((d) => d.visitas));
  const total = dias.reduce((s, d) => s + d.visitas, 0);
  return (
    <section aria-labelledby="p-dia" className="flex flex-col gap-3">
      <h2 id="p-dia" className="text-lg font-semibold">
        Visitas por dia
      </h2>
      <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <svg
          role="img"
          aria-label={`Barras de visitas por dia, ${dias.length} dias, ${num(total)} visitas no total. A tabela abaixo traz os valores.`}
          viewBox={`0 0 ${dias.length * 10} 100`}
          preserveAspectRatio="none"
          className="h-32 w-full"
        >
          <line x1="0" x2={dias.length * 10} y1="99.5" y2="99.5" stroke="var(--border)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          {dias.map((d, i) => {
            const h = (d.visitas / max) * 96;
            return d.visitas > 0 ? (
              <rect key={d.dia} x={i * 10 + 1} y={99 - h} width="8" height={h} className="fill-chart-1" />
            ) : null;
          })}
        </svg>
        <div className="mt-1 flex justify-between text-xs text-muted-foreground tabular-nums">
          <span>{formatarData(dias[0].dia)}</span>
          <span>maior dia: {num(max)}</span>
          <span>{formatarData(dias[dias.length - 1].dia)}</span>
        </div>
      </div>
      <details className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
        <summary className="cursor-pointer text-sm font-medium">Ver os valores de cada dia</summary>
        <div className="mt-3 max-h-80 overflow-auto">
          <table className="w-full text-sm tabular-nums">
            <caption className="sr-only">Visitas e páginas vistas por dia</caption>
            <thead>
              <tr className="text-left text-muted-foreground">
                <th scope="col" className="py-1 pr-2 font-normal">Dia</th>
                <th scope="col" className="py-1 pr-2 text-right font-normal">Visitas</th>
                <th scope="col" className="py-1 text-right font-normal">Páginas vistas</th>
              </tr>
            </thead>
            <tbody>
              {[...dias].reverse().map((d) => (
                <tr key={d.dia} className="border-t border-border/60">
                  <th scope="row" className="py-1 pr-2 text-left font-normal">{formatarData(d.dia)}</th>
                  <td className="py-1 pr-2 text-right">{num(d.visitas)}</td>
                  <td className="py-1 text-right">{num(d.paginas_vistas)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}

function Ranking({
  id,
  titulo,
  legenda,
  itens,
  rotulo,
  mono = false,
}: {
  id: string;
  titulo: string;
  legenda: string;
  itens: Item[];
  rotulo: (chave: string) => string;
  mono?: boolean;
}) {
  const max = Math.max(1, ...itens.map((i) => i.total));
  return (
    <section aria-labelledby={id} className="flex flex-col gap-3">
      <h2 id={id} className="text-lg font-semibold">
        {titulo}
      </h2>
      {itens.length === 0 ? (
        <p className="text-sm text-muted-foreground">Nada contado neste período.</p>
      ) : (
        <div className="rounded-xl bg-card p-4 ring-1 ring-foreground/10">
          <table className="w-full text-sm">
            <caption className="sr-only">{legenda}</caption>
            <thead className="sr-only">
              <tr>
                <th scope="col">Item</th>
                <th scope="col">Total</th>
              </tr>
            </thead>
            <tbody>
              {itens.map((i) => (
                <tr key={i.chave}>
                  <th scope="row" className="w-full py-1.5 text-left font-normal">
                    <span className={`block ${mono ? "break-all font-mono text-xs" : "break-words"}`}>{rotulo(i.chave)}</span>
                    <span aria-hidden className="mt-1 block h-1.5 rounded-sm bg-muted">
                      <span className="block h-full rounded-sm bg-chart-1" style={{ width: `${(i.total / max) * 100}%` }} />
                    </span>
                  </th>
                  <td className="py-1.5 pl-3 text-right align-top tabular-nums">{num(i.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
