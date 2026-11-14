import { describe, expect, it } from "vitest";

import {
  canalDoSocket,
  codigoDaResposta,
  conversar,
  emailConfigurado,
  enderecoValido,
  montarMensagem,
  type Canal,
  type Mensagem,
} from "./email";

const MENSAGEM: Mensagem = {
  de: "robo@exemplo.test",
  para: "dono@exemplo.test",
  assunto: "Panóptico: a API caiu",
  texto: "A API principal não respondeu em 3 testes seguidos.\n.linha que começa com ponto",
  data: new Date("2026-11-13T18:00:00Z"),
};

function texto(base: string): string {
  return new TextDecoder().decode(Uint8Array.from(atob(base), (c) => c.charCodeAt(0)));
}

/** Servidor de mentira: responde na ordem e guarda o que o cliente escreveu. */
function canalFalso(respostas: string[]): Canal & { escrito: string[] } {
  const escrito: string[] = [];
  return {
    escrito,
    ler: async () => respostas.shift() ?? "",
    escrever: async (t) => void escrito.push(t),
  };
}

const BOAS = [
  "220 smtp pronto\r\n",
  "250-smtp\r\n250-AUTH LOGIN PLAIN\r\n250 SIZE 100\r\n",
  "334 VXNlcm5hbWU6\r\n",
  "334 UGFzc3dvcmQ6\r\n",
  "235 ok\r\n",
  "250 ok\r\n",
  "250 ok\r\n",
  "354 manda\r\n",
  "250 recebido\r\n",
];

describe("montarMensagem", () => {
  it("põe o assunto e o corpo em base64, com CRLF e sem acento solto", () => {
    const m = montarMensagem(MENSAGEM);
    const [cabecalhos, corpo] = m.split("\r\n\r\n");
    expect(cabecalhos).toContain("From: Panoptico <robo@exemplo.test>");
    expect(cabecalhos).toContain("To: <dono@exemplo.test>");
    expect(cabecalhos).toContain("Date: Fri, 13 Nov 2026 18:00:00 +0000");
    const assunto = /Subject: =\?UTF-8\?B\?(.+)\?=/.exec(cabecalhos)![1];
    expect(texto(assunto)).toBe("Panóptico: a API caiu");
    expect(texto(corpo.replace(/\r\n/g, ""))).toBe(MENSAGEM.texto);
    // eslint-disable-next-line no-control-regex
    expect(/^[\x00-\x7f]*$/.test(m)).toBe(true);
    expect(m.split("\r\n").every((l) => l.length <= 78 && !l.startsWith("."))).toBe(true);
    expect(m.replace(/\r\n/g, "")).not.toMatch(/[\r\n]/);
  });
});

describe("codigoDaResposta", () => {
  it("lê o código da última linha", () => {
    expect(codigoDaResposta("250-a\r\n250-b\r\n250 c\r\n")).toBe(250);
    expect(codigoDaResposta("535 5.7.8 senha errada\r\n")).toBe(535);
    expect(codigoDaResposta("250-ainda vem mais\r\n")).toBe(0);
    expect(codigoDaResposta("")).toBe(0);
  });
});

describe("conversar", () => {
  it("segue o diálogo SMTP e termina a mensagem com ponto", async () => {
    const canal = canalFalso([...BOAS]);
    await conversar(canal, MENSAGEM, "robo@exemplo.test", "segredo");
    const linhas = canal.escrito;
    expect(linhas[0]).toBe("EHLO panoptico.social.br\r\n");
    expect(linhas[1]).toBe("AUTH LOGIN\r\n");
    expect(texto(linhas[2].trim())).toBe("robo@exemplo.test");
    expect(texto(linhas[3].trim())).toBe("segredo");
    expect(linhas[4]).toBe("MAIL FROM:<robo@exemplo.test>\r\n");
    expect(linhas[5]).toBe("RCPT TO:<dono@exemplo.test>\r\n");
    expect(linhas[6]).toBe("DATA\r\n");
    expect(linhas[7].endsWith("\r\n.\r\n")).toBe(true);
    expect(linhas[8]).toBe("QUIT\r\n");
  });

  it("para no passo que falhou e não põe a senha no erro", async () => {
    const respostas = [...BOAS];
    respostas[4] = "535 5.7.8 senha errada\r\n";
    const canal = canalFalso(respostas);
    const erro = await conversar(canal, MENSAGEM, "robo@exemplo.test", "segredo").catch((e) => e);
    expect(erro.message).toBe("smtp: senha respondeu 535");
    expect(erro.message).not.toContain("segredo");
    expect(canal.escrito.some((l) => l.startsWith("MAIL FROM"))).toBe(false);
  });

  it("recusa endereço que quebraria o comando", async () => {
    const canal = canalFalso([...BOAS]);
    const ruim = { ...MENSAGEM, para: "a@b.test>\r\nRCPT TO:<x@y.test" };
    await expect(conversar(canal, ruim, "u", "s")).rejects.toThrow("endereco invalido");
    expect(canal.escrito).toEqual([]);
    expect(enderecoValido("mikael@exemplo.test")).toBe(true);
    expect(enderecoValido("sem-arroba")).toBe(false);
  });
});

describe("canalDoSocket", () => {
  it("junta os pedaços até a resposta de várias linhas fechar", async () => {
    const codificar = new TextEncoder();
    const pedacos = ["250-smtp\r\n250-AU", "TH LOGIN\r\n", "250 SIZE\r\n", "220 outra\r\n"];
    const leitura = new ReadableStream<Uint8Array>({
      pull(c) {
        const p = pedacos.shift();
        if (p) c.enqueue(codificar.encode(p));
        else c.close();
      },
    });
    const escrito: string[] = [];
    const escrita = new WritableStream<Uint8Array>({
      write: (b) => void escrito.push(new TextDecoder().decode(b)),
    });
    const canal = canalDoSocket(leitura, escrita);
    expect(await canal.ler()).toBe("250-smtp\r\n250-AUTH LOGIN\r\n250 SIZE\r\n");
    expect(await canal.ler()).toBe("220 outra\r\n");
    await canal.escrever("EHLO x\r\n");
    expect(escrito).toEqual(["EHLO x\r\n"]);
    await expect(canal.ler()).rejects.toThrow("conexao fechada");
  });
});

describe("emailConfigurado", () => {
  it("só com usuário, senha e destino", () => {
    expect(emailConfigurado({})).toBe(false);
    expect(emailConfigurado({ SMTP_USUARIO: "a", SMTP_SENHA: "b" })).toBe(false);
    expect(emailConfigurado({ SMTP_USUARIO: "a", SMTP_SENHA: "b", ALERTA_EMAIL_PARA: "c" })).toBe(true);
  });
});
