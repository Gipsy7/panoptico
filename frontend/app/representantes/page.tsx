import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { EmendasMunicipioSecao } from "@/components/emendas-municipio";
import { ParlamentarCard } from "@/components/parlamentar-card";
import {
  type EmendasMunicipio,
  type ParlamentarResumo,
  getEmendasMunicipio,
  getRepresentantes,
} from "@/lib/api";
import { formatarCep, formatarReais } from "@/lib/formato";

export const metadata: Metadata = { title: "Seus representantes" };

type Busca = { cep?: string; uf?: string; municipio?: string };

export default function RepresentantesPage({ searchParams }: PageProps<"/representantes">) {
  return (
    <Revelacao fallback={<Carregando />}>
      {searchParams.then((sp) => (
        <Lista
          cep={primeiro(sp.cep)}
          uf={primeiro(sp.uf)}
          municipio={primeiro(sp.municipio)}
        />
      ))}
    </Revelacao>
  );
}

function primeiro(valor: string | string[] | undefined) {
  return Array.isArray(valor) ? valor[0] : valor;
}

async function Lista({ cep, uf, municipio }: Busca) {
  if (!cep && !uf && !municipio) {
    return <AvisoErro titulo="Faltou o CEP" mensagem="Digite um CEP para ver seus representantes." />;
  }

  const resultado = await getRepresentantes({ cep, uf, municipio });
  if (!resultado.ok) {
    const titulo =
      resultado.status === 404
        ? municipio
          ? "Não encontramos essa cidade"
          : "Não encontramos esse CEP"
        : resultado.status === 422
          ? "CEP inválido"
          : "Não deu para buscar agora";
    return <AvisoErro titulo={titulo} mensagem={resultado.mensagem} />;
  }

  const { localizacao, deputados, senadores, atualizado_em } = resultado.dados;
  const emendasResultado = localizacao.codigo_ibge
    ? await getEmendasMunicipio(localizacao.codigo_ibge)
    : null;
  const emendas = emendasResultado?.ok ? emendasResultado.dados : null;
  const lugar = localizacao.municipio
    ? `${localizacao.municipio}/${localizacao.uf}`
    : localizacao.estado;

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">
          {localizacao.cep
            ? `CEP ${formatarCep(localizacao.cep)}`
            : localizacao.municipio
              ? "Busca por cidade"
              : "Busca por estado"}
        </p>
        <h1 className="text-3xl tracking-tight">Você está em {lugar}</h1>
        <p className="text-muted-foreground">
          Quem representa {localizacao.estado} no Congresso Nacional:
        </p>
      </div>

      <CompartilharWhatsApp
        caminho={
          localizacao.codigo_ibge
            ? `/representantes?municipio=${localizacao.codigo_ibge}`
            : `/representantes?uf=${localizacao.uf}`
        }
        texto={`Veja quem representa ${lugar} no Congresso e quanto cada um enviou para a cidade:`}
      />

      <Secao
        titulo="Senadores"
        explicacao="Cada estado elege 3 senadores."
        parlamentares={senadores}
        emendas={emendas}
      />
      <Secao
        titulo="Deputados federais"
        explicacao={`${localizacao.estado} tem ${deputados.length} deputados federais na Câmara.`}
        parlamentares={deputados}
        emendas={emendas}
      />

      {emendas && <EmendasMunicipioSecao dados={emendas} />}

      <Link
        href={`/parlamentares?uf=${localizacao.uf}`}
        className="self-start text-sm font-medium text-primary underline underline-offset-4"
      >
        Comparar os números de todos de {localizacao.estado}
      </Link>

      <FonteRodape fonte="Dados Abertos da Câmara e do Senado" atualizadoEm={atualizado_em} />
    </div>
  );
}

function Secao({
  titulo,
  explicacao,
  parlamentares,
  emendas,
}: {
  titulo: string;
  explicacao: string;
  parlamentares: ParlamentarResumo[];
  emendas: EmendasMunicipio | null;
}) {
  const enviado = new Map(emendas?.parlamentares.map((e) => [e.parlamentar.id, e.total]));
  const destaque = (id: number) => {
    const valor = enviado.get(id);
    return valor && emendas
      ? `Enviou ${formatarReais(valor, true)} para ${emendas.municipio.nome}`
      : undefined;
  };
  return (
    <section className="flex flex-col gap-3" aria-labelledby={`secao-${titulo}`}>
      <div>
        <h2 id={`secao-${titulo}`} className="text-2xl">
          {titulo} <span className="text-muted-foreground">({parlamentares.length})</span>
        </h2>
        <p className="text-sm text-muted-foreground">{explicacao}</p>
      </div>
      {parlamentares.length === 0 ? (
        <p className="text-muted-foreground">Nenhum dado carregado ainda.</p>
      ) : (
        <ul className="grid border-t border-border sm:grid-cols-2 sm:gap-x-10">
          {parlamentares.map((p) => (
            <li key={p.id} className="border-b border-border">
              <ParlamentarCard parlamentar={p} destaque={destaque(p.id)} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Carregando() {
  return (
    <div className="flex flex-col gap-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando representantes…</span>
      <div className="h-8 w-2/3 animate-pulse rounded-[2px] bg-muted" />
      {Array.from({ length: 6 }, (_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-[2px] bg-muted" />
      ))}
    </div>
  );
}
