import streamlit as st
import pandas as pd
from datetime import datetime

# Define 'hoje' no início, sem o componente de hora, para consistência nos cálculos.
hoje = pd.to_datetime(datetime.now().date())

st.set_page_config(page_title="RELATÓRIO DINÂMICO PCP", layout="wide")
st.title("RELATÓRIO DINÂMICO PCP")

URL_CSV = "https://docs.google.com/spreadsheets/d/14i9CpKM87PRXvLAVo_0VUcjNxfxnCLwhhmg0mh5ywkI/gviz/tq?tqx=out:csv&gid=1319025913"

@st.cache_data(ttl=3600)
def carregar_dados():
    """
    Carrega os dados, converte as colunas de data e calcula os dias.
    A ordenação será aplicada depois dos filtros.
    """
    df = pd.read_csv(URL_CSV)
    # Limpa espaços em branco que possam existir nos nomes das colunas
    df = df.rename(columns=lambda x: x.strip())

    # Converte as colunas de data para datetime. Erros na conversão viram NaT (Not a Time).
    df["DATA ENTREGA PRIMEIRA VALIDACAO"] = pd.to_datetime(df["DATA ENTREGA PRIMEIRA VALIDACAO"], errors="coerce", dayfirst=True)
    df["DATA ALTERACAO STATUS"] = pd.to_datetime(df["DATA ALTERACAO STATUS"], errors="coerce", dayfirst=True)

    # Calcula a diferença em dias usando as colunas datetime.
    df["DIAS EM VC"] = (hoje - df["DATA ENTREGA PRIMEIRA VALIDACAO"]).dt.days.astype("Int64")
    df["DIAS ALTERACAO STATUS"] = (hoje - df["DATA ALTERACAO STATUS"]).dt.days.astype("Int64")

    return df

df = carregar_dados()

# --- Filtros no topo ---
st.markdown("## Filtros")
col1, col2 = st.columns(2)
with col1:
    clientes = st.multiselect("Cliente", sorted(df["CLIENTE"].dropna().unique()), default=None)
    gps = st.multiselect("GP", sorted(df["GP"].dropna().unique()), default=None)
with col2:
    produtos = st.multiselect("Produto", sorted(df["PRODUTO"].dropna().unique()), default=None)

    # Lógica para o filtro de Status
    opcoes_status = sorted(df["STATUS"].dropna().unique())
    status_padrao_desejado = ["VC", "VC R1", "VC R2", "VC ADD"]
    # Filtra os valores padrão para garantir que eles existam nas opções disponíveis
    status_padrao_valido = [s for s in status_padrao_desejado if s in opcoes_status]

    status = st.multiselect("Status", opcoes_status, default=status_padrao_valido)

# Tratamento para evitar erro se a coluna de data estiver vazia ou sem datas válidas
if not df["DATA ENTREGA PRIMEIRA VALIDACAO"].dropna().empty:
    data_min = df["DATA ENTREGA PRIMEIRA VALIDACAO"].min()
    data_max = df["DATA ENTREGA PRIMEIRA VALIDACAO"].max()

    if pd.notna(data_min) and pd.notna(data_max):
        col3, col4 = st.columns(2)
        with col3:
            data_inicial = st.date_input("Data Inicial", value=data_min, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
        with col4:
            data_final = st.date_input("Data Final", value=data_max, min_value=data_min, max_value=data_max, format="DD/MM/YYYY")
    else:
        st.warning("Não foi possível determinar o intervalo de datas para o filtro.")
        data_inicial, data_final = None, None
else:
    st.warning("Nenhuma data de entrega válida encontrada para definir os filtros.")
    data_inicial, data_final = None, None


# --- Aplicar filtros ---
df_filtrado = df.copy()
if clientes:
    df_filtrado = df_filtrado[df_filtrado["CLIENTE"].isin(clientes)]
if gps:
    df_filtrado = df_filtrado[df_filtrado["GP"].isin(gps)]
if produtos:
    df_filtrado = df_filtrado[df_filtrado["PRODUTO"].isin(produtos)]
if status:
    df_filtrado = df_filtrado[df_filtrado["STATUS"].isin(status)]

# Filtro de data, garantindo que as datas não sejam nulas antes de comparar
if data_inicial and data_final:
    df_filtrado = df_filtrado[
        df_filtrado["DATA ENTREGA PRIMEIRA VALIDACAO"].notna() &
        (df_filtrado["DATA ENTREGA PRIMEIRA VALIDACAO"] >= pd.to_datetime(data_inicial)) &
        (df_filtrado["DATA ENTREGA PRIMEIRA VALIDACAO"] <= pd.to_datetime(data_final))
    ]

# --- Funções para indicadores visuais ---
def gerar_bolinha_status(dias):
    if pd.isna(dias):
        return "⚪"
    dias = int(dias)
    if dias < 0: return "📅" # Indica data futura
    if dias <= 7: return "🟢"
    elif dias <= 14: return "🔵"
    elif dias <= 21: return "🟡"
    elif dias <= 30: return "🟠"
    elif dias <= 45: return "🔴"
    else: return "⚫"

def gerar_bolinha_vc(dias):
    if pd.isna(dias):
        return "⚪"
    dias = int(dias)
    if dias < 0: return "📅" # Emoji de calendário para indicar data futura
    if dias <= 21: return "🟢"
    elif dias <= 30: return "🟠"
    else: return "🔴"

# --- Legendas ---
st.markdown("---")
st.markdown("#### Legendas dos Indicadores")
st.markdown(
    """
    **Entrega (ENT):** &nbsp; 🟢 Até 21 dias &nbsp; | &nbsp; 🟠 22 a 30 dias &nbsp; | &nbsp; 🔴 Acima de 30 dias <br>
    **Alteração (ALT):** &nbsp; 🟢 Até 7 &nbsp; | &nbsp; 🔵 8 a 14 &nbsp; | &nbsp; 🟡 15 a 21 &nbsp; | &nbsp; 🟠 22 a 30 &nbsp; | &nbsp; 🔴 31 a 45 &nbsp; | &nbsp; ⚫ Acima de 45 dias <br>
    **Geral:** &nbsp; 📅 Data Futura &nbsp; | &nbsp; ⚪ Dado Ausente
    """,
    unsafe_allow_html=True
)
st.markdown("---")


# --- Geração de colunas visuais e exibição da tabela ---
# Aplica a ordenação correta ao DataFrame filtrado, por data cronológica
df_filtrado = df_filtrado.sort_values(
    by=["DATA ENTREGA PRIMEIRA VALIDACAO", "DATA ALTERACAO STATUS"],
    ascending=[True, True],
    na_position='last'
).reset_index(drop=True)

# Aplica as funções para gerar os indicadores visuais
df_filtrado["STATUS VISUAL"] = df_filtrado["DIAS ALTERACAO STATUS"].apply(gerar_bolinha_status)
df_filtrado["VC VISUAL"] = df_filtrado["DIAS EM VC"].apply(gerar_bolinha_vc)

# Seleciona as colunas para exibição, mantendo as colunas de data originais (datetime)
tabela_para_exibir = df_filtrado[[
    'CLIENTE', 'PROJETO', 'STATUS',
    'DATA ENTREGA PRIMEIRA VALIDACAO',
    'DIAS EM VC', 'VC VISUAL',
    'DATA ALTERACAO STATUS',
    'DIAS ALTERACAO STATUS', 'STATUS VISUAL',
    'OBSERVACOES'
]]

# Renomeia as colunas para o formato final de exibição com os novos títulos
tabela_para_exibir = tabela_para_exibir.rename(columns={
    'VC VISUAL': 'ENT',
    'STATUS VISUAL': 'ALT',
    'DATA ENTREGA PRIMEIRA VALIDACAO': 'PRIM.\nENTREGA',
    'DATA ALTERACAO STATUS': 'ALT.\nSTATUS',
    'DIAS ALTERACAO STATUS': 'DIAS\nALT.'
})

# --- Exibição da Tabela ---
st.markdown("### Tabela Detalhada com Indicadores Visuais")

st.dataframe(
    tabela_para_exibir,
    use_container_width=True,
    hide_index=True,
    height=735, # (20 linhas * 35px por linha) + 35px para o cabeçalho
    column_config={
        "PRIM.\nENTREGA": st.column_config.DatetimeColumn(
            "Prim. Entrega",
            format="DD/MM/YYYY",
        ),
        "ALT.\nSTATUS": st.column_config.DatetimeColumn(
            "Alt. Status",
            format="DD/MM/YYYY",
        )
    }
)
