import Link from "next/link";
import { notFound } from "next/navigation";

import { AvisoErro } from "@/components/aviso-erro";
import { FotoVereador } from "@/components/camara-secao";
import { CandidaturaSecao } from "@/components/candidatura-secao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { QuemESecao } from "@/components/dados-pessoais";
import { FonteRodape } from "@/components/fonte-rodape";
import { getEleito, getVereador } from "@/lib/api";
import { formatarData } from "@/lib/formato";

/** Perfil de quem está no cargo numa câmara ou assembleia, com os dados da própria casa. */
export async function PerfilMandatoLocal({ id }: { id: string }) {
  const resultado = await getVereador(id);
  if (!resultado.ok) {
    if (resultado.status === 404) notFound();
    return <AvisoErro titulo="Não deu para carregar" mensagem={resultado.mensagem} />;
  }
  const v = resultado.dados;
  const camara = v.casa === "camara";
  const cargo = camara ? "Vereador" : v.uf === "DF" ? "Deputado distrital" : "Deputado estadual";
  const nomeCasa = camara ? "câmara" : "assembleia";
  const rota = `/${camara ? "vereador" : "deputado-estadual"}/${v.id}`;
  const eleicao = v.candidatura_id ? await getEleito(String(v.candidatura_id)) : null;

  return (
    <article className="flex flex-col gap-8">
      <header className="flex items-start gap-4">
        <FotoVereador vereador={v} tamanho={72} />
        <div className="flex min-w-0 flex-col gap-1">
          <h1 className="text-3xl tracking-tight">{v.nome}</h1>
          {v.nome_completo && v.nome_completo !== v.nome && (
            <p className="text-sm text-muted-foreground">{v.nome_completo}</p>
          )}
          <p className="flex flex-wrap gap-1">
            <span className="pilula">{cargo}</span>
            {v.partido && <span className="pilula">{v.partido}</span>}
            <span className="pilula">{v.titular ? "Titular" : "Suplente"}</span>
          </p>
          {(v.inicio || v.fim) && (
            <p className="text-sm text-muted-foreground">
              Mandato {v.inicio ? `de ${formatarData(v.inicio)}` : ""} {v.fim ? `até ${formatarData(v.fim)}` : ""}
            </p>
          )}
        </div>
      </header>

      {eleicao?.ok && (
        <QuemESecao
          pessoais={eleicao.dados.pessoais}
          votos={eleicao.dados.votos != null ? { ano: eleicao.dados.ano_eleicao, total: eleicao.dados.votos } : null}
        />
      )}

      <CompartilharWhatsApp
        caminho={rota}
        texto={`Veja os projetos e as proposições de ${v.nome}, ${cargo.toLowerCase()}, com dados da própria ${nomeCasa}:`}
      />

      <section aria-labelledby="atuacao-titulo" className="revelar flex flex-col gap-4">
        <div>
          <h2 id="atuacao-titulo" className="text-2xl">
            Na {nomeCasa}
          </h2>
          <p className="text-xs text-muted-foreground">Ano atual e anterior, como a {nomeCasa} publica</p>
        </div>
        {v.proposicoes_por_tipo.length === 0 ? (
          <p className="text-muted-foreground">Nenhuma proposição como autor neste período.</p>
        ) : (
          <dl className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
            {v.proposicoes_por_tipo.map((p) => (
              <div key={p.tipo} className="flex items-baseline justify-between gap-4 border-b border-border py-2 text-sm">
                <dt className="text-muted-foreground">{p.tipo}</dt>
                <dd className="tabular-nums">{p.total}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="text-xs text-muted-foreground">
          Requerimentos e indicações são pedidos (de informação, de obra, de serviço); projetos
          podem virar lei. Conta como autor ou coautor.
        </p>
        {v.lista_projetos.length > 0 && (
          <div className="flex flex-col gap-2">
            <h3 className="font-medium">Projetos</h3>
            <ul className="lista-fios flex flex-col">
              {v.lista_projetos.map((p, i) => (
                <li key={i} className="flex flex-col gap-1 py-3">
                  <a href={p.url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
                    {p.tipo} {p.numero ? `nº ${p.numero}` : ""}/{p.ano}
                  </a>
                  <p className="text-sm">{p.ementa}</p>
                  <p className="text-xs text-muted-foreground">
                    {p.data_apresentacao ? formatarData(p.data_apresentacao) : ""}
                    {p.em_tramitacao === true ? " · em tramitação" : p.em_tramitacao === false ? " · tramitação encerrada" : ""}
                    {p.primeiro_autor ? "" : " · coautor"}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        )}
        {(v.email || v.telefone) && (
          <dl className="flex flex-col gap-1 text-sm">
            {v.email && (
              <div className="flex gap-3">
                <dt className="text-muted-foreground">E-mail</dt>
                <dd>
                  <a href={`mailto:${v.email}`} className="underline underline-offset-2">
                    {v.email}
                  </a>
                </dd>
              </div>
            )}
            {v.telefone && (
              <div className="flex gap-3">
                <dt className="text-muted-foreground">Telefone</dt>
                <dd>{v.telefone}</dd>
              </div>
            )}
          </dl>
        )}
        <FonteRodape fonte={v.fonte_nome} url={v.fonte_url} atualizadoEm={v.atualizado_em} />
      </section>

      {eleicao?.ok && (
        <CandidaturaSecao dados={eleicao.dados} />
      )}

      <Link
        href={v.municipio_ibge ? `/representantes?municipio=${v.municipio_ibge}` : `/representantes?uf=${v.uf}`}
        className="self-start text-sm underline underline-offset-4"
      >
        {camara ? "Ver a câmara e os outros representantes da cidade" : "Ver a assembleia e os outros representantes do estado"}
      </Link>
    </article>
  );
}
