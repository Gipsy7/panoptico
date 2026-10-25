"use client";

import Form from "next/form";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { useCidadeAchada } from "@/components/localizacao-home";
import { MaoToque, useMovimentoReduzido } from "@/components/mao-toque";
import { type Municipio, getMunicipios } from "@/lib/api";
import { formatarCep } from "@/lib/formato";
import { type CidadeAchada, acharCidade } from "@/lib/localizacao";
import { carregarDetalhe, carregarMunicipios, carregarUfs } from "@/lib/mapa";
import { UFS } from "@/lib/ufs";

const CAMPO =
  "seletor h-12 w-full text-base disabled:opacity-60";

type Cidades = { uf: string; estado: "vazio" | "carregando" | "pronto"; lista: Municipio[] };

/** `semCepInicial` abre direto na escolha de estado e cidade (usado quando o CEP não existe). */
export function CepForm({ semCepInicial = false }: { semCepInicial?: boolean } = {}) {
  const [cep, setCep] = useState("");
  const [tocouLocalizacao, setTocouLocalizacao] = useState(false);
  const reduzido = useMovimentoReduzido();
  const [semCep, setSemCep] = useState(semCepInicial);
  const [cidades, setCidades] = useState<Cidades>({ uf: "", estado: "vazio", lista: [] });
  const ufAtual = useRef("");
  const router = useRouter();
  // No servidor e na hidratação vale true (renderiza a versão com localização); no aparelho sem
  // geolocalização troca para o CEP logo após hidratar.
  const temGeo = useSyncExternalStore(
    () => () => {},
    () => "geolocation" in navigator,
    () => true,
  );
  const [permNegada, setPermNegada] = useState(false);
  const [focarCep, setFocarCep] = useState(false);
  // CEP como opção principal (escolhido pelo usuário ou depois de recusa/falha da localização).
  const [modoCep, setModoCep] = useState(false);
  const [aviso, setAviso] = useState("");

  // Permissão já negada antes: vai direto ao CEP. Sem a API (Safari antigo), segue normal.
  useEffect(() => {
    let status: PermissionStatus | undefined;
    const atualizar = () => {
      if (status?.state === "denied") setPermNegada(true);
    };
    try {
      navigator.permissions
        ?.query({ name: "geolocation" })
        .then((st) => {
          status = st;
          atualizar();
          st.onchange = atualizar;
        })
        .catch(() => {});
    } catch {
      // sem a API de permissões: nada a fazer
    }
    return () => {
      if (status) status.onchange = null;
    };
  }, []);
  const [ufPre, setUfPre] = useState("");
  const [loc, setLoc] = useState<
    | { estado: "ocioso" }
    | { estado: "procurando" }
    | { estado: "achou"; cidade: CidadeAchada }
  >({ estado: "ocioso" });
  const confirmacao = useRef<HTMLParagraphElement>(null);
  // Compartilha a cidade achada com o exemplo e as curiosidades da home (só em memória).
  const { definirCidade } = useCidadeAchada();
  const cidadeAchada = loc.estado === "achou" ? loc.cidade : null;
  useEffect(() => {
    definirCidade(cidadeAchada);
    return () => definirCidade(null);
  }, [cidadeAchada, definirCidade]);
  const nomeUf = (sigla: string) => UFS.find((u) => u.sigla === sigla)?.nome ?? sigla;

  function irParaCep() {
    setLoc({ estado: "ocioso" });
    setModoCep(true);
    setFocarCep(true);
  }

  function falhar() {
    irParaCep();
    setAviso("Não deu para achar sua cidade. Digite o CEP ou escolha a cidade.");
  }

  // As coordenadas só existem dentro desta função: não vão a servidor, URL nem armazenamento.
  function usarLocalizacao() {
    setLoc({ estado: "procurando" });
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const cidade = await acharCidade(pos.coords.latitude, pos.coords.longitude, {
            ufs: carregarUfs,
            municipios: carregarMunicipios,
            detalhe: carregarDetalhe,
          });
          if (!cidade) {
            falhar();
            return;
          }
          setLoc({ estado: "achou", cidade });
          setTimeout(() => confirmacao.current?.focus(), 0);
        } catch {
          falhar();
        }
      },
      (erro) => {
        if (erro.code === erro.PERMISSION_DENIED) {
          // Já estava no CEP (tocou no link secundário): o navegador não pergunta de novo.
          if (permNegada || modoCep) {
            setAviso("A localização está bloqueada neste navegador. Para usar, libere nas configurações do site.");
          }
          setPermNegada(true);
          irParaCep();
        } else {
          falhar();
        }
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 5 * 60 * 1000 },
    );
  }

  function escolherOutraCidade() {
    const uf = loc.estado === "achou" ? loc.cidade.uf : "";
    setLoc({ estado: "ocioso" });
    setModoCep(true);
    setUfPre(uf);
    setSemCep(true);
    if (uf) carregarCidades(uf);
  }

  async function carregarCidades(uf: string) {
    ufAtual.current = uf;
    setCidades({ uf, estado: "carregando", lista: [] });
    const resultado = await getMunicipios(uf);
    if (ufAtual.current !== uf) return; // o usuário já trocou de estado
    // Sem a lista, a busca segue funcionando pelo estado inteiro.
    setCidades({ uf, estado: "pronto", lista: resultado.ok ? resultado.dados : [] });
  }

  if (semCep) {
    return (
      <Form action="/representantes" className="flex flex-col gap-3">
        <label htmlFor="uf" className="text-base font-medium">
          Escolha seu estado
        </label>
        <select
          id="uf"
          name="uf"
          required
          defaultValue={ufPre}
          onChange={(e) => carregarCidades(e.target.value)}
          className={CAMPO}
        >
          <option value="" disabled>
            Selecione
          </option>
          {UFS.map((uf) => (
            <option key={uf.sigla} value={uf.sigla}>
              {uf.nome}
            </option>
          ))}
        </select>
        {cidades.estado !== "vazio" && (
          <>
            <label htmlFor="municipio" className="text-base font-medium">
              E sua cidade
            </label>
            <select
              id="municipio"
              name="municipio"
              defaultValue=""
              key={cidades.uf}
              disabled={cidades.estado === "carregando"}
              className={CAMPO}
            >
              <option value="">
                {cidades.estado === "carregando" ? "Carregando cidades…" : "Todo o estado"}
              </option>
              {cidades.lista.map((m) => (
                <option key={m.ibge} value={m.ibge}>
                  {m.nome}
                </option>
              ))}
            </select>
          </>
        )}
        <button type="submit" className="botao w-full">
          Ver meus representantes
        </button>
        <button
          type="button"
          onClick={() => setSemCep(false)}
          className="self-center py-2 text-sm text-muted-foreground underline underline-offset-4"
        >
          Voltar para a busca por CEP
        </button>
      </Form>
    );
  }

  const formCep = (
    <Form action="/representantes" className="flex flex-col gap-3">
      <label htmlFor="cep" className="text-base font-medium">
        Digite seu CEP
      </label>
      <input
        id="cep"
        name="cep"
        inputMode="numeric"
        autoComplete="postal-code"
        placeholder="00000-000"
        required
        pattern="\d{5}-?\d{3}"
        title="O CEP tem 8 números, por exemplo 01310-100"
        value={cep}
        autoFocus={focarCep}
        onChange={(e) => setCep(formatarCep(e.target.value))}
        className="campo numero h-16 text-center text-4xl tracking-[0.12em]"
      />
      <button type="submit" className="botao w-full">
        Ver meus representantes
      </button>
    </Form>
  );

  const linkSemCep = (
    <button
      type="button"
      onClick={() => setSemCep(true)}
      className="self-center min-h-11 px-3 text-sm text-muted-foreground underline underline-offset-4"
    >
      Não sei meu CEP
    </button>
  );

  const procurando = loc.estado === "procurando";

  // CEP como principal: sem API de localização, permissão negada, falha ou escolha do usuário.
  // Com a API, a localização fica como opção secundária.
  if (!temGeo || ((permNegada || modoCep) && loc.estado !== "achou")) {
    return (
      <div className="flex flex-col gap-3">
        {aviso && (
          <p role="status" className="text-center text-sm text-muted-foreground">
            {aviso}
          </p>
        )}
        {formCep}
        {linkSemCep}
        {temGeo && (
          <button
            type="button"
            onClick={usarLocalizacao}
            disabled={procurando}
            className="flex min-h-11 items-center justify-center gap-2 self-center px-3 text-sm text-muted-foreground underline underline-offset-4 disabled:opacity-60"
          >
            <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
              <circle cx="12" cy="9.5" r="2.5" />
            </svg>
            {procurando ? "Procurando sua cidade…" : "Usar minha localização"}
          </button>
        )}
      </div>
    );
  }

  const alfinete = (invertido: boolean) => (
    <span
      aria-hidden="true"
      className={`mx-auto flex size-[72px] items-center justify-center rounded-full border ${
        invertido
          ? "border-primary bg-primary text-primary-foreground"
          : "border-border bg-muted text-bronze-texto"
      }`}
    >
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 21s-7-6.2-7-11.5a7 7 0 0 1 14 0C19 14.8 12 21 12 21z" />
        <circle cx="12" cy="9.5" r="2.5" />
      </svg>
    </span>
  );

  // Na confirmação da cidade, "Não, escolher a cidade" já faz o papel de "Não sei meu CEP".
  const preferirCep = (comSemCep: boolean) => (
    <div className="flex flex-col gap-3 border-t border-border pt-3">
      <button
        type="button"
        onClick={irParaCep}
        className="self-center min-h-11 px-3 text-base text-foreground underline underline-offset-4"
      >
        Prefiro digitar o CEP
      </button>
      {comSemCep && linkSemCep}
    </div>
  );

  if (loc.estado === "achou") {
    const c = loc.cidade;
    return (
      <div className="flex flex-col gap-3 text-center">
        {alfinete(true)}
        <div role="status" aria-live="polite" className="flex flex-col gap-1">
          <p ref={confirmacao} tabIndex={-1} className="outline-none">
            <span className="block text-sm text-muted-foreground">Você está em</span>
            <span className="block font-heading text-3xl leading-tight">
              {c.nome}, {nomeUf(c.uf)}?
            </span>
          </p>
        </div>
        <button
          type="button"
          onClick={() => router.push(`/representantes?uf=${c.uf}&municipio=${c.ibge}`)}
          className="botao w-full"
        >
          Sim, é aqui
        </button>
        <button
          type="button"
          onClick={escolherOutraCidade}
          className="min-h-12 w-full rounded-lg border border-border bg-transparent px-4 text-base font-medium"
        >
          Não, escolher a cidade
        </button>
        {preferirCep(false)}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 text-center">
      {alfinete(false)}
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            setTocouLocalizacao(true);
            usarLocalizacao();
          }}
          disabled={procurando}
          className="botao w-full disabled:opacity-60"
        >
          {procurando ? "Procurando sua cidade…" : "Ver quem me representa aqui"}
        </button>
        {/* Mão que convida a tocar no botão; some no primeiro toque. */}
        {/* 1 px, não 0: o navegador não desenha um <svg> de tamanho zero, nem com overflow visível. */}
        <svg aria-hidden="true" className="pointer-events-none absolute top-1/2 right-9 size-px overflow-visible">
          <MaoToque x={0} y={0} oculta={tocouLocalizacao || procurando} reduzido={reduzido} etiquetaEsquerda semEtiqueta />
        </svg>
      </div>
      <p role="status" aria-live="polite" className="text-xs text-muted-foreground">
        Pede a sua localização. Ela fica no seu celular: só usamos para achar a cidade.
      </p>
      {preferirCep(true)}
    </div>
  );
}
