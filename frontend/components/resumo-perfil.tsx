import { formatarNumero } from "@/components/painel/barra-comparacao";
import { CartaoNumero, GradeCartoes } from "@/components/painel/cartao-numero";
import type { Casa, CandidaturaTse, Gastos, Presenca, Projetos, Sancoes, Votos } from "@/lib/api";
import { CASA_CURTA, formatarData, formatarGastos, formatarReaisCompacto } from "@/lib/formato";

/**
 * Cartões do topo do perfil federal. Cada cartão leva à seção com o detalhe (aberta em
 * gaveta por <AbasDetalhe>, pelo id "ver-<destino>"). Cartão cujo dado falta não aparece.
 */
export function ResumoPerfil({
  nome,
  casa,
  gastos,
  presenca,
  projetos,
  votos,
  bens,
  sancoes,
  subsidio,
}: {
  nome: string;
  casa: Casa;
  gastos?: Gastos;
  presenca?: Presenca;
  projetos?: Projetos;
  votos?: Votos;
  bens?: CandidaturaTse["bens"];
  sancoes?: Sancoes;
  subsidio: number;
}) {
  const media = `Média ${casa === "camara" ? "da" : "do"} ${CASA_CURTA[casa]}`;
  const governo = votos?.governo && votos.governo.total > 0 ? votos.governo : null;

  return (
    <GradeCartoes rotulo="Números principais">
      {presenca && presenca.total_votacoes > 0 && (
        <CartaoNumero
          destino="presenca"
          rotulo={`Votou em ${presenca.ano}, nas votações do Plenário`}
          valor={String(presenca.votou)}
          complemento={`de ${presenca.total_votacoes}`}
          largo
          comparacao={
            presenca.percentual !== null && presenca.media_casa_percentual !== null
              ? {
                  pessoa: { rotulo: nome, valor: presenca.percentual },
                  media: { rotulo: media, valor: presenca.media_casa_percentual },
                  formato: "percentual",
                  escala: 100,
                }
              : undefined
          }
        />
      )}
      {gastos && (
        <CartaoNumero
          destino="gastos"
          rotulo={`Verba do gabinete em ${gastos.ano}`}
          valor={gastos.total === 0 ? formatarGastos(0) : formatarReaisCompacto(gastos.total)}
          apoio={`Média ${formatarReaisCompacto(gastos.media_casa)}`}
        />
      )}
      {projetos && (
        <CartaoNumero
          destino="projetos"
          rotulo={`Projetos como autor principal desde ${projetos.desde.slice(0, 4)}`}
          valor={formatarNumero(projetos.primeiro_autor, "inteiro")}
          apoio={`Média ${formatarNumero(projetos.media_casa_primeiro_autor, "decimal")}`}
        />
      )}
      {governo && (
        <CartaoNumero
          destino="votos"
          rotulo="Votou como o Governo orientou"
          valor={`${governo.iguais} de ${governo.total}`}
          apoio={
            votos?.media_governo != null ? `Média ${formatarNumero(votos.media_governo, "percentual")}` : undefined
          }
        />
      )}
      {bens && (
        <CartaoNumero
          destino="candidatura"
          rotulo={`Bens declarados em ${bens.candidatura.ano}`}
          valor={formatarReaisCompacto(bens.total)}
          apoio={
            bens.anterior
              ? `Em ${bens.anterior.candidatura.ano}: ${formatarReaisCompacto(bens.anterior.total)}`
              : "Valor informado ao TSE"
          }
        />
      )}
      {sancoes && (
        <CartaoNumero
          destino="sancoes"
          rotulo="Registros na CGU e no TCU"
          valor={sancoes.itens.length === 0 ? "Nenhum" : String(sancoes.itens.length)}
          apoio={sancoes.atualizado_em ? `Consulta de ${formatarData(sancoes.atualizado_em)}` : undefined}
        />
      )}
      <CartaoNumero
        destino="remuneracao"
        rotulo="Salário bruto mensal"
        valor={formatarReaisCompacto(subsidio)}
        apoio="Igual para todos"
      />
    </GradeCartoes>
  );
}
