import { describe, expect, it } from "vitest";

import type { GrupoQuemVotou } from "@/lib/api";
import {
  agruparVotosLocais,
  anosParaFiltro,
  caminhoInterno,
  enderecoProjetos,
  idDaProposicao,
  filtrarGruposPorUf,
  lerFiltrosProjetos,
  lerUf,
  placarDaVotacao,
  ordenarGruposDiscurso,
  ordenarGruposVoto,
  situacaoSimples,
  textoCompartilharProjeto,
} from "@/lib/projetos";

describe("lerUf", () => {
  it("aceita sigla em qualquer caixa e rejeita o resto", () => {
    expect(lerUf("sp")).toBe("SP");
    expect(lerUf(["mg", "rj"])).toBe("MG");
    expect(lerUf("XX")).toBeNull();
    expect(lerUf("")).toBeNull();
    expect(lerUf(undefined)).toBeNull();
  });
});

describe("lerFiltrosProjetos", () => {
  it("descarta valores inválidos e mantém os válidos", () => {
    const f = lerFiltrosProjetos({ q: " saude ", esfera: "mundial", uf: "sc", ano: "20x", pagina: "3", votacao: "com" });
    expect(f).toEqual({ q: "saude", uf: "SC", pagina: "3", votacao: "com" });
  });
});

describe("enderecoProjetos", () => {
  it("volta à página 1 ao mudar um filtro e tira o que está vazio", () => {
    expect(enderecoProjetos({ q: "dengue", pagina: "4" }, { uf: "PR" })).toBe("/projetos?q=dengue&uf=PR");
    expect(enderecoProjetos({ q: "dengue" }, { q: "" })).toBe("/projetos");
    expect(enderecoProjetos({ q: "dengue" }, { pagina: "2" })).toBe("/projetos?q=dengue&pagina=2");
  });
});

describe("caminhoInterno", () => {
  it("leva votação local para a rota /votacao/local", () => {
    expect(caminhoInterno("/votacoes/local/12")).toBe("/votacao/local/12");
    expect(caminhoInterno("/projeto/camara/99")).toBe("/projeto/camara/99");
  });
});

const grupos: GrupoQuemVotou[] = [
  {
    chave: "outros",
    rotulo: "Outros",
    quantidade: 1,
    partidos: [],
    pessoas: [{ parlamentar_id: 3, nome: "C", partido: "X", uf: "SP", registro: "Abstenção" }],
  },
  {
    chave: "nao",
    rotulo: "Não",
    quantidade: 1,
    partidos: [],
    pessoas: [{ parlamentar_id: 2, nome: "B", partido: "Y", uf: "RJ", registro: "Não" }],
  },
  {
    chave: "sim",
    rotulo: "Sim",
    quantidade: 3,
    partidos: [],
    pessoas: [
      { parlamentar_id: 1, nome: "A", partido: "X", uf: "SP", registro: "Sim" },
      { parlamentar_id: 4, nome: "D", partido: "Z", uf: "SP", registro: "Sim" },
      { parlamentar_id: 5, nome: "E", partido: "Z", uf: "SP", registro: "Sim" },
    ],
  },
];

describe("grupos de voto", () => {
  it("ficam sempre em Sim, Não, outros", () => {
    expect(ordenarGruposVoto(grupos).map((g) => g.chave)).toEqual(["sim", "nao", "outros"]);
  });
  it("discursos: Sim, Não, outro registro, sem voto", () => {
    const g = [{ chave: "sem_voto" }, { chave: "outro" }, { chave: "nao" }, { chave: "sim" }];
    expect(ordenarGruposDiscurso(g).map((x) => x.chave)).toEqual(["sim", "nao", "outro", "sem_voto"]);
  });
  it("filtrar por estado recalcula quantidades e partidos", () => {
    const r = filtrarGruposPorUf(grupos, "SP");
    expect(r.map((g) => g.quantidade)).toEqual([3, 0, 1]);
    expect(r[0].partidos).toEqual([
      { partido: "Z", quantidade: 2 },
      { partido: "X", quantidade: 1 },
    ]);
  });
  it("sem estado, devolve tudo", () => {
    expect(filtrarGruposPorUf(grupos, null).map((g) => g.quantidade)).toEqual([3, 1, 1]);
  });
});

describe("situacaoSimples", () => {
  it("traduz o que reconhece e guarda o texto oficial", () => {
    expect(situacaoSimples("Aguardando Designação de Relator", false)).toEqual({
      rotulo: "Esperando um relator ser escolhido",
      oficial: "Aguardando Designação de Relator",
    });
    expect(situacaoSimples("Arquivada", false).rotulo).toBe("Arquivado");
    expect(situacaoSimples("Transformado em Norma Jurídica", true).rotulo).toBe("Virou lei");
  });
  it("não inventa tradução", () => {
    expect(situacaoSimples("Situação nunca vista", null)).toEqual({ rotulo: null, oficial: "Situação nunca vista" });
    expect(situacaoSimples(null, null)).toEqual({ rotulo: null, oficial: null });
  });
});

describe("textoCompartilharProjeto", () => {
  it("é factual, com o placar quando existe", () => {
    const t = textoCompartilharProjeto({
      rotulo: "PL 1/2025",
      ementa: "Dispõe sobre algo.",
      casaCurta: "Câmara",
      placar: { sim: 300, nao: 100, data: "01/02/2025" },
    });
    expect(t).toContain("Sim 300 x Não 100");
    expect(t).not.toMatch(/aprovad|rejeitad/i);
  });
  it("diz quando não houve votação nominal", () => {
    expect(textoCompartilharProjeto({ rotulo: "PL 1/2025", casaCurta: "Senado" })).toContain("Ainda sem votação nominal");
  });
});

describe("anosParaFiltro", () => {
  it("lista do ano atual para trás", () => {
    expect(anosParaFiltro(2026, 3)).toEqual([2026, 2025, 2024]);
  });
});

describe("idDaProposicao", () => {
  it("lê o id nas duas Casas", () => {
    expect(idDaProposicao("https://www.camara.leg.br/proposicoesWeb/fichadetramitacao?idProposicao=2345")).toBe("2345");
    expect(idDaProposicao("https://www25.senado.leg.br/web/atividade/materias/-/materia/160001")).toBe("160001");
    expect(idDaProposicao(null)).toBeNull();
    expect(idDaProposicao("https://exemplo.gov.br/x")).toBeNull();
  });
});

describe("placarDaVotacao", () => {
  const base = {
    id_externo: "1",
    data: "2025-01-01",
    descricao: "",
    resultado: null,
    secreta: false,
    link: "/votacao/camara/1",
    placar_contado: { sim: 10, nao: 5, abstencao: 0, obstrucao: 0, outros: 0 },
  };
  it("prefere o placar publicado pela Casa", () => {
    expect(placarDaVotacao({ ...base, placar_publicado: { sim: 12, nao: 6, abstencao: 0 } })).toEqual({ sim: 12, nao: 6, daFonte: true });
    expect(placarDaVotacao({ ...base, placar_publicado: null })).toEqual({ sim: 10, nao: 5, daFonte: false });
  });
});

describe("agruparVotosLocais", () => {
  it("separa Sim, Não e outros, nessa ordem, e ordena por nome", () => {
    const g = agruparVotosLocais([
      { mandato_id: 1, nome: "Zé", partido: null, voto: "Sim" },
      { mandato_id: 2, nome: "Ana", partido: null, voto: "SIM" },
      { mandato_id: 3, nome: "Bia", partido: null, voto: "Não" },
      { mandato_id: 4, nome: "Cris", partido: null, voto: "Abstenção" },
    ]);
    expect(g.map((x) => x.chave)).toEqual(["sim", "nao", "outros"]);
    expect(g[0].votos.map((v) => v.nome)).toEqual(["Ana", "Zé"]);
    expect(g[2].votos).toHaveLength(1);
  });
});
