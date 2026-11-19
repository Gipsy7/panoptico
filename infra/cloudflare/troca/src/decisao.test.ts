import { describe, expect, it } from "vitest";
import {
  FALHAS_PARA_RESERVA,
  decidir,
  enderecosDeRelease,
  alertar,
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

describe("alertar", () => {
  const MIN = 60_000;
  /** Roda os testes em sequência, um por minuto, e devolve os eventos. */
  function eventos(inicio: EstadoServico, testes: [boolean, boolean][], t0 = 0) {
    let e = inicio;
    return testes.map(([principalOk, reservaOk], i) => {
      const a = alertar(decidir(e, principalOk, reservaOk), t0 + i * MIN);
      e = a.estado;
      return a.evento;
    });
  }
  const fora: [boolean, boolean] = [false, true];
  const ok: [boolean, boolean] = [true, true];

  it("avisa uma vez ao ir para a reserva e uma vez ao voltar", () => {
    const r = eventos(base(), [fora, fora, fora, fora, fora, ...Array(10).fill(ok), ok]);
    expect(r.slice(0, 5)).toEqual([null, null, "foi_para_reserva", null, null]);
    expect(r.slice(5, 14)).toEqual(Array(9).fill(null));
    expect(r[14]).toBe("voltou_para_principal");
    expect(r[15]).toBeNull();
  });

  it("sem reserva saudável, avisa que parou e só avisa a volta com a principal estável", () => {
    const semReserva: [boolean, boolean] = [false, false];
    const r = eventos(base(), [semReserva, semReserva, semReserva, semReserva, ...Array(10).fill([true, false])]);
    expect(r.slice(0, 4)).toEqual([null, null, "parou_sem_troca", null]);
    expect(r.slice(4, 13)).toEqual(Array(9).fill(null));
    expect(r[13]).toBe("voltou_a_responder");
  });

  it("oscilando (3 falhas, 1 sucesso), avisa uma vez só", () => {
    const semReserva: [boolean, boolean] = [false, false];
    const ciclo: [boolean, boolean][] = [semReserva, semReserva, semReserva, [true, false]];
    const r = eventos(base(), Array(10).fill(ciclo).flat());
    expect(r.filter(Boolean)).toEqual(["parou_sem_troca"]);
  });

  it("nova queda dentro de uma hora da anterior não avisa; depois do intervalo, avisa", () => {
    const r = eventos(base(), [fora, fora, fora, ...Array(10).fill(ok), fora, fora, fora, ...Array(60).fill(fora)]);
    const avisos = r.map((x, i) => (x ? `${i}:${x}` : null)).filter(Boolean);
    expect(avisos).toEqual(["2:foi_para_reserva", "12:voltou_para_principal", "62:foi_para_reserva"]);
  });

  it("em modo observar também avisa que parou, sem dizer que trocou", () => {
    const r = eventos(base({ modo: "observar" }), [fora, fora, fora, fora]);
    expect(r).toEqual([null, null, "parou_sem_troca", null]);
  });

  it("uma falha isolada não avisa", () => {
    expect(eventos(base(), [fora, ok, fora, ok])).toEqual([null, null, null, null]);
  });
});
