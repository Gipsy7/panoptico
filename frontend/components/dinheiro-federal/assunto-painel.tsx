"use client";

/**
 * Painel do Mapa (protótipo A): primeiro os caminhos do lugar (os mesmos destinos da home: quem
 * representa a cidade e tudo sobre ela; no estado, "Por dentro" e os representantes); depois o
 * assunto escolhido em camadas: o número do lugar com a comparação, "aprofundar" (a série e a nota)
 * e o link para tudo sobre o assunto. "Dinheiro" continua com o conteúdo de impostos e repasses.
 */
import Link from "next/link";
import { useEffect, useState } from "react";

import { IconeAssunto } from "@/components/icone-assunto";
import { BotaoAvisoLugar } from "@/components/botao-aviso-lugar";
import { EixoAnos, LinhaSerie, resumoSerie } from "@/components/tempo/eixo-tempo";
import { dominioDe } from "@/components/tempo/ao-longo-do-tempo";
import { getTempoEstado, getTempoMunicipio, type IndicadoresUfs, type TempoDoLugar } from "@/lib/api";
import { type AssuntoMapa, formatarIndicadorAssunto, ultimoPonto } from "@/lib/assuntos-mapa";

type Lugar = { uf: string | null; ufNome: string; ibge: string | null; nomeCidade: string };

function Caminho({ href, icone, titulo, texto }: { href: string; icone: "pessoa" | "lugar"; titulo: string; texto: string }) {
  return (
    <Link
      href={href}
      className="group flex items-center gap-3 border border-l-4 border-border bg-card px-3 py-2.5 hover:border-foreground"
      style={{ borderLeftColor: "var(--bronze)" }}
    >
      <span className="text-bronze">
        <IconeAssunto assunto={icone} className="size-6" />
      </span>
      <span className="flex min-w-0 flex-col">
        <span className="font-semibold">{titulo}</span>
        <span className="text-sm text-muted-foreground">{texto}</span>
      </span>
      <span aria-hidden className="ml-auto text-lg transition-transform group-hover:translate-x-0.5">
        →
      </span>
    </Link>
  );
}

export function CaminhosDoLugar({ uf, ufNome, ibge, nomeCidade }: Lugar) {
  if (!uf) {
    return (
      <div className="flex flex-col gap-3">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <IconeAssunto assunto="mao" className="size-5 text-bronze" />
          Toque num estado no mapa para entrar nele; depois, numa cidade.
        </p>
        <BotaoAvisoLugar uf={null} nome="Brasil" />
      </div>
    );
  }
  return (
    <nav aria-label={`Caminhos a partir de ${ibge ? nomeCidade : ufNome}`} className="flex flex-col gap-2">
      {ibge ? (
        <>
          <Caminho
            href={`/representantes?municipio=${ibge}`}
            icone="pessoa"
            titulo={`Quem representa ${nomeCidade}`}
            texto="Prefeito, vereadores, governador, deputados e senadores"
          />
          <Caminho href={`/cidade/${ibge}`} icone="lugar" titulo={`Tudo sobre ${nomeCidade}`} texto="Por dentro da cidade, assunto por assunto" />
        </>
      ) : (
        <>
          <Caminho
            href={`/representantes?uf=${uf}`}
            icone="pessoa"
            titulo={`Quem representa ${ufNome}`}
            texto="Governador, deputados e senadores do estado"
          />
          <Caminho href={`/estado/${uf}`} icone="lugar" titulo={`Tudo sobre ${ufNome}`} texto="Por dentro do estado, assunto por assunto" />
        </>
      )}
      <BotaoAvisoLugar uf={uf} ibge={ibge} nome={ibge ? nomeCidade : ufNome} />
    </nav>
  );
}

export function CamadaAssunto({
  assunto,
  lugar,
  indUf,
  indMun,
}: {
  assunto: AssuntoMapa;
  lugar: Lugar;
  indUf: IndicadoresUfs | null;
  indMun: IndicadoresUfs | null;
}) {
  const [aberto, setAberto] = useState(false);
  const [tempo, setTempo] = useState<{ chave: string; dados: TempoDoLugar | null } | null>(null);
  const { uf, ufNome, ibge, nomeCidade } = lugar;
  const chave = `${uf}|${ibge}`;
  const cor = `var(--tema-${assunto.tema})`;

  useEffect(() => {
    if (!aberto || !uf || tempo?.chave === chave) return;
    let vivo = true;
    (ibge ? getTempoMunicipio(ibge) : getTempoEstado(uf)).then((r) => vivo && setTempo({ chave, dados: r.ok ? r.dados : null }));
    return () => {
      vivo = false;
    };
  }, [aberto, uf, ibge, chave, tempo?.chave]);

  if (!assunto.indicador) return null;
  // Homicídios: cidade e estado na mesma conta (média dos 3 últimos anos).
  const idUf = assunto.indicador === "homicidios" ? "homicidios_media3" : assunto.indicador;
  const iUf = indUf?.indicadores.find((i) => i.id === idUf);
  const iMun = indMun?.indicadores.find((i) => i.id === assunto.indicador);
  const ref = ibge ? iMun : iUf;
  const ponto = ibge ? ultimoPonto(iMun, ibge) : uf ? ultimoPonto(iUf, uf) : null;
  const pontoUf = ibge && uf ? ultimoPonto(iUf, uf) : null;
  const valores = iUf ? Object.values(iUf.valores).map((p) => p[p.length - 1]?.valor).filter((v): v is number => v != null) : [];

  const nomeLugar = ibge ? nomeCidade : uf ? ufNome : "Brasil";
  const serie = tempo?.chave === chave ? tempo.dados?.series.find((s) => s.id === assunto.serie) : undefined;
  const d = tempo?.dados ? dominioDe(tempo.dados) : null;

  return (
    <section className="flex flex-col gap-2 border border-l-4 border-border bg-card p-3" style={{ borderLeftColor: cor }} aria-label={`${assunto.nome} em ${nomeLugar}`}>
      <p className="flex items-center gap-2 text-xs font-semibold tracking-wider uppercase" style={{ color: cor }}>
        <IconeAssunto assunto={assunto.icone} className="size-4" />
        {assunto.nome} · {nomeLugar}
      </p>
      {!uf ? (
        valores.length > 0 &&
        iUf && (
          <p className="text-sm">
            {iUf.titulo}: de {formatarIndicadorAssunto(iUf, Math.min(...valores))} a {formatarIndicadorAssunto(iUf, Math.max(...valores))} entre os
            estados. Toque num estado.
          </p>
        )
      ) : ponto && ref ? (
        <>
          <p className="numero text-3xl leading-none">{formatarIndicadorAssunto(ref, ponto.valor)}</p>
          <p className="text-sm">
            {/^\p{Lu}{2}/u.test(ref.titulo) ? ref.titulo : ref.titulo.charAt(0).toLowerCase() + ref.titulo.slice(1)}
            {ref.titulo.includes("média") ? "" : `, ${ponto.ano}`}
            {pontoUf && iUf ? (
              <span className="text-muted-foreground">
                {" "}
                ({ufNome}: {formatarIndicadorAssunto(iUf, pontoUf.valor)})
              </span>
            ) : null}
          </p>
        </>
      ) : (
        <p className="text-sm text-muted-foreground">Sem dado deste assunto para {nomeLugar}.</p>
      )}

      {uf && (
        <button
          type="button"
          aria-expanded={aberto}
          onClick={() => setAberto((a) => !a)}
          className="inline-flex min-h-9 items-center gap-1.5 self-start border border-foreground px-2.5 text-sm"
        >
          {aberto ? "Fechar" : "Aprofundar"}
          <span aria-hidden className={`inline-block transition-transform ${aberto ? "rotate-90" : ""}`}>
            ▸
          </span>
        </button>
      )}
      {aberto && uf && (
        <div className="flex flex-col gap-2 border-l-2 border-dashed border-border pl-3">
          {serie && d ? (
            <>
              <p className="text-sm font-semibold">
                {serie.rotulo} <span className="font-normal text-muted-foreground">({serie.unidade})</span>
              </p>
              <p className="text-xs text-muted-foreground">{resumoSerie(serie, d)}</p>
              <LinhaSerie d={d} s={serie} cor={cor} nomeEstado={uf} nomeLugar={ibge ? nomeCidade : uf} altura={80} />
              <EixoAnos d={d} reserva={serie.comparacoes.length > 0} />
            </>
          ) : assunto.serie && tempo?.chave !== chave ? (
            <p className="text-sm text-muted-foreground">Carregando a série…</p>
          ) : null}
          {ref?.nota && <p className="text-xs text-muted-foreground">{ref.nota}</p>}
          <Link href={ibge ? `/cidade/${ibge}` : `/estado/${uf}`} className="text-sm underline underline-offset-4">
            Tudo sobre {assunto.nome.toLowerCase()} em {nomeLugar} →
          </Link>
        </div>
      )}
      {ref && <p className="text-xs text-muted-foreground">Fonte: {ref.fonte_nome}.</p>}
    </section>
  );
}
