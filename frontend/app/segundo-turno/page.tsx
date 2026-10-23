import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { EsqueletoSecao } from "@/components/esqueleto-secao";
import { FonteRodape } from "@/components/fonte-rodape";
import { ListaPerguntas, Pergunta } from "@/components/painel/pergunta";
import { Revelacao } from "@/components/revelacao";
import { TEXTO_REGISTRO } from "@/components/sancoes-secao";
import {
  DetalheCandidato,
  DisputaLadoALado,
  dataPorExtenso,
  deEstado,
  emEstado,
  tituloDisputa,
} from "@/components/segundo-turno";
import { CabecalhoPagina } from "@/components/ui/cabecalho-pagina";
import { Migalhas } from "@/components/ui/migalhas";
import { type SegundoTurno, getAgendaSegundoTurno, getSegundoTurno } from "@/lib/api";
import { formatarCep, formatarData } from "@/lib/formato";
import { UFS } from "@/lib/ufs";

type Busca = { cep?: string; uf?: string; municipio?: string };

function primeiro(valor: string | string[] | undefined) {
  return Array.isArray(valor) ? valor[0] : valor;
}

function lerBusca(sp: Record<string, string | string[] | undefined>): Busca {
  return { cep: primeiro(sp.cep), uf: primeiro(sp.uf), municipio: primeiro(sp.municipio) };
}

export async function generateMetadata({ searchParams }: PageProps<"/segundo-turno">): Promise<Metadata> {
  const busca = lerBusca(await searchParams);
  const base = {
    title: "Compare os candidatos do 2º turno",
    description: "Digite o CEP e veja, lado a lado, os candidatos do 2º turno, com dados oficiais do TSE.",
  };
  if (!busca.cep && !busca.uf && !busca.municipio) return base;
  const r = await getSegundoTurno(busca);
  if (!r.ok) return base;
  const { uf, estado } = r.dados.localizacao;
  const titulo = `2º turno em ${estado}`;
  const nomes = r.dados.disputas.flatMap((d) => d.candidatos.map((c) => c.nome_urna));
  return {
    title: titulo,
    description: nomes.length
      ? `${nomes.join(", ")}: bens, campanha, eleições anteriores e registros na CGU e no TCU, lado a lado, com dados oficiais.`
      : base.description,
    openGraph: { title: titulo, images: [{ url: `/segundo-turno/imagem?uf=${uf}`, width: 1200, height: 630 }] },
  };
}

export default function SegundoTurnoPage({ searchParams }: PageProps<"/segundo-turno">) {
  return (
    <Revelacao fallback={<EsqueletoSecao rotulo="Carregando o 2º turno…" secoes={3} />}>
      {searchParams.then((sp) => (
        <Conteudo {...lerBusca(sp)} />
      ))}
    </Revelacao>
  );
}

function Busca({ rotulo = "Ver os candidatos" }: { rotulo?: string }) {
  return (
    <div className="flex max-w-md flex-col gap-6">
      <form action="/segundo-turno" className="flex flex-col gap-3">
        <label htmlFor="cep-2t" className="text-base font-medium">
          Seu CEP
        </label>
        <input
          id="cep-2t"
          name="cep"
          inputMode="numeric"
          autoComplete="postal-code"
          placeholder="00000-000"
          pattern="[0-9]{5}-?[0-9]{3}"
          required
          className="seletor h-12 w-full text-base"
        />
        <button type="submit" className="botao w-full">
          {rotulo}
        </button>
      </form>
      <form action="/segundo-turno" className="flex flex-col gap-3">
        <label htmlFor="uf-2t" className="text-base font-medium">
          Ou escolha o estado
        </label>
        <select id="uf-2t" name="uf" required defaultValue="" className="seletor h-12 w-full text-base">
          <option value="" disabled>
            Selecione
          </option>
          {UFS.map((u) => (
            <option key={u.sigla} value={u.sigla}>
              {u.nome}
            </option>
          ))}
        </select>
        <button type="submit" className="botao-linha w-full">
          Ver pelo estado
        </button>
      </form>
    </div>
  );
}

async function Conteudo(busca: Busca) {
  if (!busca.cep && !busca.uf && !busca.municipio) return <Inicio />;
  const r = await getSegundoTurno(busca);
  if (!r.ok) {
    const titulo =
      r.status === 404 ? "Não encontramos esse CEP" : r.status === 422 ? "CEP inválido" : "Não deu para buscar agora";
    return (
      <div className="pagina-secoes">
        <AvisoErro titulo={titulo} mensagem={r.mensagem} />
        <Busca />
      </div>
    );
  }
  return <Resultado dados={r.dados} />;
}

async function Inicio() {
  const agenda = await getAgendaSegundoTurno();
  const a = agenda.ok ? agenda.dados : null;
  const nomes = a?.ufs_governador.map((s) => UFS.find((u) => u.sigla === s)?.nome ?? s) ?? [];
  return (
    <div className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <Migalhas itens={[{ rotulo: "Início", href: "/" }, { rotulo: "2º turno" }]} />
        <CabecalhoPagina
          sobretitulo={a?.data_segundo_turno ? `2º turno · ${formatarData(a.data_segundo_turno)}` : "2º turno"}
          titulo="Compare os candidatos do 2º turno"
          subtitulo="Digite o CEP e veja, lado a lado, quem estará na sua urna, com os mesmos dados oficiais para cada candidato."
        />
        {a?.em_andamento && (
          <p className="text-sm text-muted-foreground">
            {a.presidente ? "Há 2º turno para presidente" : "Não há 2º turno para presidente na base"}
            {nomes.length > 0 ? ` e para governador em ${lista(nomes)}.` : "."}
          </p>
        )}
      </div>
      <Busca />
    </div>
  );
}

function cap(t: string) {
  return t.charAt(0).toUpperCase() + t.slice(1);
}

function lista(itens: string[]) {
  return itens.length > 1 ? `${itens.slice(0, -1).join(", ")} e ${itens.at(-1)}` : (itens[0] ?? "");
}

function Resultado({ dados }: { dados: SegundoTurno }) {
  const { localizacao: loc, disputas } = dados;
  const lugar = loc.municipio ? `${loc.municipio}/${loc.uf}` : loc.estado;
  const quando = dados.data_segundo_turno ? dataPorExtenso(dados.data_segundo_turno) : null;
  const cargos = disputas.map((d) => (d.chave === "presidente" ? "presidente" : `governador ${deEstado(d.unidade)}`));
  const ufGov = disputas.find((d) => d.chave === "governador");
  const decidido = disputas.length > 0 && disputas.every((d) => d.decidida);

  return (
    <article data-largura="larga" className="pagina-secoes">
      <div className="flex flex-col gap-4">
        <Migalhas itens={[{ rotulo: "Início", href: "/" }, { rotulo: "2º turno" }]} />
        <CabecalhoPagina
          sobretitulo={loc.cep ? `CEP ${formatarCep(loc.cep)}` : "Busca por estado"}
          titulo={decidido ? `Resultado do 2º turno em ${lugar}` : `O 2º turno em ${lugar}`}
          subtitulo={
            disputas.length === 0
              ? undefined
              : decidido
                ? `Resultado publicado pelo TSE para ${lista(cargos)}. Os mesmos dados para cada candidato, na ordem do número na urna.`
                : `${quando ? `No ${quando}, ` : ""}você vota para ${lista(cargos)}. Os mesmos dados para cada candidato, na ordem do número na urna.`
          }
        />
        {disputas.length === 0 && (
          <p className="painel">
            {dados.em_andamento
              ? `A base do Panóptico ainda não tem candidatos do 2º turno que valham para quem vota ${emEstado(loc.estado)}.`
              : "Não há 2º turno a disputar agora."}
          </p>
        )}
        {!ufGov && dados.governador_eleito_1turno && (
          <p className="text-sm text-muted-foreground">
            {cap(emEstado(loc.estado))} não há 2º turno para governador: {dados.governador_eleito_1turno.nome_urna}
            {dados.governador_eleito_1turno.partido ? ` (${dados.governador_eleito_1turno.partido})` : ""} foi eleito(a)
            no 1º turno.{" "}
            <Link href={dados.governador_eleito_1turno.perfil ?? `/eleito/${dados.governador_eleito_1turno.id}`} className="underline underline-offset-2">
              Ver perfil
            </Link>
          </p>
        )}
        {!ufGov && !dados.governador_eleito_1turno && disputas.length > 0 && (
          <p className="text-sm text-muted-foreground">
            A base não tem 2º turno para governador {emEstado(loc.estado)}.
          </p>
        )}
        {disputas.length > 0 && (
          <CompartilharWhatsApp
            caminho={`/segundo-turno?uf=${loc.uf}`}
            texto={`Compare os candidatos do 2º turno ${emEstado(loc.estado)}, com dados oficiais do TSE:`}
          />
        )}
      </div>

      {disputas.map((d) => (
        <DisputaLadoALado key={d.chave} d={d} dados={dados} />
      ))}

      {disputas.length > 0 && (
        <p className="text-sm">
          As propostas de governo de cada candidato estão no{" "}
          <a href={dados.propostas_url} target="_blank" rel="noopener noreferrer" className="font-medium underline underline-offset-2">
            DivulgaCandContas, do TSE
          </a>{" "}
          (procure pelo nome do candidato).
        </p>
      )}

      {disputas.length > 0 && (
      <ListaPerguntas titulo="Para entender os números">
        <Pergunta
          id="entender-ordem"
          pergunta="Por que os candidatos aparecem nessa ordem?"
          resposta="Pelo número na urna, do menor para o maior"
        >
          <p>
            A ordem não tem relação com votos, pesquisas ou qualquer avaliação. Os dois lados mostram exatamente os
            mesmos campos, com o mesmo destaque.
          </p>
        </Pergunta>
        <Pergunta
          id="entender-bens"
          pergunta="O que são bens declarados?"
          resposta="O patrimônio que o candidato informou ao TSE"
        >
          <p>
            Ao pedir o registro, cada candidato entrega uma lista de bens (imóveis, veículos, aplicações, participação em
            empresas) com o valor que ele mesmo informa. O TSE publica a lista como recebeu, sem conferir os valores. Um
            imóvel costuma ser declarado pelo valor de compra, não pelo de mercado.
          </p>
          <p>
            Quando a mesma pessoa foi candidata antes, aparece também o total declarado na eleição anterior que está na
            base.
          </p>
        </Pergunta>
        <Pergunta
          id="entender-dinheiro"
          pergunta="De onde vem o dinheiro da campanha?"
          resposta="Partido, fundos públicos, pessoas e o próprio candidato"
        >
          <p>
            A campanha recebe dinheiro do partido (que inclui o Fundo Especial de Financiamento de Campanha, público), de
            pessoas físicas e do próprio candidato. Empresas não podem doar desde 2015. O valor mostrado é o que a
            prestação de contas do 1º turno registra; a do 2º turno é entregue depois da votação.
          </p>
          <p>Pela lei de proteção de dados, o Panóptico não mostra o nome de quem doou como pessoa física.</p>
        </Pergunta>
        <Pergunta
          id="entender-falta"
          pergunta="Por que um candidato não tem algum dado?"
          resposta="A fonte ainda não publicou ou a base ainda não carregou"
        >
          <p>
            “Não informado pela fonte” quer dizer que o arquivo do TSE carregado no Panóptico não traz aquele dado para
            o candidato (por exemplo, a prestação de contas ainda não entregue). “Não identificado na base” quer dizer que
            a candidatura ainda não foi ligada com segurança ao histórico da pessoa; sem essa ligação, não dá para
            dizer quais eleições disputou nem se há registros na CGU e no TCU.
          </p>
          <p>
            Antes do resultado, os votos mostrados são os votos válidos que o candidato recebeu no 1º turno; depois, os
            do 2º turno. O percentual não aparece porque a base não tem o total de votos válidos de cada disputa, e
            o Panóptico não estima esse número.
          </p>
        </Pergunta>
        <Pergunta
          id="entender-registro"
          pergunta="O que são os registros na CGU e no TCU?"
          resposta="Sanções e contas julgadas irregulares, como a fonte informa"
        >
          <p>
            A Controladoria-Geral da União mantém cadastros de pessoas punidas (por exemplo, impedidas de contratar com
            o governo ou demitidas do serviço público), e o Tribunal de Contas da União publica quem teve as contas
            julgadas irregulares. {TEXTO_REGISTRO}
          </p>
        </Pergunta>
      </ListaPerguntas>
      )}

      {disputas.some((d) => d.candidatos.length > 0) && (
        <section aria-labelledby="detalhe-titulo" className="flex flex-col gap-4">
          <h2 id="detalhe-titulo" className="text-2xl">
            Em detalhe
          </h2>
          {disputas.map((d) => (
            <div key={d.chave} className="flex flex-col gap-2">
              <h3 className="sobretitulo">{tituloDisputa(d)}</h3>
              {d.candidatos.map((c) => (
                <DetalheCandidato key={c.id} c={c} dados={dados} cargo={d.cargo} />
              ))}
            </div>
          ))}
          <FonteRodape fonte="TSE: prestação de contas eleitorais" url={dados.contas_url} atualizadoEm={dados.atualizado_em} />
        </section>
      )}

      <section aria-labelledby="outro-titulo" className="flex flex-col gap-3">
        <h2 id="outro-titulo" className="text-2xl">
          Ver outro lugar
        </h2>
        <Busca rotulo="Ver o 2º turno deste CEP" />
      </section>
    </article>
  );
}
