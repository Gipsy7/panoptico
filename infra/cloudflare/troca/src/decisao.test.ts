import { describe, expect, it } from "vitest";
import {
  FALHAS_PARA_RESERVA,
  decidir,
  enderecosDeRelease,
  eventoDeAlerta,
  estadoInicial,
  respostaSaudavel,
  type EstadoServico,
} from "./decisao";

const base = (p: Partial<EstadoServico> = {}): EstadoServico => ({ ...estadoInicial(), ...p });

describe("respostaSaudavel", () => {
  it("200 e ok", () => expect(respostaSaudavel({ status: 200, corpo: "x" })).toBe(true));
  it("timeout falha", () => expect(respostaSaudavel({ timeout: true })).toBe(false));
  it("5xx e 402 falham", () => {
    expect(respostaSaudavel({ status: 503 })).toBe(false);
    expect(respostaSaudavel({ status: 402 })).toBe(false);
  });
  it("403 com DEPLOYMENT_DISABLED falha; 403 comum nao", () => {
    expect(respostaSaudavel({ status: 403, corpo: "DEPLOYMENT_DISABLED" })).toBe(false);
    expect(respostaSaudavel({ status: 403, corpo: "Payment required" })).toBe(false);
    expect(respostaSaudavel({ status: 403, corpo: "proibido" })).toBe(true);
  });
  it("api exige banco ok", () => {
    expect(respostaSaudavel({ status: 200, corpo: '{"status":"ok","banco":"ok"}' }, true)).toBe(true);
    expect(respostaSaudavel({ status: 200, corpo: '{"status":"ok","banco":"indisponivel"}' }, true)).toBe(false);
    expect(respostaSaudavel({ status: 200, corpo: "html" }, true)).toBe(false);
  });
});

describe("decidir", () => {
  it("uma falha nao troca", () => {
    const d = decidir(base(), false, true);
    expect(d.trocarPara).toBeNull();
    expect(d.estado.falhas).toBe(1);
  });
  it("so vai para a reserva depois de FALHAS_PARA_RESERVA falhas seguidas", () => {
    let d = decidir(base(), false, true);
    for (let i = 1; i < FALHAS_PARA_RESERVA; i++) {
      expect(d.trocarPara).toBeNull();
      d = decidir(d.estado, false, true);
    }
    expect(d.trocarPara).toBe("reserva");
    expect(d.estado.ativo).toBe("reserva");
  });
  it("com a principal no ar, a reserva nao testada nao muda nada", () => {
    const d = decidir(base({ falhas: FALHAS_PARA_RESERVA - 1 }), true, false);
    expect(d.trocarPara).toBeNull();
    expect(d.estado.falhas).toBe(0);
  });
  it("nao vai se a reserva estiver doente", () => {
    const b = decidir(base({ falhas: 1 }), false, false);
    expect(b.trocarPara).toBeNull();
    expect(b.estado.ativo).toBe("principal");
  });
  it("sucesso zera as falhas", () => {
    expect(decidir(base({ falhas: 1 }), true, true).estado.falhas).toBe(0);
  });
  it("volta com 10 sucessos, nao com 9", () => {
    const r = base({ ativo: "reserva", sucessos: 8 });
    const nove = decidir(r, true, true);
    expect(nove.trocarPara).toBeNull();
    const dez = decidir(nove.estado, true, true);
    expect(dez.trocarPara).toBe("principal");
  });
  it("falha na volta zera os sucessos", () => {
    expect(decidir(base({ ativo: "reserva", sucessos: 9 }), false, true).estado.sucessos).toBe(0);
  });
  it("observar nao troca, so informa", () => {
    const d = decidir(base({ modo: "observar", falhas: FALHAS_PARA_RESERVA - 1 }), false, true);
    expect(d.trocarPara).toBeNull();
    expect(d.observou).toBe("reserva");
    expect(d.estado.ativo).toBe("principal");
  });
  it("modo reserva fixa o destino", () => {
    expect(decidir(base({ modo: "reserva" }), true, true).trocarPara).toBe("reserva");
  });
  it("modo principal fixa o destino mesmo com falhas", () => {
    expect(decidir(base({ modo: "principal", ativo: "reserva" }), false, true).trocarPara).toBe("principal");
    expect(decidir(base({ modo: "principal" }), false, true).trocarPara).toBeNull();
  });
});

describe("teto dos contadores", () => {
  it("com a origem estavel o estado para de mudar", () => {
    let e = base();
    for (let i = 0; i < 30; i++) e = decidir(e, true, true).estado;
    const congelado = JSON.stringify(e);
    expect(JSON.stringify(decidir(e, true, true).estado)).toBe(congelado);
  });
});

describe("enderecosDeRelease", () => {
  it("acha o release em hostname e em URL", () => {
    expect(
      enderecosDeRelease([
        "release.panoptico.social.br",
        "https://api-release.panoptico.social.br/saude",
        "https://RELEASE.panoptico.social.br/",
      ]),
    ).toHaveLength(3);
  });
  it("produção, teste direto e reserva passam", () => {
    expect(
      enderecosDeRelease([
        "panoptico.social.br",
        "api.panoptico.social.br",
        "https://vps.panoptico.social.br/",
        "https://api-vps.panoptico.social.br/saude",
        "https://api-reserva.panoptico.social.br/saude",
        "https://panoptico.netlify.app/",
        "781d882f-d05b-49f6-b059-638092923fc5.cfargotunnel.com",
        undefined,
        "",
      ]),
    ).toEqual([]);
  });
});

describe("eventoDeAlerta", () => {
  /** Roda os testes em sequência e devolve os eventos de cada minuto. */
  function eventos(inicio: EstadoServico, testes: [boolean, boolean][]) {
    let e = inicio;
    return testes.map(([principalOk, reservaOk]) => {
      const d = decidir(e, principalOk, reservaOk);
      const evento = eventoDeAlerta(e, d, principalOk);
      e = d.estado;
      return evento;
    });
  }

  it("avisa uma vez ao ir para a reserva e uma vez ao voltar", () => {
    const fora: [boolean, boolean] = [false, true];
    const volta: [boolean, boolean] = [true, true];
    const r = eventos(base(), [fora, fora, fora, fora, fora, ...Array(10).fill(volta), volta]);
    expect(r.slice(0, 5)).toEqual([null, null, "foi_para_reserva", null, null]);
    expect(r.slice(5, 14)).toEqual(Array(9).fill(null));
    expect(r[14]).toBe("voltou_para_principal");
    expect(r[15]).toBeNull();
  });

  it("sem reserva saudável, avisa que parou sem troca e depois que voltou", () => {
    const fora: [boolean, boolean] = [false, false];
    const r = eventos(base(), [fora, fora, fora, fora, fora, [true, false], [true, false]]);
    expect(r).toEqual([null, null, "parou_sem_troca", null, null, "voltou_a_responder", null]);
  });

  it("em modo observar também avisa que parou, sem dizer que trocou", () => {
    const fora: [boolean, boolean] = [false, true];
    const r = eventos(base({ modo: "observar" }), [fora, fora, fora, fora]);
    expect(r).toEqual([null, null, "parou_sem_troca", null]);
  });

  it("uma falha isolada não avisa", () => {
    expect(eventos(base(), [[false, true], [true, true], [false, true], [true, true]])).toEqual([
      null,
      null,
      null,
      null,
    ]);
  });
});
