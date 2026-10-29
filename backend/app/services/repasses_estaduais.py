"""Quanto o governo do estado repassou à prefeitura (SICONFI, Declaração de Contas Anuais).

O valor é o que a própria prefeitura declarou ao Tesouro como receita recebida do estado
(receita bruta realizada, contas 1.7.2 correntes e 2.4.2 de capital do Anexo I-C), para os
5.570 municípios pelo mesmo critério. A carga está em `ingestion/siconfi/contas.py`.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ContasMunicipio, FonteIngestao, Municipio

FONTE_NOME = "Declaração de Contas Anuais (SICONFI, Tesouro Nacional)"
FONTE_URL = "https://siconfi.tesouro.gov.br/"

# (chave, rótulo do dia a dia, termo oficial, explicação, repasse obrigatório por lei)
TIPOS: list[tuple[str, str, str, str, bool]] = [
    (
        "icms",
        "Parte do ICMS",
        "Cota-parte do ICMS",
        "O ICMS é o imposto do estado sobre mercadorias e serviços. A Constituição manda o "
        "estado entregar 25% do que arrecada às cidades; a lei estadual define quanto cabe a "
        "cada uma, em boa parte pelo movimento econômico da cidade.",
        True,
    ),
    (
        "ipva",
        "Parte do IPVA",
        "Cota-parte do IPVA",
        "Metade do IPVA dos veículos registrados na cidade fica com a prefeitura, como manda a "
        "Constituição.",
        True,
    ),
    (
        "ipi",
        "Parte do IPI das exportações",
        "Cota-parte do IPI-Exportação",
        "A União entrega aos estados uma parte do IPI ligada às exportações, e a Constituição "
        "manda o estado repassar 25% disso às cidades.",
        True,
    ),
    (
        "cide",
        "Parte da CIDE dos combustíveis",
        "Cota-parte da CIDE-Combustíveis",
        "Parte do tributo federal sobre combustíveis que chega ao estado; a lei manda repassar "
        "25% às cidades, para transporte e vias.",
        True,
    ),
    (
        "royalties",
        "Royalties repassados pelo estado",
        "Cota-parte das compensações financeiras pela exploração de recursos naturais",
        "Parte do que o estado recebe pela exploração de petróleo, minérios e rios para energia, "
        "que a lei manda dividir com as cidades.",
        True,
    ),
    (
        "sus",
        "Saúde (SUS)",
        "Transferências dos estados ao Sistema Único de Saúde",
        "Dinheiro do estado para o fundo municipal de saúde: atendimento, remédios e programas "
        "do SUS, conforme regras e acordos da saúde entre o estado e as cidades.",
        False,
    ),
    (
        "convenios",
        "Convênios com o estado",
        "Transferências de convênios dos estados (correntes e de capital)",
        "Dinheiro para uma obra ou um programa combinado num acordo (convênio) entre o estado e "
        "a prefeitura.",
        False,
    ),
    (
        "outras",
        "Outros repasses do estado",
        "Outras transferências dos estados (correntes e de capital)",
        "Programas de educação e de assistência social, compensação de perdas do ICMS e demais "
        "repasses do estado que não se encaixam nos tipos acima.",
        False,
    ),
]

MEDIA_UF_DESCRICAO = (
    "Média simples, entre os municípios do estado que enviaram as contas do mesmo ano ao "
    "Tesouro, do valor recebido do estado dividido pela população de cada um. Quem não enviou "
    "as contas fica de fora; um tipo que a prefeitura não recebeu entra como zero."
)
MOTIVO_DF = (
    "Brasília não tem prefeitura separada do governo do Distrito Federal: o DF acumula os papéis "
    "de estado e de município, então não há repasse do estado para a cidade."
)
MOTIVO_SEM_CARGA = "Os repasses do estado às prefeituras ainda não foram carregados."
MOTIVO_NAO_ENVIOU = (
    "A prefeitura não enviou ao Tesouro Nacional as contas dos anos carregados ({anos}), por "
    "isso não sabemos quanto recebeu do estado."
)


def _vazio(municipio: Municipio, motivo: str, atualizado_em: datetime | None) -> dict:
    return {
        "disponivel": False,
        "motivo": motivo,
        "uf": municipio.uf,
        "ano": None,
        "populacao": None,
        "total": None,
        "por_habitante": None,
        "media_uf_por_habitante": None,
        "municipios_na_media": 0,
        "municipios_uf": 0,
        "media_uf_descricao": MEDIA_UF_DESCRICAO,
        "parte_por_lei": None,
        "percentual_por_lei": None,
        "fundeb": None,
        "tipos": [],
        "anterior": None,
        "anos_sem_contas": [],
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }


def _por_hab(valor: float | None, populacao: int | None) -> float | None:
    if valor is None or not populacao:
        return None
    return round(valor / populacao, 2)


def resumo(session: Session, municipio: Municipio) -> dict:
    atualizado_em: datetime | None = session.scalar(
        select(func.max(FonteIngestao.concluido_em)).where(
            FonteIngestao.fonte == "siconfi_contas", FonteIngestao.status == "ok"
        )
    )
    if municipio.uf == "DF":
        return _vazio(municipio, MOTIVO_DF, atualizado_em)

    # Linhas do estado com o recorte carregado (no máximo ~850 por ano, em MG).
    linhas = session.execute(
        select(
            ContasMunicipio.municipio_ibge,
            ContasMunicipio.ano,
            ContasMunicipio.populacao,
            ContasMunicipio.transf_estado,
        )
        .join(Municipio, Municipio.ibge == ContasMunicipio.municipio_ibge)
        .where(Municipio.uf == municipio.uf, ContasMunicipio.transf_estado.is_not(None))
    ).all()
    # JSON nulo (carga anterior ao recorte) passa pelo IS NOT NULL do SQL: filtra aqui.
    linhas = [linha for linha in linhas if linha.transf_estado]
    anos = sorted({linha.ano for linha in linhas}, reverse=True)
    if not anos:
        return _vazio(municipio, MOTIVO_SEM_CARGA, atualizado_em)

    proprias = {linha.ano: linha for linha in linhas if linha.municipio_ibge == municipio.ibge}
    anos_sem_contas = [a for a in anos if a not in proprias]
    if not proprias:
        motivo = MOTIVO_NAO_ENVIOU.format(anos=", ".join(str(a) for a in sorted(anos)))
        vazio = _vazio(municipio, motivo, atualizado_em)
        vazio["anos_sem_contas"] = sorted(anos_sem_contas)
        return vazio

    ano = max(proprias)
    atual = proprias[ano]
    dados: dict = atual.transf_estado
    populacao = atual.populacao
    do_ano = [linha for linha in linhas if linha.ano == ano and linha.populacao]
    municipios_uf = session.scalar(
        select(func.count()).select_from(Municipio).where(Municipio.uf == municipio.uf)
    )

    def media(chave: str) -> float | None:
        if not do_ano:
            return None
        razoes = [float(linha.transf_estado.get(chave) or 0) / linha.populacao for linha in do_ano]
        return round(sum(razoes) / len(razoes), 2)

    total = float(dados["total"])
    tipos = []
    for chave, rotulo, termo, explicacao, por_lei in TIPOS:
        valor = float(dados.get(chave) or 0)
        tipos.append(
            {
                "chave": chave,
                "rotulo": rotulo,
                "termo_oficial": termo,
                "explicacao": explicacao,
                "por_lei": por_lei,
                "valor": valor,
                "percentual": round(100 * valor / total, 1) if total else 0,
                "por_habitante": _por_hab(valor, populacao),
                "media_uf_por_habitante": media(chave),
            }
        )
    parte_por_lei = round(sum(t["valor"] for t in tipos if t["por_lei"]), 2)
    anterior_ano = max((a for a in proprias if a < ano), default=None)
    fundeb = dados.get("fundeb")
    return {
        "disponivel": True,
        "motivo": None,
        "uf": municipio.uf,
        "ano": ano,
        "populacao": populacao,
        "total": total,
        "por_habitante": _por_hab(total, populacao),
        "media_uf_por_habitante": media("total"),
        "municipios_na_media": len(do_ano),
        "municipios_uf": municipios_uf or 0,
        "media_uf_descricao": MEDIA_UF_DESCRICAO,
        "parte_por_lei": parte_por_lei,
        "percentual_por_lei": round(100 * parte_por_lei / total, 1) if total else None,
        "fundeb": float(fundeb) if fundeb is not None else None,
        # Tipos sem valor ficam fora da lista (não há o que mostrar), mas entram na média.
        "tipos": [t for t in tipos if t["valor"]],
        "anterior": {
            "ano": anterior_ano,
            "total": float(proprias[anterior_ano].transf_estado["total"]),
        }
        if anterior_ano
        else None,
        "anos_sem_contas": sorted(anos_sem_contas),
        "fonte_nome": FONTE_NOME,
        "fonte_url": FONTE_URL,
        "atualizado_em": atualizado_em,
    }
