import streamlit as st
import pandas as pd
import locale
import limpeza
import plotly.express as px
import plotly.graph_objects as go
from datetime import timedelta
from graficos import aplicar_estilo_kpi, exibir_kpis

# Função para download do DataFrame
def download_button(df, filename="dados.csv"):
    # Convertendo o DataFrame para CSV
    csv = df.to_csv(index=False)
    # Convertendo o CSV para o formato adequado para download
    csv_bytes = csv.encode()

    # Botão de download
    st.download_button(
        label="Baixar dados",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv"
    )

# Configurações iniciais
st.set_page_config(layout="wide")
st.title('Analisar Geração de Leads')

# Localidade para moeda
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')

# Função de cache para o carregamento de arquivos

def carregar_arquivos(arquivos):
    df, df_gasto = None, None
    for arquivo in arquivos:
        nome_arquivo = arquivo.name.lower()
        if "hubspot" in nome_arquivo:
            df = pd.read_csv(arquivo)
            df = limpeza.tratar_arquivo_hubspot(df)
        elif "gasto" in nome_arquivo:
            df_gasto = pd.read_csv(arquivo)
            df_gasto = limpeza.tratar_arquivo_pagos(df_gasto)
    return df, df_gasto


# Uploads
st.sidebar.header("Upload dos Arquivos")
arquivos = st.sidebar.file_uploader("Envie os arquivos CSV", type="csv", accept_multiple_files=True)
considerar_dias_uteis = st.sidebar.checkbox("Considerar apenas dias úteis", value=False)

df, df_gasto = None, None

if arquivos:
    df, df_gasto = carregar_arquivos(arquivos)

if df is not None and df_gasto is not None:
    df_filtrado = df.copy()
    st.sidebar.title("Filtros")

    def multiselect_com_default(label, opcoes):
        with st.sidebar.expander(label):
            selecionadas = st.multiselect(label, opcoes)
            return selecionadas if selecionadas else list(opcoes)

    filtros = {
        'equipe': multiselect_com_default("Equipe", df['equipe'].unique()),
        'produto': multiselect_com_default("Produto", df['produto'].unique()),
        'convenio_acronimo': multiselect_com_default("Convênio", df['convenio_acronimo'].unique()),
        'origem': multiselect_com_default("Canal", df['origem'].unique())
    }

    # Filtro de Etapa com base nas datas
    st.sidebar.subheader("Escolha a etapa para análise")
    etapa_filtro = st.sidebar.selectbox(
        "Selecione a etapa que deseja analisar:",
        options=["Lead", "Negociação", "Contratação", "Pago", "Perda"],
        format_func=lambda x: x
    )

    with st.sidebar.expander('Filtro Data'):
        data_inicio = st.date_input('Data de início', df['data'].min())
        data_fim = st.date_input('Data de fim', df['data'].max())


    # Aplicando filtros adicionais com base nas datas e outros critério
    df_filtrado = df_filtrado[
        (df_filtrado['data'] >= data_inicio) & 
        (df_filtrado['data'] <= data_fim) & 
        (df_filtrado['equipe'].isin(filtros['equipe'])) & 
        (df_filtrado['produto'].isin(filtros['produto'])) & 
        (df_filtrado['convenio_acronimo'].isin(filtros['convenio_acronimo'])) & 
        (df_filtrado['origem'].isin(filtros['origem']))
    ]

    # Corrigindo possíveis valores inválidos nas datas de etapa
    colunas_datas = ['data_negociacao', 'data_perda', 'data_contratacao', 'data_pago', 'data']

    # Filtrando df_filtrado com base na etapa selecionada
    if etapa_filtro == "Lead":
        df_filtrado = df_filtrado[df_filtrado['data'].notna()]    
    elif etapa_filtro == "Negociação":
        df_filtrado = df_filtrado[df_filtrado['data_negociacao'].notna()]
    elif etapa_filtro == "Perda":
        df_filtrado = df_filtrado[df_filtrado['data_perda'].notna()]
    elif etapa_filtro == "Contratação":
        df_filtrado = df_filtrado[df_filtrado['data_contratacao'].notna()]
    elif etapa_filtro == "Pago":
        df_filtrado = df_filtrado[df_filtrado['data_pago'].notna()]
    

    df_gasto = df_gasto[
        (df_gasto['data'] >= data_inicio) & (df_gasto['data'] <= data_fim) & 
        (df_gasto['Convênio'].isin(filtros['convenio_acronimo'])) & 
        (df_gasto['Produto'].isin(filtros['produto'])) & 
        (df_gasto['Equipe'].isin(filtros['equipe'])) & 
        (df_gasto['Canal'].isin(filtros['origem']))
    ]

    # Filtrar por dias úteis
    df_filtrado = limpeza.filtrar_dias_uteis(df_filtrado, data_inicio, data_fim, considerar_dias_uteis)
    df_gasto = limpeza.filtrar_dias_uteis(df_gasto, data_inicio, data_fim, considerar_dias_uteis)

    # Custos unitários e cálculo de gastos
    custos_unitarios = {'SMS': 0.048, 'RCS': 0.105, 'HYPERFLOW': 0.047, 'Whatsapp': 0.046}
    gastos = (
        df_gasto.groupby(['Equipe', 'Convênio', 'Produto', 'Canal', ])['Quantidade']
        .sum()
        .reset_index()
    )

    gastos['valor_pago'] = gastos['Canal'].map(custos_unitarios) * gastos['Quantidade']
    gastos['valor_pago'] = gastos['valor_pago'].round(2)

    # Exibir os KPIs
    aplicar_estilo_kpi()
    colunas = st.columns(6)
    exibir_kpis(df, df_filtrado, gastos, data_inicio, data_fim, considerar_dias_uteis, colunas)



    # GRAFICO 1 - GASTOS POR CADA CONVENIO/PRODUTO
    from graficos import grafico_gasto_convenio_produto
    with st.expander("Gasto por Convênio e Produto"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=1)
        fig = grafico_gasto_convenio_produto(df_filtrado, df_gasto, top_n)
        st.plotly_chart(fig, key=f'graf1')
    
    

    # GRAFICO 2 - QUANTIDADE DE LEADS POR ORIGEM
    from graficos import leads_por_origem
    with st.expander("Quantidade de Leads por Origem"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=2)
        fig = leads_por_origem(df_filtrado, df_gasto, top_n)
        st.plotly_chart(fig, key=f'graf2')

    # GRAFICO 3 - FUNIL DE ETAPAS
    from graficos import funil_de_etapas
    with st.expander("Funil de Geração de leads por Etapa"):
        fig = funil_de_etapas(df_filtrado, df_gasto)
        st.plotly_chart(fig, key=f'graf3')

    # GRAFICO 4 - COHORT DINAMICO
    from graficos import cohort_dinamico
    with st.expander("Cohort dinâmico para Etapas"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=3)
        fig = cohort_dinamico(df_filtrado, df_gasto)
        st.plotly_chart(fig, use_container_width=True)

    # GRAFICO 5 - CPL por Convênio/Produto
    from graficos import cpl_convenios_produto
    with st.expander("Custo por Lead (Convenio-Produto)"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=4)
        tipo_cpl = st.selectbox("Tipo de CPL que deseja visualizar:", ["Maiores CPLs", "Menores CPLs"], key="cpl_tipo")

        maiores = tipo_cpl == "Maiores CPLs"
        fig = cpl_convenios_produto(df_filtrado, df_gasto, top_n=top_n, maiores=maiores)
        st.plotly_chart(fig)

    # GRAFICO 6 - ROI por Convênio/Produto
    from graficos import roi_por_convenio_produto
    with st.expander("ROI por Convênio/Produto"):
        top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=5)
        tipo_roi = st.selectbox("Tipo de ROI que deseja visualizar:", ["Melhores ROIs", "Piores ROIs"], key="roi_tipo")
        
        melhores = tipo_roi == "Melhores ROIs"
        fig = roi_por_convenio_produto(df_filtrado, df_gasto, top_n=top_n, melhores=melhores)
        st.plotly_chart(fig)

    from graficos import quantidade_leads_por_convenio
    with st.expander("Quantidade de Leads por Convênio"):
        col1, col2 = st.columns([2, 1])
        with col1:
            top_n = st.slider("Quantos convênios deseja visualizar?", min_value=5, max_value=40, value=5, step=1, key=6)
        with col2:
            ordem = st.selectbox("Ordenar por:", options=["maiores", "menores"], index=0, key=61)
        
        fig = quantidade_leads_por_convenio(df_filtrado, df_gasto, top_n=top_n, ordem=ordem)
        st.plotly_chart(fig)


    from graficos import roi_por_canal, gasto_vs_comissao_por_canal
    with st.expander("Análise de ROI e Gasto por Canal"):
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Gasto x Comissão por Canal")
            fig_comparativo = gasto_vs_comissao_por_canal(df_filtrado, df_gasto)
            st.plotly_chart(fig_comparativo, use_container_width=True)
        
        with col2:
            st.subheader("ROI por Canal")
            fig_roi = roi_por_canal(df_filtrado, df_gasto)
            st.plotly_chart(fig_roi, use_container_width=True)
        

    from graficos import perdas_por_etapa
    with st.expander("Perdas por Etapa"):
        fig = perdas_por_etapa(df_filtrado)
        st.plotly_chart(fig)

    
    from graficos import grafico_leads_por_10k
    with st.expander("Leads estimados por 10k disparos"):
        top_n = st.slider("Quantos convênios deseja visualizar?", 5, 40, 10, 1)
        tipo_ordem = st.selectbox("Ordenar por:", ["maiores", "menores"])
        maiores = tipo_ordem == "maiores"

        fig, merged_final = grafico_leads_por_10k(df_filtrado, df_gasto, top_n=top_n, maiores=maiores)
        st.plotly_chart(fig, use_container_width=True)
        st.write(merged_final)

        # Adicionando o botão de download
        download_button(merged_final, filename="leads_por_10k.csv")
