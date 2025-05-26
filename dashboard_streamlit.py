import streamlit as st
import pandas as pd
import unicodedata
from datetime import datetime, timedelta

st.set_page_config(layout="wide")
st.title("📊 Relatório Dinâmico PCP")

sheet_url = "https://docs.google.com/spreadsheets/d/14i9CpKM87PRXvLAVo_0VUcjNxfxnCLwhhmg0mh5ywkI/gviz/tq?tqx=out:csv&gid=1319025913"
df = pd.read_csv(sheet_url)
df.columns = df.columns.str.strip()
df.columns = df.columns.map(lambda x: unicodedata.normalize("NFKD", x).encode("ASCII", "ignore").decode("utf-8"))

df["DATA ENTREGA PRIMEIRA VALIDACAO"] = pd.to_datetime(
    df["DATA ENTREGA PRIMEIRA VALIDACAO"].astype(str)
    .str.strip()
    .str.replace(r"[^\d/]", "", regex=True),
    format="%d/%m/%Y", errors="coerce"
)

df["QTD DE TELAS/MIN"] = pd.to_numeric(df["QTD DE TELAS/MIN"], errors="coerce").fillna(0)

datas_validas = df["DATA ENTREGA PRIMEIRA VALIDACAO"].dropna()
data_min = datas_validas.min()
data_max = datas_validas.max()
hoje = datetime.today()
primeiro_dia_mes_atual = datetime(hoje.year, hoje.month, 1)
primeiro_dia_mes_anterior = (primeiro_dia_mes_atual - timedelta(days=1)).replace(day=1)
data_inicial_padrao = max(data_min, primeiro_dia_mes_anterior)
data_final_padrao = data_max

# Filtros no topo
st.markdown("### Filtros")

col1, col2, col3 = st.columns(3)
with col1:
    data_inicial = st.date_input("Data Inicial", value=data_inicial_padrao, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
with col2:
    data_final = st.date_input("Data Final", value=data_final_padrao, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")

df_temp = df[df["DATA ENTREGA PRIMEIRA VALIDACAO"].between(pd.to_datetime(data_inicial), pd.to_datetime(data_final), inclusive="both")]

col4, col5, col6 = st.columns(3)
with col4:
    fase_options = sorted(list(set(df_temp["FASE"].fillna("Não informado").tolist()) | set(["Produção"])))
    fase = st.multiselect("Fase", options=fase_options, default=["VC"] if "VC" in fase_options else None, key="f2")
with col5:
    gp = st.multiselect("GP", options=sorted(df_temp["GP"].fillna("Não informado").unique().tolist()), key="g2")
with col6:
    cliente = st.multiselect("Cliente", options=sorted(df_temp["CLIENTE"].fillna("Não informado").unique().tolist()), key="c2")

df_temp = df_temp[df_temp["FASE"].fillna("Não informado").isin(fase)] if fase else df_temp
df_temp = df_temp[df_temp["GP"].fillna("Não informado").isin(gp)] if gp else df_temp
df_temp = df_temp[df_temp["CLIENTE"].fillna("Não informado").isin(cliente)] if cliente else df_temp

df_filtrado = df_temp.copy()
df_filtrado["DIAS EM VC"] = (datetime.today() - df_filtrado["DATA ENTREGA PRIMEIRA VALIDACAO"]).dt.days

if not df_filtrado.empty:
    st.markdown("""
    <style>
    .legenda-box {
        display: flex;
        gap: 2rem;
        margin-bottom: 1rem;
        font-size: 0.9rem;
    }
    .legenda-item {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    .legenda-cor {
        width: 20px;
        height: 20px;
        border-radius: 3px;
        display: inline-block;
    }
    </style>
    <div class="legenda-box">
        <div class="legenda-item"><span class="legenda-cor" style="background-color:#d4edda"></span>Até 10 dias</div>
        <div class="legenda-item"><span class="legenda-cor" style="background-color:#fff3cd"></span>De 11 a 30 dias</div>
        <div class="legenda-item"><span class="legenda-cor" style="background-color:#f8d7da"></span>Acima de 30 dias</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Tabela Detalhada")
    tabela = df_filtrado[[
        "CLIENTE", "PROJETO", "FASE", "DIAS EM VC", "DATA ENTREGA PRIMEIRA VALIDACAO"
    ]].rename(columns={
        "FASE": "STATUS",
        "DATA ENTREGA PRIMEIRA VALIDACAO": "DATA PRIMEIRA ENTREGA"
    }).reset_index(drop=True)

    tabela["DATA PRIMEIRA ENTREGA"] = tabela["DATA PRIMEIRA ENTREGA"].apply(lambda x: x.strftime("%d/%m/%Y") if pd.notnull(x) else "")

    def formatar_dias(val):
        if val <= 10:
            cor = "#d4edda"
        elif val <= 30:
            cor = "#fff3cd"
        else:
            cor = "#f8d7da"
        return f'background-color: {cor}; text-align: center'

    def centralizar(val):
        return "text-align: center;"

    st.dataframe(tabela.style
                 .applymap(formatar_dias, subset=["DIAS EM VC"])
                 .applymap(centralizar, subset=["DIAS EM VC"]))
else:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")
