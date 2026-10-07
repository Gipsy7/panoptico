"use client";

import Form from "next/form";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { formatarCep } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

export function CepForm() {
  const [cep, setCep] = useState("");
  const [semCep, setSemCep] = useState(false);

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
          className="h-14 rounded-xl border border-input bg-card px-4 text-lg focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none"
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
