"""TAREFA DO ALUNO -- os cinco testes que faltam para os >= 8 do entregavel.

Cada teste abaixo tem nome, docstring e um pytest.skip. Apague o skip, escreva o
corpo, e o teste passa a valer. Nenhum deles precisa de banco: os tres primeiros
rodam so contra o motor.
"""

from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal, localcontext

from app.dominio.motor_emergia import SEIS_CASAS, _soma, calcular_indices
from app.dominio.tipos import CategoriaFluxo, FluxoEmergetico


def test_regressao_numerica_contra_a_planilha(fluxos_golden):
    """Compara os seis indices com a aba SSB da Planilha_base.xlsx.

    Criterio do entregavel: abs(delta) <= 1E-6 por indice. Comece pelo inventario
    de referencia (Y = 200, F = 50, renovaveis = 115, nao renovaveis = 85) e
    escreva os seis valores esperados a mao antes de rodar -- se o teste passar
    de primeira sem voce saber o valor esperado, ele nao esta provando nada.

    A mao: EYR = Y/F = 200/50 = 4. ELR = nao_renovaveis/renovaveis = 85/115 =
    17/23 = 0,739130(4347...) -> 0,739130 em seis casas (setimo digito e 4,
    arredonda para baixo). ESI = EYR/ELR = 4*115/85 = 92/17 = 5,4117647(058...)
    -> 5,411765 (setimo digito 7, arredonda para cima). EII = ELR/EYR =
    17/92 = 0,1847826(08...) -> 0,184783 (setimo digito 6, arredonda para
    cima). percentual_r = 115/200*100 = 57,5, exato.
    """
    resultado = calcular_indices(fluxos_golden, Decimal("1000"))

    esperado = {
        "y": Decimal("200.000000"),
        "eyr": Decimal("4.000000"),
        "elr": Decimal("0.739130"),
        "esi": Decimal("5.411765"),
        "eii": Decimal("0.184783"),
        "percentual_r": Decimal("57.500000"),
    }
    tolerancia = Decimal("1E-6")
    for campo, valor_esperado in esperado.items():
        obtido = getattr(resultado, campo)
        delta = abs(obtido - valor_esperado)
        assert delta <= tolerancia, (
            f"{campo}: esperado {valor_esperado}, obtido {obtido}, delta {delta}"
        )


def test_quantizacao_unica_no_final():
    """Mostra o erro duplo de arredondar no meio do calculo.

    Calcule ESI = EYR / ELR de duas formas: (a) quantizando EYR e ELR para seis
    casas antes de dividir; (b) dividindo em 28 digitos e quantizando so o ESI.
    Os dois resultados diferem -- e o motor usa (b). Prove a diferenca.
    """
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN

        eyr_cheio = Decimal(200) / Decimal(50)    # = 4, exato
        elr_cheio = Decimal(85) / Decimal(115)    # diziima periodica

        # (a) arredonda EYR e ELR antes de dividir -- erro duplo
        esi_arredonda_antes = (
            eyr_cheio.quantize(SEIS_CASAS) / elr_cheio.quantize(SEIS_CASAS)
        ).quantize(SEIS_CASAS)

        # (b) divide com os 28 digitos cheios e quantiza so o resultado final
        # -- e o que calcular_indices faz
        esi_quantiza_so_no_final = (eyr_cheio / elr_cheio).quantize(SEIS_CASAS)

    assert esi_arredonda_antes == Decimal("5.411768")
    assert esi_quantiza_so_no_final == Decimal("5.411765")
    assert esi_arredonda_antes != esi_quantiza_so_no_final, (
        "arredondar EYR e ELR antes de dividir acumula dois erros de "
        "arredondamento; o motor arredonda uma unica vez, no ESI pronto"
    )


def test_ordem_da_soma_com_magnitudes_divergentes():
    """A associatividade quebra quando as magnitudes divergem.

    Monte um inventario com um fluxo de 1E20 sej e outro de 1E-5 sej e some nas
    duas ordens possiveis. Explique, no corpo do teste, por que a precisao de 28
    digitos e o limite -- e por que ordenar o inventario e uma decisao de dominio.

    Com prec=28, o fluxo gigante (1E20, 21 digitos inteiros) deixa so 7 casas
    decimais de "espaco" para qualquer soma. Um fluxo de 6E-5 somado direto a
    1E20 fica abaixo da ultima casa representavel e arredonda para cima a cada
    soma isolada; somando os pequenos entre si primeiro, o arredondamento
    acontece uma unica vez, no final. Resultado: a soma total depende da ordem
    em que os fluxos chegam -- por isso o motor nao pode tratar a ordem do
    inventario como irrelevante, e por isso test_determinismo.py so prova
    invariancia de ordem para o inventario didatico, de magnitudes proximas.
    """
    grande = FluxoEmergetico("chuva", CategoriaFluxo.R, Decimal("1E20"))
    pequenos = [
        FluxoEmergetico(f"poeira_{i}", CategoriaFluxo.R, Decimal("6E-8"))
        for i in range(5)
    ]

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN

        # grande primeiro: cada parcela pequena e arredondada isoladamente
        soma_grande_primeiro = _soma([grande, *pequenos], {CategoriaFluxo.R})
        # pequenos primeiro: eles se somam exatos entre si, so depois encontram o grande
        soma_pequenos_primeiro = _soma([*pequenos, grande], {CategoriaFluxo.R})

    assert soma_grande_primeiro != soma_pequenos_primeiro, (
        "mesmos seis fluxos, ordens diferentes, somas diferentes: a precisao "
        "de 28 digitos do contexto e o limite, e ordenar o inventario antes de "
        "somar e uma decisao de dominio, nao um detalhe de implementacao"
    )


def test_erro_de_dominio_responde_problem_json(cliente, corpo_golden):
    """Inventario sem fluxo renovavel deve sair 422 em application/problem+json.

    Hoje sai 500, porque o handler de FluxosInsuficientes nao existe -- note que
    o 404 e o 422 do framework JA saem no formato certo, pelos handlers do
    esqueleto: o que falta e so o erro de dominio. Feche o TODO PASSO 3 em
    app/main.py e depois assegure aqui: status 422, header content-type
    application/problem+json e os cinco campos da RFC 9457.
    """
    # inventario so com N e MN: nenhum fluxo renovavel -> FluxosInsuficientes
    corpo_golden["fluxos"] = [
        f for f in corpo_golden["fluxos"] if f["categoria"] in ("N", "MN")
    ]

    r = cliente.post("/v1/safras/42/calculos", json=corpo_golden)

    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    corpo = r.json()
    for campo in ("type", "title", "status", "detail", "instance"):
        assert campo in corpo
    assert corpo["status"] == 422


def test_campo_extra_no_corpo_da_requisicao_e_rejeitado(cliente, corpo_golden):
    """"energia_produto_jj" tem de morrer com 422, nao virar calculo incompleto.

    Hoje o CalculoRequestDTO nao declara extra="forbid": o campo desconhecido e
    ignorado e o typo passa silencioso, exatamente como na planilha. Feche o
    TODO PASSO 3 em app/api/v1/dto.py e prove aqui.
    """
    corpo_golden["energia_produto_jj"] = "1000"   # typo: ninguem declarou este campo

    r = cliente.post("/v1/safras/42/calculos", json=corpo_golden)

    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/problem+json")
    campos = [erro["campo"] for erro in r.json()["erros"]]
    assert any("energia_produto_jj" in campo for campo in campos)
