import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { AbasTema, type AbaTema } from "@/components/abas-tema";
import { Bancada } from "@/components/casa/bancada";
import { Chapa, cargoDoVice } from "@/components/chapa";
import { FotoOuIniciais } from "@/components/eleitos-secao";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { Revelacao } from "@/components/revelacao";
import { getBancadasEstado, getContasEstado, getDinheiroFederalUf, getExecutivo } from "@/lib/api";
import { formatarReais, formatarReaisCompacto } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

/**
 * Raio-X do estado (redesenho, etapa 4): o mesmo modelo da cidade, só com o que já está carregado
 * (moradores, dinheiro da União, contas do governo do estado, governador e vice, bancadas). As telas
 * completas continuam onde estão; "Tudo sobre" leva a elas.
 */

function estadoDe(uf: string) {
  return UFS.find((u) => u.sigla === uf.toUpperCase()) ?? null;
}

export async function generateMetadata({ params }: PageProps<"/estado/[uf]">): Promise<Metadata> {
  const { uf } = await params;
  const e = estadoDe(uf);
  if (!e) return { title: "Estado" };
  return {
    title: `Raio-X de ${e.nome}: dinheiro público e quem governa`,
    description: `${e.nome}: moradores, quanto a União arrecada e repassa, contas do governo do estado, governador e vice e as bancadas, com dados oficiais, fonte e data.`,
  };
}

export default function EstadoPage({ params }: PageProps<"/estado/[uf]">) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o estado…" secoes={3} />}>
      {params.then(({ uf }) => (
        <Estado uf={uf.toUpperCase()} />
      ))}
    </Revelacao>
  );
}

const num = (n: number) => n.toLocaleString("pt-BR");

async function Estado({ uf }: { uf: string }) {
  const e = estadoDe(uf);
  if (!e) notFound();
  const [federalR, contasR, executivoR, bancadasR] = await Promise.all([
    getDinheiroFederalUf(uf),
    getContasEstado(uf),
    getExecutivo(uf),
    getBancadasEstado(uf),
  ]);
  const federal = federalR.ok && !federalR.dados.sem_dados ? federalR.dados : null;
  const contas = contasR.ok ? contasR.dados : null;
  const governador = executivoR.ok ? executivoR.dados.governador : null;
  const bancadas = bancadasR.ok ? bancadasR.dados : null;
  const populacao = federal?.populacao ?? contas?.populacao ?? null;
  const cidades = federal?.cidades.length ?? null;

  // Frase do Raio-X: só fatos com fonte, sem adjetivo; o que não houver fica de fora.
  const partes: string[] = [];
  if (populacao != null) partes.push(`${e.nome} tem ${num(populacao)} moradores${cidades ? ` em ${num(cidades)} cidades` : ""}.`);
  if (federal?.arrecadacao != null && federal.repasse != null)
    partes.push(
      `Em ${federal.ano}, a União arrecadou ${formatarReaisCompacto(federal.arrecadacao)} no estado e repassou ${formatarReaisCompacto(federal.repasse)} ao governo do estado e às prefeituras.`,
    );
  if (contas?.despesa_por_habitante != null)
    partes.push(
      `O governo do estado gastou ${formatarReais(contas.despesa_por_habitante, true)} por morador em ${contas.ano}${contas.media_estados_despesa_por_habitante != null ? ` (média dos estados: ${formatarReais(contas.media_estados_despesa_por_habitante, true)})` : ""}.`,
    );

  const numero = (rotulo: string, valor: string) => (
    <div className="border-t-2 border-foreground pt-2">
      <dt className="text-sm text-muted-foreground">{rotulo}</dt>
      <dd className="numero text-2xl">{valor}</dd>
    </div>
  );

  const abas: AbaTema[] = [];
  if (populacao != null || cidades) {
    abas.push({
      id: "retrato",
      rotulo: "Retrato",
      tema: "eleicoes",
      conteudo: (
        <div className="flex flex-col gap-3">
          <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {populacao != null &&
              numero(`Moradores${federal?.populacao_ano ? ` (${federal.populacao_ano})` : ""}`, num(populacao))}
            {cidades != null && numero("Cidades", num(cidades))}
            {bancadas && bancadas.assembleia.total > 0 && numero("Cadeiras na Assembleia", num(bancadas.assembleia.total))}
          </dl>
          <p className="text-sm text-muted-foreground">
            Economia, escolas, saúde e obras entram aqui quando os dados do IBGE, do INEP, do DATASUS e do Obrasgov forem
            carregados.
          </p>
          <FonteRodape fonte="IBGE (população)" atualizadoEm={null} />
        </div>
      ),
    });
  }
  if (federal || contas) {
    abas.push({
      id: "dinheiro",
      rotulo: "Dinheiro público",
      tema: "dinheiro",
      conteudo: (
        <div className="flex flex-col gap-4">
          <dl className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {federal?.arrecadacao != null && numero(`União arrecadou em ${federal.ano}`, formatarReaisCompacto(federal.arrecadacao))}
            {federal?.repasse != null && numero(`União repassou em ${federal.ano}`, formatarReaisCompacto(federal.repasse))}
            {contas?.despesa_por_habitante != null &&
              numero(`Governo do estado gastou por morador em ${contas.ano}`, formatarReais(contas.despesa_por_habitante, true))}
            {contas?.media_estados_despesa_por_habitante != null &&
              numero("Média dos estados, por morador", formatarReais(contas.media_estados_despesa_por_habitante, true))}
            {contas?.assembleia != null &&
              numero(`Gasto na área Legislativa em ${contas.ano}`, formatarReaisCompacto(contas.assembleia))}
          </dl>
          <ul className="flex flex-col gap-1 text-sm">
            <li>
              <Link href={`/impostos-e-repasses/${uf}`} className="underline underline-offset-4">
                Impostos e repasses de {e.nome}, cidade por cidade
              </Link>
            </li>
          </ul>
          {federal && (
            <FonteRodape fonte={federal.fontes[0]?.nome ?? "Tesouro Nacional e Receita Federal"} url={federal.fontes[0]?.url} atualizadoEm={federal.fontes[0]?.atualizado_em ?? null} />
          )}
          {contas && <FonteRodape fonte={contas.fonte_nome} url={contas.fonte_url} atualizadoEm={contas.atualizado_em} />}
        </div>
      ),
    });
  }
  if (governador || bancadas) {
    abas.push({
      id: "politica",
      rotulo: "Política",
      tema: "votos",
      conteudo: (
        <div className="flex flex-col gap-5">
          {governador && (
            <Chapa
              titular={{
                nome: governador.titular.nome_urna,
                partido: governador.titular.partido,
                cargo: governador.cargo,
                href: `/eleito/${governador.titular.id}`,
                retrato: <FotoOuIniciais eleito={governador.titular} tamanho={40} decorativa />,
              }}
              vice={
                governador.vice && {
                  nome: governador.vice.nome_urna,
                  partido: governador.vice.partido,
                  cargo: cargoDoVice(governador.cargo),
                  href: `/eleito/${governador.vice.id}`,
                  retrato: <FotoOuIniciais eleito={governador.vice} tamanho={40} decorativa />,
                }
              }
              rodape={`Eleitos juntos, na mesma chapa, em ${governador.ano_eleicao}.`}
            />
          )}
          {bancadas && (
            <>
              <Bancada
                titulo="Assembleia Legislativa"
                itens={bancadas.assembleia.itens}
                total={bancadas.assembleia.total}
                fonte={bancadas.assembleia.fonte_nome}
                fonteUrl={bancadas.assembleia.fonte_url}
                atualizadoEm={bancadas.assembleia.atualizado_em}
              />
              <Bancada
                titulo={`Deputados federais de ${e.nome}`}
                itens={bancadas.camara_uf.itens}
                total={bancadas.camara_uf.total}
                fonte={bancadas.camara_uf.fonte_nome}
                fonteUrl={bancadas.camara_uf.fonte_url}
                atualizadoEm={bancadas.camara_uf.atualizado_em}
              />
              <Bancada
                titulo={`Senadores de ${e.nome}`}
                itens={bancadas.senado_uf.itens}
                total={bancadas.senado_uf.total}
                fonte={bancadas.senado_uf.fonte_nome}
                fonteUrl={bancadas.senado_uf.fonte_url}
                atualizadoEm={bancadas.senado_uf.atualizado_em}
              />
            </>
          )}
        </div>
      ),
    });
  }

  const tudo = [
    { href: `/representantes?uf=${uf}`, rotulo: `Quem representa ${e.nome}`, texto: "Governador, senadores, deputados federais e estaduais" },
    { href: `/impostos-e-repasses/${uf}`, rotulo: "Impostos e repasses", texto: "O que a União arrecada e repassa, cidade por cidade" },
    { href: `/parlamentares?uf=${uf}`, rotulo: "Deputados federais e senadores", texto: "Gastos, presença e projetos, com a média da Casa" },
    { href: `/projetos?esfera=estadual&uf=${uf}`, rotulo: "Projetos na Assembleia", texto: "O que está sendo votado no estado" },
  ];

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <p className="sobretitulo">Raio-X · Estado</p>
          <h1 className="titulo-pagina">{e.nome}</h1>
          {partes.length > 0 && <p className="max-w-3xl text-lg leading-snug">{partes.join(" ")}</p>}
        </div>
        {abas.length > 0 ? (
          <AbasTema rotulo={`Temas de ${e.nome}`} abas={abas} />
        ) : (
          <p className="text-muted-foreground">Ainda não há dados carregados para este estado.</p>
        )}
      </div>

      <section aria-labelledby="tudo-estado" className="flex flex-col gap-3">
        <h2 id="tudo-estado" className="text-2xl">
          Tudo sobre {e.nome}
        </h2>
        <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {tudo.map((t) => (
            <li key={t.href}>
              <Link
                href={t.href}
                className="flex min-h-11 flex-col gap-0.5 rounded-[var(--raio)] border border-border bg-card px-4 py-3 hover:border-foreground/40 focus-visible:outline-2 focus-visible:outline-bronze"
              >
                <span className="font-semibold">{t.rotulo} ›</span>
                <span className="text-sm text-muted-foreground">{t.texto}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
