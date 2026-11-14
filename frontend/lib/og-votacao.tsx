import { ImageResponse } from "next/og";

import { type FormatoCartao, FORMATOS } from "@/lib/cartao-cidade";
import { type ChaveGrupo, type GrupoCartao, nomesCortados } from "@/lib/cartao-votacao";
import { LINHAS_MARCA } from "@/lib/marca-svg";
import { carregarFontes } from "@/lib/og-cidade";

// Cartão "Como votaram os deputados de [estado]" (docs/DECISOES.md, 2026-11-14). Mesma paleta
// escura dos cartões de perfil e de cidade. Sim é cheio e Não é vazado, como nas cadeiras do
// site: nenhuma cor de certo ou errado.

const TINTA = "#141414";
const PAPEL = "#f4f1ea";
const BRONZE_CL = "#c9954a";
const AREIA = "#c4a77d";
const TERRA = "#8f7650";
const CINZA = "#6e6a63";
const CINZA_CL = "#a39d92";

export type PessoaCartaoVotacao = { parlamentar_id: number; nome: string; foto: string | null };
export type GrupoComFotos = Omit<GrupoCartao, "pessoas"> & { pessoas: PessoaCartaoVotacao[] };

export type DadosCartaoVotacao = {
  formato: FormatoCartao;
  /** "Como votaram os deputados de SC". */
  titulo: string;
  /** "PLP 186/2026" ou nulo quando a votação não tem proposição ligada. */
  proposicao: string | null;
  /** "Aprovada" | "Rejeitada" | nulo. */
  resultado: string | null;
  ementa: string | null;
  /** "Câmara" | "Senado". */
  casa: string;
  /** Data da votação, já formatada. */
  data: string;
  grupos: GrupoComFotos[];
  /** Com fotos (estado de até 20 pessoas na votação) ou só nomes. */
  comFotos: boolean;
  /** "Fonte: … · atualizado em …". */
  rodape: string;
  /** Aviso de recorte ("A Câmara só publica quem registrou voto.") ou nulo. */
  nota: string | null;
  /** "panoptico.social.br/votacao/camara/123". */
  link: string;
};

function Sol({ tamanho }: { tamanho: number }) {
  return (
    <svg width={tamanho} height={tamanho} viewBox="0 0 64 64">
      <g fill="none" stroke={BRONZE_CL} strokeLinecap="round" strokeWidth={3.4}>
        {LINHAS_MARCA.map((l, i) => (
          <line key={i} {...l} />
        ))}
        <circle cx={32} cy={32} r={8} />
      </g>
    </svg>
  );
}

/** A marca do voto: Sim cheio, Não vazado, outro registro tracejado. */
function marca(chave: ChaveGrupo, lado: number) {
  const base = { display: "flex", width: lado, height: lado, borderRadius: lado } as const;
  if (chave === "sim") return <div style={{ ...base, background: BRONZE_CL }} />;
  if (chave === "nao") return <div style={{ ...base, border: `${Math.max(3, Math.round(lado / 7))}px solid ${PAPEL}` }} />;
  return <div style={{ ...base, border: `${Math.max(2, Math.round(lado / 9))}px dashed ${CINZA_CL}` }} />;
}

function Foto({ p, chave, largura, altura }: { p: PessoaCartaoVotacao; chave: ChaveGrupo; largura: number; altura: number }) {
  return (
    <div
      style={{
        position: "relative",
        display: "flex",
        width: largura,
        height: altura,
        background: p.foto ? BRONZE_CL : TERRA,
        overflow: "hidden",
        alignItems: "flex-end",
        justifyContent: "center",
      }}
    >
      {p.foto ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={p.foto}
          alt=""
          width={largura}
          height={altura}
          style={{ position: "absolute", top: 0, left: 0, objectFit: "cover", objectPosition: "50% 18%", filter: "grayscale(1) contrast(1.1)" }}
        />
      ) : (
        <svg width={Math.round(altura * 0.8)} height={Math.round(altura * 0.8)} viewBox="0 0 100 100">
          <circle cx={50} cy={40} r={19} fill={AREIA} />
          <path d="M12 104C12 74 30 63 50 63S88 74 88 104Z" fill={AREIA} />
        </svg>
      )}
      <div style={{ position: "absolute", left: 6, bottom: 6, display: "flex", background: TINTA, padding: 4, borderRadius: 99 }}>
        {marca(chave, Math.round(largura * 0.17))}
      </div>
    </div>
  );
}

export async function cartaoVotacao(d: DadosCartaoVotacao): Promise<ImageResponse> {
  const { width, height } = FORMATOS[d.formato];
  const stories = d.formato === "stories";
  const k = stories ? 1.18 : 1; // tudo um pouco maior no Stories
  const px = (n: number) => Math.round(n * k);
  const margem = stories ? 72 : 60;
  const util = width - margem * 2;
  const n = (chave: ChaveGrupo) => d.grupos.find((g) => g.chave === chave)?.pessoas.length ?? 0;
  const total = n("sim") + n("nao") + n("outros");
  const comGente = d.grupos.filter((g) => g.pessoas.length > 0);

  // Fotos: 9 por linha; a altura encolhe quando o estado tem muita gente num grupo.
  const porLinha = 9;
  const gap = 8;
  const larguraFoto = Math.floor((util - gap * (porLinha - 1)) / porLinha);
  const linhasDeFotos = comGente.reduce((s, g) => s + Math.ceil(g.pessoas.length / porLinha), 0);
  const alturaFoto = Math.round(larguraFoto * (stories || linhasDeFotos <= 3 ? 1.25 : 1.05));
  // Só nomes: os caracteres disponíveis são divididos entre os grupos na proporção de cada um.
  const caracteres = stories ? 800 : 560;
  const cota = (pessoas: number) => Math.max(90, Math.floor((caracteres * pessoas) / Math.max(1, total)));

  const topo = (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: px(36), fontWeight: 700 }}>
        <Sol tamanho={px(44)} />
        Panóptico
      </div>
      <div style={{ display: "flex", fontSize: px(24), color: BRONZE_CL, fontWeight: 700, letterSpacing: "0.08em" }}>
        {`${d.casa.toUpperCase()} · ${d.data}`}
      </div>
    </div>
  );

  const cabecalho = (
    <div style={{ display: "flex", flexDirection: "column", gap: px(10) }}>
      <div style={{ display: "flex", fontSize: px(stories ? 45 : 54), fontWeight: 700, lineHeight: 1.02, letterSpacing: "-0.02em" }}>{d.titulo}</div>
      {(d.proposicao || d.resultado) && (
        <div style={{ display: "flex", alignItems: "baseline", gap: 16, fontSize: px(46), fontWeight: 700 }}>
          {d.proposicao && <span style={{ color: BRONZE_CL }}>{d.proposicao}</span>}
          {d.resultado && <span style={{ fontSize: px(30), color: CINZA_CL, fontWeight: 400 }}>{`${d.resultado} no Plenário`}</span>}
        </div>
      )}
      {d.ementa && <div style={{ display: "flex", fontSize: px(24), color: CINZA_CL, lineHeight: 1.25 }}>{d.ementa}</div>}
    </div>
  );

  const barra = total > 0 && (
    <div style={{ display: "flex", width: util, height: px(22), border: `3px solid ${PAPEL}` }}>
      {n("sim") > 0 && <div style={{ display: "flex", flexGrow: n("sim"), background: BRONZE_CL }} />}
      {n("nao") > 0 && <div style={{ display: "flex", flexGrow: n("nao") }} />}
      {n("outros") > 0 && <div style={{ display: "flex", flexGrow: n("outros"), background: CINZA }} />}
    </div>
  );

  const placar = (
    <div style={{ display: "flex", alignItems: "flex-end", gap: px(44) }}>
      {d.grupos
        .filter((g) => g.chave !== "outros" || g.pessoas.length > 0)
        .map((g) => (
          <div key={g.chave} style={{ display: "flex", alignItems: "flex-end", gap: 14 }}>
            <div style={{ display: "flex", fontSize: px(g.chave === "outros" ? 84 : 132), fontWeight: 700, lineHeight: 0.85, color: g.chave === "sim" ? BRONZE_CL : PAPEL }}>
              {g.pessoas.length}
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: px(30), paddingBottom: 6 }}>
              {marca(g.chave, px(24))}
              {g.rotulo}
            </div>
          </div>
        ))}
    </div>
  );

  const grupos = (
    <div style={{ display: "flex", flexDirection: "column", gap: px(d.comFotos ? 16 : 22) }}>
      {comGente.map((g) => (
        <div key={g.chave} style={{ display: "flex", flexDirection: "column", gap: px(8) }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: px(28), fontWeight: 700 }}>
            {marca(g.chave, px(22))}
            {`${g.rotulo} · ${g.pessoas.length}`}
          </div>
          {d.comFotos && (
            <div style={{ display: "flex", flexWrap: "wrap", gap, width: util }}>
              {g.pessoas.map((p) => (
                <Foto key={p.parlamentar_id} p={p} chave={g.chave} largura={larguraFoto} altura={alturaFoto} />
              ))}
            </div>
          )}
          <div style={{ display: "flex", fontSize: px(d.comFotos ? 21 : 26), lineHeight: 1.3, color: d.comFotos ? CINZA_CL : PAPEL }}>
            {nomesCortados(
              g.pessoas.map((p) => p.nome),
              d.comFotos ? (stories ? 330 : 250) : cota(g.pessoas.length),
            )}
          </div>
        </div>
      ))}
    </div>
  );

  return new ImageResponse(
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        gap: px(stories ? 34 : 22),
        background: TINTA,
        color: PAPEL,
        padding: stories ? `${250}px ${margem}px 0` : `${px(44)}px ${margem}px 0`,
      }}
    >
      {topo}
      {cabecalho}
      {!d.comFotos && placar}
      {barra}
      {grupos}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
          marginTop: "auto",
          paddingBottom: stories ? 230 : 30,
          fontSize: px(21),
          color: CINZA_CL,
        }}
      >
        <div style={{ display: "flex" }}>{d.rodape}</div>
        {d.nota && <div style={{ display: "flex" }}>{d.nota}</div>}
        <div style={{ display: "flex", color: PAPEL, fontSize: px(26), fontWeight: 700 }}>{d.link}</div>
      </div>
    </div>,
    { width, height, fonts: await carregarFontes() },
  );
}
