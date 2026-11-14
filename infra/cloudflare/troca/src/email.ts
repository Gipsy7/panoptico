// Envio de e-mail de alerta por SMTP (porta 465, TLS desde o início), direto do Worker.
// O Worker vive fora da VPS: é ele que consegue avisar quando a VPS inteira cai.
// Sem biblioteca: o diálogo SMTP é curto e fica aqui, separado da conexão para poder ser testado.

export interface Mensagem {
  de: string;
  para: string;
  assunto: string;
  texto: string;
  data?: Date;
}

/** Fala com o servidor: lê uma resposta inteira (pode ter várias linhas) e escreve uma linha. */
export interface Canal {
  ler(): Promise<string>;
  escrever(texto: string): Promise<void>;
}

function base64(texto: string): string {
  const bytes = new TextEncoder().encode(texto);
  let binario = "";
  for (const b of bytes) binario += String.fromCharCode(b);
  return btoa(binario);
}

/** Um endereço só, sem nada que quebre a linha do comando SMTP. */
export function enderecoValido(e: string): boolean {
  return /^[^\s<>@,;:"]+@[^\s<>@,;:"]+\.[^\s<>@,;:"]+$/.test(e);
}

/** Mensagem pronta para o comando DATA: cabeçalhos, corpo em base64 e linhas com CRLF. */
export function montarMensagem(m: Mensagem): string {
  const corpo = base64(m.texto).replace(/(.{76})/g, "$1\r\n").replace(/\r\n$/, "");
  return [
    `From: Panoptico <${m.de}>`,
    `To: <${m.para}>`,
    `Subject: =?UTF-8?B?${base64(m.assunto)}?=`,
    `Date: ${(m.data ?? new Date()).toUTCString().replace("GMT", "+0000")}`,
    "MIME-Version: 1.0",
    'Content-Type: text/plain; charset="utf-8"',
    "Content-Transfer-Encoding: base64",
    "Auto-Submitted: auto-generated",
    "",
    corpo,
  ].join("\r\n");
}

/** Código de uma resposta SMTP completa (a última linha é "250 texto"; as anteriores, "250-texto"). */
export function codigoDaResposta(resposta: string): number {
  const linhas = resposta.split("\r\n").filter(Boolean);
  const ultima = linhas[linhas.length - 1] ?? "";
  return /^\d{3}( |$)/.test(ultima) ? Number(ultima.slice(0, 3)) : 0;
}

/** O diálogo inteiro. Erro diz em que passo parou e o código, nunca a senha. */
export async function conversar(
  canal: Canal,
  m: Mensagem,
  usuario: string,
  senha: string,
): Promise<void> {
  if (!enderecoValido(m.de) || !enderecoValido(m.para)) throw new Error("smtp: endereco invalido");
  const esperar = async (passo: string, ...aceitos: number[]) => {
    const codigo = codigoDaResposta(await canal.ler());
    if (!aceitos.includes(codigo)) throw new Error(`smtp: ${passo} respondeu ${codigo}`);
  };
  const mandar = async (linha: string, passo: string, ...aceitos: number[]) => {
    await canal.escrever(`${linha}\r\n`);
    await esperar(passo, ...aceitos);
  };
  await esperar("saudacao", 220);
  await mandar("EHLO panoptico.social.br", "EHLO", 250);
  await mandar("AUTH LOGIN", "AUTH", 334);
  await mandar(base64(usuario), "usuario", 334);
  await mandar(base64(senha), "senha", 235);
  await mandar(`MAIL FROM:<${m.de}>`, "MAIL FROM", 250);
  await mandar(`RCPT TO:<${m.para}>`, "RCPT TO", 250, 251);
  await mandar("DATA", "DATA", 354);
  // O corpo vai em base64: nenhuma linha começa com ponto, não precisa de "dot-stuffing".
  await mandar(`${montarMensagem(m)}\r\n.`, "mensagem", 250);
  await canal.escrever("QUIT\r\n");
}

/** Canal sobre um par de fluxos (o socket do Worker). Junta os pedaços até a resposta fechar. */
export function canalDoSocket(
  leitura: ReadableStream<Uint8Array>,
  escrita: WritableStream<Uint8Array>,
): Canal {
  const leitor = leitura.getReader();
  const escritor = escrita.getWriter();
  const decodificar = new TextDecoder();
  const codificar = new TextEncoder();
  let sobra = "";
  return {
    async ler() {
      for (;;) {
        // Resposta completa: termina em CRLF e a última linha tem espaço depois do código.
        const fim = sobra.endsWith("\r\n");
        if (fim && codigoDaResposta(sobra) > 0) {
          const resposta = sobra;
          sobra = "";
          return resposta;
        }
        const { value, done } = await leitor.read();
        if (done) throw new Error("smtp: conexao fechada");
        sobra += decodificar.decode(value, { stream: true });
        if (sobra.length > 16_384) throw new Error("smtp: resposta grande demais");
      }
    },
    async escrever(texto) {
      await escritor.write(codificar.encode(texto));
    },
  };
}

export interface ConfigEmail {
  SMTP_HOST?: string;
  SMTP_USUARIO?: string;
  SMTP_SENHA?: string;
  ALERTA_EMAIL_PARA?: string;
}

export function emailConfigurado(env: ConfigEmail): boolean {
  return Boolean(env.SMTP_USUARIO && env.SMTP_SENHA && env.ALERTA_EMAIL_PARA);
}

/** Envia pelo SMTP configurado. Quem chama trata o erro: alerta nunca pode derrubar a troca. */
export async function enviarEmail(env: ConfigEmail, assunto: string, texto: string): Promise<void> {
  const { connect } = await import("cloudflare:sockets");
  const socket = connect(
    { hostname: env.SMTP_HOST || "smtp.zoho.com", port: 465 },
    { secureTransport: "on", allowHalfOpen: false },
  );
  try {
    const limite = new Promise<never>((_, recusar) =>
      setTimeout(() => recusar(new Error("smtp: tempo esgotado")), 15_000),
    );
    await Promise.race([
      conversar(
        canalDoSocket(socket.readable, socket.writable),
        { de: env.SMTP_USUARIO!, para: env.ALERTA_EMAIL_PARA!, assunto, texto },
        env.SMTP_USUARIO!,
        env.SMTP_SENHA!,
      ),
      limite,
    ]);
  } finally {
    await socket.close().catch(() => undefined);
  }
}
