"use client";

import Form from "next/form";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { type Municipio, getMunicipios } from "@/lib/api";
import { formatarCep } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

const CAMPO =
  "h-14 rounded-xl border border-input bg-card px-4 text-lg focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none disabled:opacity-60";

type Cidades = { uf: string; estado: "vazio" | "carregando" | "pronto"; lista: Municipio[] };

export function CepForm() {
  const [cep, setCep] = useState("");
  const [semCep, setSemCep] = useState(false);
  const [cidades, setCidades] = useState<Cidades>({ uf: "", estado: "vazio", lista: [] });
  const ufAtual = useRef("");

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
          defaultValue=""
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
        <Button type="submit" className="h-14 rounded-xl text-lg">
          Ver meus representantes
        </Button>
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

  return (
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
        onChange={(e) => setCep(formatarCep(e.target.value))}
        className="h-14 rounded-xl border border-input bg-card px-4 text-center text-2xl tracking-widest placeholder:text-muted-foreground/60 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
      />
      <Button type="submit" className="h-14 rounded-xl text-lg">
        Ver meus representantes
      </Button>
      <button
        type="button"
        onClick={() => setSemCep(true)}
        className="self-center py-2 text-sm text-muted-foreground underline underline-offset-4"
      >
        Não sei meu CEP
      </button>
    </Form>
  );
}
