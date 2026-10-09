import type { Metadata } from "next";
import Link from "next/link";

import { AvisoErro } from "@/components/aviso-erro";
import { PartidoSecao } from "@/components/partido-secao";
import { Revelacao } from "@/components/revelacao";
import { getPartido } from "@/lib/api";

export async function generateMetadata({ params }: PageProps<"/partidos/[sigla]">): Promise<Metadata> {
  const { sigla } = await params;
  const nome = decodeURIComponent(sigla);
  return {
    title: `Dinheiro do ${nome}`,
    description: `Fundo Partidário, fundo eleitoral, receitas, gastos e repasses a candidaturas do ${nome}, segundo a prestação de contas entregue ao TSE.`,
  };
}

const texto = (v: string | string[] | undefined) => (typeof v === "string" && v ? v : undefined);

export default function PartidoPage({ params, searchParams }: PageProps<"/partidos/[sigla]">) {
  return (
    <Revelacao fallback={<p className="text-muted-foreground">Carregando…</p>}>
      {Promise.all([params, searchParams]).then(([{ sigla }, sp]) => (
        <Conteudo sigla={decodeURIComponent(sigla)} ano={texto(sp.ano)} />
      ))}
    </Revelacao>
  );
}

async function Conteudo({ sigla, ano }: { sigla: string; ano?: string }) {
  const resultado = await getPartido(sigla, ano);
  if (!resultado.ok) {
    return (
      <div className="flex flex-col gap-4">
        <AvisoErro titulo="Partido não encontrado" mensagem={resultado.mensagem} />
        <Link href="/partidos" className="text-sm underline underline-offset-4">
          Ver todos os partidos
        </Link>
      </div>
    );
  }
  return <PartidoSecao dados={resultado.dados} />;
}
