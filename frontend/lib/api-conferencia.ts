// GERADO por `npm run tipos-api` (lib/conferencia-api.ts). Não edite à mão.
// Cada linha diz: a resposta desta rota (lib/api-schema.ts, do contrato da API) cabe no tipo
// que o site espera (lib/api.ts). Se o `tsc` acusar uma linha, a API e o site divergem.
/* eslint-disable @typescript-eslint/no-unused-vars */
import type { Agenda, AgendaSegundoTurno, AgroMunicipio, Antecessores, AtosPresidenciais, Bancada, BancadasEstado, BuscaProjetos, CadeirasPorPartido, CalendarioVotacoes, Camara, CandidaturaTse, Carreira, CidadesParecidas, Cobertura, Comparacao, ComparacaoLocal, ComparacaoLocalN, ComparacaoN, ComposicaoCongresso, ConfiancaDoPerfil, ContasEstado, ContasMunicipio, ContratosDaPessoa, Correcoes, DestinoEmendas, DinheiroFederalEstado, DinheiroFederalMunicipio, DinheiroFederalPainel, EleicaoDisponivel, EleitoDetalhe, Eleitores, EleitosFuturos, EmendasDeputadoEstadual, EmendasDosMaisVotados, EmendasMunicipio, EmendasRelator, EmpregoMunicipio, Executivo, FichaFornecedor, Fonte, Fornecedores, FornecedoresPncp, Gastos, IdebMunicipio, IndicadoresUfs, InternetMunicipio, LinhaDoTempo, ListaEleitos, ListaParlamentares, MaisVotados, Municipio, ObrasMunicipio, ObrasPorUf, PainelExecutivo, ParlamentarDetalhe, PartidoDetalhe, Partidos, Pauta, PibMunicipio, Presenca, ProjetoFederal, ProjetoLocal, Projetos, RepassesEstaduais, Representantes, RespostaBusca, RespostaCitado, ResultadoEleicao, Sancoes, SaneamentoMunicipio, SaudeMunicipio, SegundoTurno, SegurancaMunicipio, ServicoFederal, Temas, TempoDoLugar, VereadorDetalhe, Vocacoes, VotacaoDetalhe, VotacaoLocal, VotacoesLocais, Votos, VotosComissoes, VotosPorTema } from "@/lib/api";
import type { paths } from "@/lib/api-schema";

type Resposta<R extends keyof paths> = paths[R] extends {
  get: { responses: { 200: { content: { "application/json": infer T } } } };
}
  ? T
  : never;
// Duas folgas, de propósito:
// - Solto: o site pode estreitar um texto ("camara" | "senado") onde a API declara só `str`.
// - Enviado: campo com valor padrão sai sempre na resposta (o Pydantic serializa os padrões),
//   mas o contrato o marca como opcional.
type Solto<T> = T extends string
  ? string
  : T extends (infer U)[]
    ? Solto<U>[]
    : T extends object
      ? { [K in keyof T]: Solto<T[K]> }
      : T;
type Enviado<T> = T extends (infer U)[]
  ? Enviado<U>[]
  : T extends object
    ? { [K in keyof T]-?: Enviado<Exclude<T[K], undefined>> }
    : T;
/** Falha na compilação quando a resposta da rota não cabe no tipo que o site espera. */
type Confere<Esperado, Real extends Solto<Esperado>> = Real;
/** Para rota com mais de um formato de resposta: algum deles cabe no tipo do site. */
type CabeEmUm<Esperado, Real> = [Extract<Real, Solto<Esperado>>] extends [never] ? false : true;
type Ok<T extends true> = T;

type _Representantes_0 = Confere<Representantes, Enviado<Resposta<"/representantes">>>;
type _ParlamentarDetalhe_1 = Confere<ParlamentarDetalhe, Enviado<Resposta<"/parlamentares/{parlamentar_id}">>>;
type _Gastos_2 = Confere<Gastos, Enviado<Resposta<"/parlamentares/{parlamentar_id}/gastos">>>;
type _EleitosFuturos_3 = Confere<EleitosFuturos, Enviado<Resposta<"/estados/{uf}/eleitos-2026">>>;
type _Executivo_4 = Confere<Executivo, Enviado<Resposta<"/executivo">>>;
type _Camara_5 = Confere<Camara, Enviado<Resposta<"/municipios/{ibge}/camara">>>;
type _VotacoesLocais_6 = Confere<VotacoesLocais, Enviado<Resposta<"/vereadores/{mandato_id}/votacoes">>>;
type _Camara_7 = Confere<Camara, Enviado<Resposta<"/estados/{uf}/assembleia">>>;
type _VereadorDetalhe_8 = Confere<VereadorDetalhe, Enviado<Resposta<"/vereadores/{mandato_id}">>>;
type _Fornecedores_9 = Confere<Fornecedores, Enviado<Resposta<"/municipios/{ibge}/fornecedores">>>;
type _ContasMunicipio_10 = Confere<ContasMunicipio, Enviado<Resposta<"/municipios/{ibge}/contas">>>;
type _RepassesEstaduais_11 = Confere<RepassesEstaduais, Enviado<Resposta<"/municipios/{ibge}/repasses-estaduais">>>;
type _ListaEleitos_12 = Confere<ListaEleitos, Enviado<Resposta<"/municipios/{ibge}/vereadores">>>;
type _ListaEleitos_13 = Confere<ListaEleitos, Enviado<Resposta<"/estados/{uf}/deputados-estaduais">>>;
type _EleitoDetalhe_14 = Confere<EleitoDetalhe, Enviado<Resposta<"/eleitos/{candidatura_id}">>>;
type _VotosComissoes_15 = Confere<VotosComissoes, Enviado<Resposta<"/parlamentares/{parlamentar_id}/votos-comissoes">>>;
type _CandidaturaTse_16 = Confere<CandidaturaTse, Enviado<Resposta<"/parlamentares/{parlamentar_id}/candidatura">>>;
type _Projetos_17 = Confere<Projetos, Enviado<Resposta<"/parlamentares/{parlamentar_id}/projetos">>>;
type _DestinoEmendas_18 = Confere<DestinoEmendas, Enviado<Resposta<"/parlamentares/{parlamentar_id}/emendas-destino">>>;
type _EmendasRelator_19 = Confere<EmendasRelator, Enviado<Resposta<"/parlamentares/{parlamentar_id}/emendas-relator">>>;
type _Presenca_20 = Confere<Presenca, Enviado<Resposta<"/parlamentares/{parlamentar_id}/presenca">>>;
type _EmendasDeputadoEstadual_21 = Confere<EmendasDeputadoEstadual, Enviado<Resposta<"/deputados-estaduais/{mandato_id}/emendas">>>;
type _EmendasMunicipio_22 = Confere<EmendasMunicipio, Enviado<Resposta<"/municipios/{ibge}/emendas">>>;
type _Fonte_23 = Confere<Fonte[], Enviado<Resposta<"/fontes">>>;
type _Municipio_24 = Confere<Municipio[], Enviado<Resposta<"/municipios">>>;
type _InternetMunicipio_25 = Confere<InternetMunicipio, Enviado<Resposta<"/municipios/{ibge}/internet">>>;
type _SaneamentoMunicipio_26 = Confere<SaneamentoMunicipio, Enviado<Resposta<"/municipios/{ibge}/saneamento">>>;
type _SegurancaMunicipio_27 = Confere<SegurancaMunicipio, Enviado<Resposta<"/municipios/{ibge}/seguranca">>>;
type _SaudeMunicipio_28 = Confere<SaudeMunicipio, Enviado<Resposta<"/municipios/{ibge}/saude">>>;
type _CadeirasPorPartido_29 = Confere<CadeirasPorPartido, Enviado<Resposta<"/partidos/cadeiras">>>;
type _IndicadoresUfs_30 = Confere<IndicadoresUfs, Enviado<Resposta<"/estados/{uf}/cidades/indicadores">>>;
type _IndicadoresUfs_31 = Confere<IndicadoresUfs, Enviado<Resposta<"/estados/indicadores">>>;
type _TempoDoLugar_32 = Confere<TempoDoLugar, Enviado<Resposta<"/municipios/{ibge}/tempo">>>;
type _TempoDoLugar_33 = Confere<TempoDoLugar, Enviado<Resposta<"/estados/{uf}/tempo">>>;
type _CidadesParecidas_34 = Confere<CidadesParecidas, Enviado<Resposta<"/municipios/{ibge}/parecidas">>>;
type _Vocacoes_35 = Confere<Vocacoes, Enviado<Resposta<"/municipios/{ibge}/vocacoes">>>;
type _EmpregoMunicipio_36 = Confere<EmpregoMunicipio, Enviado<Resposta<"/municipios/{ibge}/emprego">>>;
type _AgroMunicipio_37 = Confere<AgroMunicipio, Enviado<Resposta<"/municipios/{ibge}/agro">>>;
type _PibMunicipio_38 = Confere<PibMunicipio, Enviado<Resposta<"/municipios/{ibge}/pib">>>;
type _IdebMunicipio_39 = Confere<IdebMunicipio, Enviado<Resposta<"/municipios/{ibge}/ideb">>>;
type _ObrasMunicipio_40 = Confere<ObrasMunicipio, Enviado<Resposta<"/municipios/{ibge}/obras">>>;
type _ObrasPorUf_41 = Confere<ObrasPorUf, Enviado<Resposta<"/obras/estados">>>;
type _Municipio_42 = Confere<Municipio[], Enviado<Resposta<"/municipios/busca">>>;
type _ListaParlamentares_43 = Confere<ListaParlamentares, Enviado<Resposta<"/parlamentares">>>;
type _Temas_44 = Confere<Temas, Enviado<Resposta<"/parlamentares/{parlamentar_id}/temas">>>;
type _Votos_45 = Confere<Votos, Enviado<Resposta<"/parlamentares/{parlamentar_id}/votos">>>;
type _Comparacao_46 = Ok<CabeEmUm<Comparacao, Enviado<Resposta<"/comparar">>>>;
type _ComparacaoN_47 = Ok<CabeEmUm<ComparacaoN, Enviado<Resposta<"/comparar">>>>;
type _RespostaBusca_48 = Confere<RespostaBusca, Enviado<Resposta<"/busca">>>;
type _ComparacaoLocal_49 = Ok<CabeEmUm<ComparacaoLocal, Enviado<Resposta<"/comparar/local">>>>;
type _ComparacaoLocalN_50 = Ok<CabeEmUm<ComparacaoLocalN, Enviado<Resposta<"/comparar/local">>>>;
type _LinhaDoTempo_51 = Confere<LinhaDoTempo, Enviado<Resposta<"/pessoas/{pessoa_id}/eventos">>>;
type _ConfiancaDoPerfil_52 = Confere<ConfiancaDoPerfil, Enviado<Resposta<"/pessoas/de/confianca">>>;
type _Partidos_53 = Confere<Partidos, Enviado<Resposta<"/partidos">>>;
type _PartidoDetalhe_54 = Confere<PartidoDetalhe, Enviado<Resposta<"/partidos/{sigla}">>>;
type _ContratosDaPessoa_55 = Confere<ContratosDaPessoa, Enviado<Resposta<"/pessoas/{pessoa_id}/contratos">>>;
type _FornecedoresPncp_56 = Confere<FornecedoresPncp, Enviado<Resposta<"/municipios/{ibge}/fornecedores-pncp">>>;
type _Sancoes_57 = Confere<Sancoes, Enviado<Resposta<"/pessoas/{pessoa_id}/sancoes">>>;
type _ServicoFederal_58 = Confere<ServicoFederal, Enviado<Resposta<"/pessoas/{pessoa_id}/servico-federal">>>;
type _Carreira_59 = Confere<Carreira, Enviado<Resposta<"/pessoas/{pessoa_id}/carreira">>>;
type _VotosPorTema_60 = Confere<VotosPorTema, Enviado<Resposta<"/parlamentares/{parlamentar_id}/votos-por-tema">>>;
type _SegundoTurno_61 = Confere<SegundoTurno, Enviado<Resposta<"/segundo-turno">>>;
type _AgendaSegundoTurno_62 = Confere<AgendaSegundoTurno, Enviado<Resposta<"/segundo-turno/agenda">>>;
type _VotacaoDetalhe_63 = Confere<VotacaoDetalhe, Enviado<Resposta<"/votacoes/{casa}/{id_externo}">>>;
type _PainelExecutivo_64 = Confere<PainelExecutivo, Enviado<Resposta<"/executivo/{candidatura_id}/painel">>>;
type _ContasEstado_65 = Confere<ContasEstado, Enviado<Resposta<"/estados/{uf}/contas">>>;
type _Agenda_66 = Confere<Agenda, Enviado<Resposta<"/executivo/{candidatura_id}/agenda">>>;
type _AtosPresidenciais_67 = Confere<AtosPresidenciais, Enviado<Resposta<"/executivo/{candidatura_id}/atos">>>;
type _Cobertura_68 = Confere<Cobertura, Enviado<Resposta<"/cobertura">>>;
type _DinheiroFederalPainel_69 = Confere<DinheiroFederalPainel, Enviado<Resposta<"/dinheiro-federal">>>;
type _DinheiroFederalEstado_70 = Confere<DinheiroFederalEstado, Enviado<Resposta<"/dinheiro-federal/{uf}">>>;
type _DinheiroFederalMunicipio_71 = Confere<DinheiroFederalMunicipio, Enviado<Resposta<"/municipios/{ibge}/dinheiro-federal">>>;
type _BuscaProjetos_72 = Confere<BuscaProjetos, Enviado<Resposta<"/projetos">>>;
type _ProjetoFederal_73 = Confere<ProjetoFederal, Enviado<Resposta<"/projetos/{casa}/{id_externo}">>>;
type _ProjetoLocal_74 = Confere<ProjetoLocal, Enviado<Resposta<"/projetos/local/{projeto_local_id}">>>;
type _VotacaoLocal_75 = Confere<VotacaoLocal, Enviado<Resposta<"/votacoes/local/{votacao_local_id}">>>;
type _Pauta_76 = Confere<Pauta, Enviado<Resposta<"/pauta">>>;
type _BancadasEstado_77 = Confere<BancadasEstado, Enviado<Resposta<"/estados/{uf}/bancadas">>>;
type _Bancada_78 = Confere<Bancada, Enviado<Resposta<"/municipios/{ibge}/bancada">>>;
type _ComposicaoCongresso_79 = Confere<ComposicaoCongresso, Enviado<Resposta<"/congresso/composicao">>>;
type _RespostaCitado_80 = Confere<RespostaCitado[], Enviado<Resposta<"/pessoas/de/respostas">>>;
type _Correcoes_81 = Confere<Correcoes, Enviado<Resposta<"/correcoes">>>;
type _CalendarioVotacoes_82 = Confere<CalendarioVotacoes, Enviado<Resposta<"/votacoes/calendario">>>;
type _ResultadoEleicao_83 = Confere<ResultadoEleicao, Enviado<Resposta<"/eleicoes/resultado">>>;
type _EleicaoDisponivel_84 = Confere<EleicaoDisponivel[], Enviado<Resposta<"/eleicoes/disponiveis">>>;
type _FichaFornecedor_85 = Confere<FichaFornecedor, Enviado<Resposta<"/fornecedores/{cnpj}">>>;
type _EmendasDosMaisVotados_86 = Confere<EmendasDosMaisVotados, Enviado<Resposta<"/municipios/{ibge}/emendas-dos-mais-votados">>>;
type _MaisVotados_87 = Confere<MaisVotados, Enviado<Resposta<"/municipios/{ibge}/mais-votados">>>;
type _Eleitores_88 = Confere<Eleitores, Enviado<Resposta<"/municipios/{ibge}/eleitores">>>;
type _Antecessores_89 = Confere<Antecessores, Enviado<Resposta<"/eleicoes/antecessores">>>;
