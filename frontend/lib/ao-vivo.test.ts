import { describe, expect, it } from "vitest";

import { type AoVivo, type CasaAoVivo, conferidoEm, diaCurto, diaEHora, horaLocal, seloDe } from "./ao-vivo";

function casa(parcial: Partial<CasaAoVivo>): CasaAoVivo {
  return {
    casa: "camara",
    situacao: "sem",
    titulo: null,
    inicio: null,
    itens: [],
    total_itens: 0,
    url_video: null,
    rotulo_video: "TV Câmara",
    proxima: null,
    indisponivel: false,
    conferido_em: null,
    ...parcial,
  };
}

const dados = (...casas: CasaAoVivo[]): AoVivo => ({
  conferido_em: null,
  fonte_nome: "x",
  fonte_url: "https://x",
  casas,
});

describe("datas e horas", () => {
  it("formata hora, dia e dia da semana sem depender do fuso", () => {
    expect(horaLocal("2026-11-10T14:06")).toBe("14h06");
    expect(horaLocal("2026-11-10T09:00")).toBe("9h");
    expect(diaCurto("2026-11-10T09:00")).toBe("10/11");
    expect(diaEHora("2026-11-10T13:55")).toBe("terça, 10/11, às 13h55");
  });
  it("converte o instante UTC para Brasília", () => {
    expect(conferidoEm("2026-11-10T18:42:00+00:00")).toBe("10/11/2026, às 15h42");
  });
});

describe("selo do cabeçalho", () => {
  it("fica oculto sem dados ou sem nada a dizer", () => {
    expect(seloDe(null)).toBeNull();
    expect(seloDe(dados(casa({ indisponivel: true }), casa({ casa: "senado" })))).toBeNull();
  });
  it("diz 'Ao vivo' com sessão em andamento", () => {
    const s = seloDe(dados(casa({ situacao: "agora" }), casa({ casa: "senado" })));
    expect(s?.tipo).toBe("agora");
    expect(s?.rotulo).toBe("Ao vivo");
    expect(s?.leitor).toContain("Câmara");
  });
  it("sem sessão, mostra a data da mais próxima", () => {
    const s = seloDe(
      dados(
        casa({ situacao: "proxima", proxima: { inicio: "2026-11-12T13:55", titulo: "a" } }),
        casa({ casa: "senado", situacao: "proxima", proxima: { inicio: "2026-11-10T14:00", titulo: "b" } }),
      ),
    );
    expect(s?.tipo).toBe("proxima");
    expect(s?.rotulo).toBe("Próx. 10/11");
  });
});
