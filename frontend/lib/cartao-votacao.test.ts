import { describe, expect, it } from "vitest";

import {
  caminhoCartaoVotacao,
  fraseCompartilhar,
  gruposDoEstado,
  nomesCortados,
  placarEmTexto,
  tituloCartao,
  totalDosGrupos,
  ufValida,
} from "./cartao-votacao";

const v = (parlamentar_id: number, nome: string, uf: string, voto: string) => ({ parlamentar_id, nome, uf, voto });

const VOTOS = [
  v(1, "Zé Trovão", "SC", "Sim"),
  v(2, "Ana Paula Lima", "SC", "Sim"),
  v(3, "Pedro Uczai", "SC", "Não"),
  v(4, "Ismael", "SC", "Abstenção"),
  v(5, "Fulano", "SP", "Sim"),
  v(6, "Ávila", "SC", "Artigo 17"),
];

describe("gruposDoEstado", () => {
  it("separa Sim, Não e outro registro, só do estado, em ordem alfabética", () => {
    const g = gruposDoEstado(VOTOS, "SC");
    expect(g.map((x) => x.chave)).toEqual(["sim", "nao", "outros"]);
    expect(g[0].pessoas.map((p) => p.nome)).toEqual(["Ana Paula Lima", "Zé Trovão"]);
    expect(g[1].pessoas.map((p) => p.nome)).toEqual(["Pedro Uczai"]);
    expect(g[2].pessoas.map((p) => p.nome)).toEqual(["Ávila", "Ismael"]);
    expect(totalDosGrupos(g)).toBe(5);
  });

  it("estado sem ninguém na votação devolve os três grupos vazios", () => {
    const g = gruposDoEstado(VOTOS, "RR");
    expect(g).toHaveLength(3);
    expect(totalDosGrupos(g)).toBe(0);
  });
});

describe("nomesCortados", () => {
  it("mostra todos quando cabem", () => {
    expect(nomesCortados(["Ana", "Beto", "Caio"], 40)).toBe("Ana, Beto, Caio");
    expect(nomesCortados([], 40)).toBe("");
  });

  it("corta e diz quantos ficaram de fora, sem passar do limite", () => {
    const nomes = Array.from({ length: 30 }, (_, i) => `Deputado ${i + 1}`);
    const texto = nomesCortados(nomes, 60);
    expect(texto).toMatch(/^Deputado 1, Deputado 2.* e mais \d+$/);
    expect(texto.length).toBeLessThanOrEqual(60 + "e mais 99".length);
    const mostrados = texto.split(" e mais ")[0].split(", ").length;
    expect(mostrados + Number(texto.split(" e mais ")[1])).toBe(30);
  });

  it("sempre mostra pelo menos o primeiro nome", () => {
    expect(nomesCortados(["Um Nome Bem Comprido Mesmo", "Outro"], 5)).toBe("Um Nome Bem Comprido Mesmo e mais 1");
  });
});

describe("textos", () => {
  const g = gruposDoEstado(VOTOS, "SC");

  it("título por Casa", () => {
    expect(tituloCartao("camara", "SC")).toBe("Como votaram os deputados de SC");
    expect(tituloCartao("senado", "SC")).toBe("Como votaram os senadores de SC");
  });

  it("placar literal, com outro registro só quando existe", () => {
    expect(placarEmTexto(g)).toBe("2 Sim, 1 Não, 2 com outro registro");
    expect(placarEmTexto(gruposDoEstado(VOTOS, "SP"))).toBe("1 Sim, 0 Não");
  });

  it("frase para compartilhar", () => {
    expect(fraseCompartilhar("camara", "SP", "PLP 186/2026", gruposDoEstado(VOTOS, "SP"))).toBe(
      "Como votaram os deputados de SP em PLP 186/2026: 1 Sim, 0 Não. Veja o voto de cada um:",
    );
    expect(fraseCompartilhar("senado", "SP", null, gruposDoEstado(VOTOS, "SP"))).toContain("nesta votação");
  });

  it("caminho da imagem e UF", () => {
    expect(caminhoCartaoVotacao("camara", "2635476-36", "SC")).toBe("/votacao/camara/2635476-36/cartao/SC");
    expect(ufValida("sc")).toBe("SC");
    expect(ufValida("S")).toBeNull();
    expect(ufValida("../x")).toBeNull();
    expect(ufValida(null)).toBeNull();
  });
});
