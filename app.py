import streamlit as st
import pandas as pd
import numpy as np

st.title("Otimizador de Apostas por Odds e Confiança")

modo = st.selectbox(
    "Modo de estratégia",
    ["Conservador", "Balanceado", "Agressivo"]
)

if modo == "Conservador":
    peso_retorno = 0.40
    peso_risco = 0.60
elif modo == "Balanceado":
    peso_retorno = 0.60
    peso_risco = 0.40
else:
    peso_retorno = 0.80
    peso_risco = 0.20

capital = st.number_input("Capital total disponível (R$)", min_value=1.0, value=30.0, step=1.0)

st.subheader("Informe os resultados")

num_resultados = st.number_input("Quantidade de resultados possíveis", min_value=2, max_value=5, value=3)

resultados = []

for i in range(num_resultados):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        nome = st.text_input(f"Resultado {i+1}", value=f"Resultado {i+1}")

    with col2:
        odd = st.number_input(f"Odd {i+1}", min_value=1.01, value=2.00, step=0.01)

    with col3:
        apostar = st.checkbox(f"Apostar?", value=True, key=f"apostar_{i}")

    with col4:
        confianca = st.number_input(
            f"Confiança {i+1}",
            min_value=0.0,
            max_value=100.0,
            value=50.0,
            step=1.0
        )

    resultados.append({
        "nome": nome,
        "odd": odd,
        "apostar": apostar,
        "confianca": confianca
    })

st.subheader("Parâmetros de otimização")

perda_maxima_percentual = st.slider(
    "Perda máxima aceitável no cenário protegido (%)",
    min_value=0,
    max_value=100,
    value=50
)

passo = st.selectbox("Precisão da simulação", [0.10, 0.50, 1.00], index=1)

def gerar_distribuicoes(total, n, passo):
    valores = np.arange(0, total + passo, passo)

    if n == 1:
        return [[total]]

    distribuicoes = []

    def backtrack(atual, restante, k):
        if k == 1:
            distribuicoes.append(atual + [round(restante, 2)])
            return

        for v in valores:
            if v <= restante:
                backtrack(atual + [round(v, 2)], round(restante - v, 2), k - 1)

    backtrack([], total, n)
    return distribuicoes

selecionados = [r for r in resultados if r["apostar"]]

if st.button("Calcular otimização"):
    if len(selecionados) == 0:
        st.error("Selecione pelo menos um resultado para apostar.")
    else:
        soma_confianca = sum(r["confianca"] for r in resultados)

        if soma_confianca == 0:
            st.error("A soma dos fatores de confiança deve ser maior que zero.")
        else:
            for r in resultados:
                r["probabilidade_subjetiva"] = r["confianca"] / soma_confianca

            distribuicoes = gerar_distribuicoes(capital, len(selecionados), passo)

            linhas = []

            for dist in distribuicoes:
                apostas = dict(zip([r["nome"] for r in selecionados], dist))

                retornos = {}
                lucros = {}

                for r in resultados:
                    valor_apostado = apostas.get(r["nome"], 0)
                    retorno = valor_apostado * r["odd"]
                    lucro = retorno - capital

                    retornos[r["nome"]] = retorno
                    lucros[r["nome"]] = lucro

                retorno_esperado = sum(
                    lucros[r["nome"]] * r["probabilidade_subjetiva"]
                    for r in resultados
                )

                maior_ganho = max(lucros.values())
                maior_perda = min(lucros.values())

                perda_empate_ok = True

                for r in resultados:
                    if "empate" in r["nome"].lower():
                        perda_empate = -lucros[r["nome"]]
                        limite = capital * perda_maxima_percentual / 100
                        if perda_empate > limite:
                            perda_empate_ok = False

                if perda_empate_ok:
                    linha = {
                        "Retorno esperado ponderado": round(retorno_esperado, 2),
                        "Maior ganho": round(maior_ganho, 2),
                        "Maior perda": round(maior_perda, 2),
                    }

                    for nome, valor in apostas.items():
                        linha[f"Aposta em {nome}"] = round(valor, 2)

                    for nome, lucro in lucros.items():
                        linha[f"Lucro se {nome}"] = round(lucro, 2)

                    linhas.append(linha)

            df = pd.DataFrame(linhas)

            if df.empty:
                st.warning("Nenhuma distribuição atende aos critérios definidos.")
            else:
                df["Score estratégico"] = (
    df["Retorno esperado ponderado"] * peso_retorno + df["Maior perda"] * peso_risco
)

df = df.sort_values(
    by=["Score estratégico"],
    ascending=False
)

                st.subheader("Melhores combinações")
                st.dataframe(df.head(20), use_container_width=True)

                st.subheader("Melhor combinação encontrada")
                st.write(df.iloc[0])
