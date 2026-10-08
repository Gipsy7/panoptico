import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { Revelacao } from "@/components/revelacao";
import { CompartilharWhatsApp } from "@/components/compartilhar";
import { FonteRodape } from "@/components/fonte-rodape";
import { EmendasMunicipioSecao } from "@/components/emendas-municipio";
import { CamaraSecao } from "@/components/camara-secao";
import { CanaisSecao } from "@/components/canais-secao";
import { ContasSecao } from "@/components/contas-secao";
import { FornecedoresSecao } from "@/components/fornecedores-secao";
import { EleitosSecao } from "@/components/eleitos-secao";
import { ExecutivoSecao } from "@/components/executivo-secao";
import { ParlamentarCard } from "@/components/parlamentar-card";
import {
  type EmendasMunicipio,
  type ParlamentarResumo,
  getDeputadosEstaduais,
  getAssembleia,
  getCamara,
  getCanais,
  getContas,
  getFornecedores,
  getExecutivo,
  getEmendasMunicipio,
  getVereadores,
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
  const [emendasResultado, vereadoresResultado, estaduaisResultado, executivoResultado, canaisResultado, contasResultado, camaraResultado, fornecedoresResultado, assembleiaResultado] = await Promise.all([
    localizacao.codigo_ibge ? getEmendasMunicipio(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getVereadores(localizacao.codigo_ibge) : null,
    getDeputadosEstaduais(localizacao.uf),
    getExecutivo(localizacao.uf, localizacao.codigo_ibge),
    localizacao.codigo_ibge ? getCanais(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getContas(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getCamara(localizacao.codigo_ibge) : null,
    localizacao.codigo_ibge ? getFornecedores(localizacao.codigo_ibge) : null,
    getAssembleia(localizacao.uf),
  ]);
  const assembleia = assembleiaResultado.ok ? assembleiaResultado.dados : null;
  const fornecedores = fornecedoresResultado?.ok ? fornecedoresResultado.dados : null;
  const camara = camaraResultado?.ok ? camaraResultado.dados : null;
  const contas = contasResultado?.ok ? contasResultado.dados : null;
  const canais = canaisResultado?.ok ? canaisResultado.dados.itens : [];
  const executivo = executivoResultado.ok ? executivoResultado.dados : null;
  const vereadores = vereadoresResultado?.ok ? vereadoresResultado.dados : null;
  const estaduais = estaduaisResultado.ok ? estaduaisResultado.dados : null;
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
          Quem governa e quem representa {lugar}, do Executivo à câmara municipal:
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

      {executivo && (
        <ExecutivoSecao dados={executivo} estado={localizacao.estado} cidade={localizacao.municipio} />
      )}

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

      {contas && localizacao.municipio && <ContasSecao dados={contas} cidade={localizacao.municipio} />}

      {fornecedores && localizacao.municipio && (
        <FornecedoresSecao dados={fornecedores} cidade={localizacao.municipio} />
      )}

      {emendas && <EmendasMunicipioSecao dados={emendas} />}

      {camara && localizacao.municipio && <CamaraSecao dados={camara} nome={`Câmara de ${localizacao.municipio}`} />}

      {vereadores && vereadores.itens.length > 0 && (
        <EleitosSecao
          recolhido={Boolean(camara)}
          id="vereadores-titulo"
          titulo={`Vereadores de ${localizacao.municipio}`}
          explicacao={`Eleitos em ${vereadores.ano_eleicao} para a câmara municipal, segundo o TSE. Um suplente pode ter assumido alguma vaga depois.`}
          dados={vereadores}
        />
      )}

      {localizacao.municipio && <CanaisSecao canais={canais} cidade={localizacao.municipio} />}

      {assembleia && (
        <CamaraSecao dados={assembleia} casa="assembleia" nome={`Assembleia de ${localizacao.estado}`} />
      )}

      {estaduais && estaduais.itens.length > 0 && (
        <EleitosSecao
          recolhido={Boolean(assembleia)}
          id="estaduais-titulo"
          titulo={localizacao.uf === "DF" ? "Deputados distritais" : `Deputados estaduais de ${localizacao.estado}`}
          explicacao={`Eleitos em ${estaduais.ano_eleicao} para a ${localizacao.uf === "DF" ? "Câmara Legislativa" : "Assembleia Legislativa"}, segundo o TSE. Quem hoje está em outro cargo aparece indicado.`}
          dados={estaduais}
        />
      )}

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
