import pytest

from app.services.extremos import extremo

# Os mesmos casos de frontend/lib/descobertas.test.ts ("extremoDaSerie").
CASOS = [
    ([(2019, 5), (2020, 6), (2021, 7), (2022, 9)], "o maior da série, que começa em 2019"),
    ([(2019, 9), (2020, 7), (2021, 6), (2022, 5)], "o menor da série, que começa em 2019"),
    ([(2017, 10), (2018, 4), (2019, 5), (2020, 6), (2021, 8)], "o maior desde 2017"),
    ([(2017, 2), (2018, 8), (2019, 7), (2020, 9), (2021, 3)], "o menor desde 2017"),
    # Só 2 pontos entre o recorde e o último: pouco para afirmar.
    ([(2016, 1), (2017, 10), (2018, 4), (2019, 5), (2020, 8)], None),
    # Empate com o mais alto não é recorde da série; o anterior que alcança é o próprio empate.
    ([(2019, 9), (2020, 5), (2021, 6), (2022, 9)], None),
    ([(2018, 9), (2019, 5), (2020, 6), (2021, 7), (2022, 9)], "o maior desde 2018"),
    # Poucos pontos.
    ([(2020, 1), (2021, 2), (2022, 3)], None),
    # No meio do caminho: nem maior nem menor de nenhum trecho longo.
    ([(2018, 5), (2019, 9), (2020, 1), (2021, 6), (2022, 5)], None),
]


@pytest.mark.parametrize(("pontos", "esperado"), CASOS)
def test_extremo(pontos, esperado):
    assert extremo(pontos) == esperado


def test_aceita_pontos_fora_de_ordem():
    assert extremo([(2022, 9), (2019, 5), (2021, 7), (2020, 6)]) == (
        "o maior da série, que começa em 2019"
    )
