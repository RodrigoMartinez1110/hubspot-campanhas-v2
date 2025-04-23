import pandas as pd

def tratar_arquivo_hubspot(df):
    # Renomear colunas
    colunas_renomeadas = {
        'ID do registro.': 'id',
        'Nome do negócio': 'nome',
        'Data de criação': 'data_criado',
        'CPF': 'cpf',
        'Telefone': 'telefone',
        'Convênio': 'convenio',
        'Origem': 'origem',
        'Campanha': 'tag_campanha',
        'Proprietário original do negócio': 'vendedor',
        'Tipo de Campanha': 'produto',
        'Equipe da HubSpot': 'equipe',
        'Etapa do negócio': 'etapa',
        'Motivo de fechamento perdido': 'motivo_fechamento',
        'Comissão total projetada': 'comissao_projetada',
        'Valor': 'comissao_gerada',
        'Proprietário do negócio': 'vendedor2',
        'Date entered "CONTRATAÇÃO ( Pipeline de Vendas)"': 'data_contratacao',
        'Date entered "LEAD ( Pipeline de Vendas)"': 'data_lead',
        'Date entered "NEGOCIAÇÃO ( Pipeline de Vendas)"': 'data_negociacao',
        'Date entered "PAGO ( Pipeline de Vendas)"': 'data_pago',
        'Date entered "PERDA ( Pipeline de Vendas)"': 'data_perda',
        'Detalhes do motivo de perda': 'detalhe_perda',
        'Comissão Konsigleads': 'comissao_paga'
    }
    df = df.rename(columns=colunas_renomeadas)

    # Agrupamento de motivos
    motivos_principais = {
        'Sem Interação', 'Telefone Inválido', 'Sem interesse', 'Sem oportunidade',
        'Lead respondeu "NÃO" ao disparo', 'Vínculo inadequado', 'Desistência do Cliente',
        'Sem interação; Sem interesse', 'Não atende', 'Não receber mensagens - LGPD',
        'Margem Insuficiente'
    }
    df['motivo_fechamento_agrupado'] = df['motivo_fechamento'].apply(
        lambda x: x if x in motivos_principais else 'Outros'
    )

    # Função auxiliar para acrônimos de convênio
    def criar_acronimo(convenio):
        if not isinstance(convenio, str):
            return ''
        convenio = convenio.lower()
        mapeamento = {
            'prefeitura de recife': 'PREF REC',
            'prefeitura de curitiba': 'PREF CUR',
            'prefeitura de maringá': 'PREF MAR',
            'prefeitura de goiânia': 'PREF GOI',
            'prefeitura de belo horizonte': 'PREF BH',
            'governo de rondônia': 'GOV RO',
            'governo do paraná': 'GOV PR',
            'prefeitura de são paulo': 'PREF SP',
            'governo de são paulo': 'GOV SP',
            'prefeitura do rio de janeiro': 'PREF RJ',
            'governo do rio de janeiro': 'GOV RJ',
            'prefeitura de salvador': 'PREF SSA',
            'governo da bahia': 'GOV BA',
            'governo de alagoas': 'GOV AL',
            'governo do amazonas': 'GOV AM',
            'governo do maranhão': 'GOV MA',
            'governo de goiás': 'GOV GO',
            'governo do ceará': 'GOV CE',
            'governo de pernambuco': 'GOV PE',
            'governo de mato grosso do sul': 'GOV MS',
            'governo de mato grosso': 'GOV MT',
            'governo do piauí': 'GOV PI',
            'prefeitura de joão pessoa': 'PREF JP',
            'governo de minas gerais': 'GOV MG',
            'governo de santa catarina': 'GOV SC',
            'inss': 'INSS',
            'siape': 'SIAPE',
            'tribunal de justiça de são paulo (tjsp)': 'TJSP',
            'governo do espírito santo': 'GOV ES',
            'marinha': 'Marinha',
            'iniciativa privada': 'CLT'
        }
        return mapeamento.get(convenio, convenio)

    df['convenio_acronimo'] = df['convenio'].apply(criar_acronimo)

    # Padronizar valores da coluna 'equipe'
    substituicoes_equipe = {
        'Cs Cp': 'Cs Cp',
        'Cs Port': 'Cs Port',
        'Sales app': 'Esteira',
        'Sales': 'Sales',
        'Cs Ativação': 'Cs Ativacao',
        'Cs App': 'Cs App',
    }

    

    for chave, valor in substituicoes_equipe.items():
        df.loc[df['equipe'].str.contains(chave, case=False, na=False), 'equipe'] = valor

    # Converter colunas de data
    df['data_criado'] = pd.to_datetime(df['data_criado'], errors='coerce')
    df['data'] = df['data_criado'].dt.date
    df['horario_criado'] = df['data_criado'].dt.time
    df.drop(columns=['data_criado'], inplace=True)

    colunas_data_extra = ['data_lead', 'data_negociacao', 'data_contratacao', 'data_pago']
    for coluna in colunas_data_extra:
        df[coluna] = pd.to_datetime(df[coluna], errors='coerce').dt.date

    df.loc[df['equipe'] == 'Cs Cdx', 'produto'] = 'CDX'
    df.loc[df['equipe'] == 'Cs Cp', 'produto'] = 'CP'
    df.loc[df['equipe'] == 'Cs Port', 'produto'] = 'Port'


    df.loc[(df['origem'] == 'HYPERFLOW') & (df['equipe'] == 'Sales'), 'origem'] = 'RCS'
    df.loc[(df['origem'] == 'Duplicação Negócio App') & (df['equipe'] == 'Sales'), 'origem'] = 'Duplicacao'
    df.loc[(df['origem'] == 'Duplicação') & (df['equipe'] == 'Sales'), 'origem'] = 'Duplicacao'

    return df


def tratar_arquivo_pagos(dataframe):
    dataframe['data'] = pd.to_datetime(dataframe['Data'], errors='coerce', dayfirst=True).dt.date
    dataframe['Valor Gasto'] = (dataframe['Canal'].map({'SMS': 0.047, 'RCS': 0.105, 'HYPERFLOW': 0.04672, 'Whatsapp': 0.04672}) * dataframe['Quantidade']).round(2)
    return dataframe


def filtrar_dias_uteis(df, data_inicio, data_fim, considerar_dias_uteis):
    if considerar_dias_uteis:
        dias_uteis = pd.bdate_range(start=data_inicio, end=data_fim)
        return df[df['data'].isin(dias_uteis.date)]
    return df

