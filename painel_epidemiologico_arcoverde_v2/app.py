"""
Dashboard de Saúde - Arcoverde/PE
Painel de visualização de dados do SIM, SINAN e SINASC

VERSÃO: 2.0 - Melhorias de Segurança e Transparência
- Execução localhost por padrão
- Cache em formato Parquet (seguro)
- Modo demonstração explícito
- Transparência de fonte de dados
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from streamlit_folium import st_folium
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard de Saúde - Arcoverde/PE",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importações locais
from config import (
    MUNICIPIO, SISTEMAS, DOENCAS_SINAN, TEMA_CORES, 
    ATUALIZACAO, FAIXAS_ETARIAS
)
from data_loader import data_loader, calcular_faixa_etaria, processar_cid, set_demo_mode
from visualizations import charts, maps

# CSS personalizado para estilo similar ao CNIE
st.markdown("""
<style>
    /* Cores principais */
    :root {
        --primary: #1351B4;
        --secondary: #2670E8;
        --success: #168821;
        --warning: #FFCD07;
        --danger: #E52207;
        --info: #155BCB;
    }
    
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #1351B4 0%, #2670E8 100%);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }
    
    /* Banner de modo demonstração */
    .demo-banner {
        background: linear-gradient(135deg, #FFCD07 0%, #FFA500 100%);
        color: #333;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: bold;
        border: 2px solid #FF8C00;
    }
    
    /* Banner de erro de conexão */
    .error-banner {
        background: linear-gradient(135deg, #E52207 0%, #C41E3A 100%);
        color: white;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 1rem;
        text-align: center;
        font-weight: bold;
    }
    
    /* Info box */
    .info-box {
        background: #e8f4fd;
        border-left: 4px solid var(--info);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    /* Warning box */
    .warning-box {
        background: #fff8e1;
        border-left: 4px solid var(--warning);
        padding: 1rem;
        border-radius: 0 8px 8px 0;
        margin: 1rem 0;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #666;
        border-top: 1px solid #eee;
        margin-top: 3rem;
    }
    
    /* Métricas */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700 !important;
        color: var(--primary) !important;
    }
    
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        color: #666 !important;
    }
    
    /* Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #f0f2f6;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        font-weight: 500;
    }
    
    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)


# Variáveis de estado da sessão
if 'last_update_time' not in st.session_state:
    st.session_state.last_update_time = datetime.now()
if 'data_source_info' not in st.session_state:
    st.session_state.data_source_info = {}
if 'connection_errors' not in st.session_state:
    st.session_state.connection_errors = []


# Funções auxiliares
@st.cache_data(ttl=3600)
def carregar_dados_sistema(sistema: str, anos: list, **kwargs):
    """Carrega dados com cache"""
    return data_loader.get_multi_years_data(sistema, anos, **kwargs)


def calcular_indicadores(df_sim: pd.DataFrame, df_sinan: pd.DataFrame, 
                         df_sinasc: pd.DataFrame) -> dict:
    """Calcula indicadores principais"""
    indicadores = {
        'obitos': len(df_sim) if not df_sim.empty else 0,
        'notificacoes': len(df_sinan) if not df_sinan.empty else 0,
        'nascimentos': len(df_sinasc) if not df_sinasc.empty else 0,
        'taxa_mortalidade': 0,
        'taxa_natalidade': 0,
        'obitos_infantis': 0,
        'baixo_peso': 0
    }
    
    # Taxa de mortalidade (por 1000 habitantes)
    populacao = 76000  # População estimada de Arcoverde
    if indicadores['obitos'] > 0:
        indicadores['taxa_mortalidade'] = (indicadores['obitos'] / populacao) * 1000
    
    # Taxa de natalidade
    if indicadores['nascimentos'] > 0:
        indicadores['taxa_natalidade'] = (indicadores['nascimentos'] / populacao) * 1000
    
    # Óbitos infantis (< 1 ano)
    if not df_sim.empty and 'idade' in df_sim.columns:
        indicadores['obitos_infantis'] = len(df_sim[df_sim['idade'] < 1])
    
    # Baixo peso ao nascer (< 2500g)
    if not df_sinasc.empty and 'peso' in df_sinasc.columns:
        indicadores['baixo_peso'] = len(df_sinasc[df_sinasc['peso'] < 2500])
    
    return indicadores


def render_demo_banner():
    """Renderiza banner de modo demonstração"""
    if data_loader.is_demo_mode():
        st.markdown("""
        <div class="demo-banner">
            ⚠️ <strong>MODO DEMONSTRAÇÃO ATIVADO</strong> ⚠️<br>
            Os dados exibidos são FICTÍCIOS e servem apenas para demonstração do funcionamento do dashboard.<br>
            <em>NÃO utilize para análise epidemiológica real.</em>
        </div>
        """, unsafe_allow_html=True)


def render_connection_error_banner():
    """Renderiza banner de erro de conexão"""
    if st.session_state.connection_errors:
        errors = "<br>".join(st.session_state.connection_errors)
        st.markdown(f"""
        <div class="error-banner">
            ❌ <strong>ERRO DE CONEXÃO</strong> ❌<br>
            {errors}<br>
            <em>Verifique sua conexão com a internet e a disponibilidade do DATASUS.</em>
        </div>
        """, unsafe_allow_html=True)


def render_header():
    """Renderiza o cabeçalho"""
    st.markdown(f"""
    <div class="main-header">
        <h1>🏥 Dashboard de Saúde</h1>
        <p>{MUNICIPIO['nome']} - {MUNICIPIO['uf']} | {MUNICIPIO['mesorregiao']}</p>
        <p style="font-size: 0.9rem; margin-top: 1rem;">
            Dados do SIM, SINAN e SINASC integrados ao IBGE
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Renderiza a barra lateral com filtros"""
    st.sidebar.markdown("""
    <div style="text-align: center; padding: 1rem 0;">
        <h2 style="color: #1351B4; margin: 0;">⚙️ Filtros</h2>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("---")
    
    # Filtro de anos
    st.sidebar.subheader("📅 Período de Análise")
    ano_atual = datetime.now().year
    anos_disponiveis = list(range(2015, ano_atual + 1))
    
    ano_inicio, ano_fim = st.sidebar.select_slider(
        "Selecione o intervalo:",
        options=anos_disponiveis,
        value=(2020, ano_atual - 1)
    )
    
    anos_selecionados = list(range(ano_inicio, ano_fim + 1))
    
    st.sidebar.markdown("---")
    
    # Filtro de sistemas
    st.sidebar.subheader("🏥 Sistemas de Informação")
    
    sistemas_selecionados = {
        'SIM': st.sidebar.checkbox("SIM - Mortalidade", value=True),
        'SINAN': st.sidebar.checkbox("SINAN - Notificações", value=True),
        'SINASC': st.sidebar.checkbox("SINASC - Nascimentos", value=True)
    }
    
    st.sidebar.markdown("---")
    
    # Filtro de doenças (SINAN)
    if sistemas_selecionados['SINAN']:
        st.sidebar.subheader("🦠 Doenças (SINAN)")
        doencas_selecionadas = st.sidebar.multiselect(
            "Selecione as doenças:",
            options=list(DOENCAS_SINAN.values()),
            default=["Dengue", "Tuberculose"]
        )
    else:
        doencas_selecionadas = []
    
    st.sidebar.markdown("---")
    
    # Seção de Transparência Operacional
    st.sidebar.subheader("ℹ️ Informações do Sistema")
    
    # Status do PySUS
    if data_loader.is_pysus_available():
        st.sidebar.success("✅ PySUS conectado")
    else:
        st.sidebar.error("❌ PySUS não disponível")
    
    # Modo de operação
    if data_loader.is_demo_mode():
        st.sidebar.warning("⚠️ Modo Demonstração")
    else:
        st.sidebar.info("🟢 Modo Produção")
    
    st.sidebar.markdown("---")
    
    # Fonte dos dados e última atualização
    last_update = st.session_state.last_update_time.strftime('%d/%m/%Y %H:%M')
    
    st.sidebar.info(f"""
    **📊 Fonte dos Dados:**
    • PySUS (DATASUS)
    • IBGE (Localidades e Malhas)
    
    **🕐 Última atualização:**
    {last_update}
    
    **🔄 Próxima atualização:**
    {(datetime.now() + timedelta(days=7)).strftime('%d/%m/%Y')}
    """)
    
    # Informações técnicas (expansível)
    with st.sidebar.expander("🔧 Informações Técnicas"):
        st.markdown(f"""
        **Cache:** Formato Parquet
        **Permissões:** Restritas (0o600)
        **Versão:** 2.0
        **Ambiente:** {'Localhost (127.0.0.1)' if os.environ.get('STREAMLIT_SERVER_ADDRESS', '127.0.0.1') == '127.0.0.1' else 'Externo'}
        """)
    
    return anos_selecionados, sistemas_selecionados, doencas_selecionadas


def render_indicadores(indicadores: dict):
    """Renderiza cards de indicadores"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Óbitos (SIM)",
            value=f"{indicadores['obitos']:,}".replace(",", "."),
            delta=None
        )
    
    with col2:
        st.metric(
            label="Notificações (SINAN)",
            value=f"{indicadores['notificacoes']:,}".replace(",", "."),
            delta=None
        )
    
    with col3:
        st.metric(
            label="Nascimentos (SINASC)",
            value=f"{indicadores['nascimentos']:,}".replace(",", "."),
            delta=None
        )
    
    with col4:
        st.metric(
            label="Taxa Mortalidade",
            value=f"{indicadores['taxa_mortalidade']:.1f}‰",
            delta=None
        )


def render_tab_sim(df_sim: pd.DataFrame):
    """Renderiza aba do SIM"""
    st.header("📊 Sistema de Informação sobre Mortalidade (SIM)")
    
    if df_sim.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    # Aviso de dados simulados
    if '_demo_data' in df_sim.columns and df_sim['_demo_data'].any():
        st.warning("⚠️ Estes dados são FICTÍCIOS (modo demonstração).")
    
    # Layout em colunas
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolução temporal
        if 'ano' in df_sim.columns:
            evolucao = df_sim.groupby('ano').size().reset_index(name='quantidade')
            fig = charts.evolucao_temporal(
                evolucao, 
                titulo="Evolução de Óbitos por Ano",
                cor=TEMA_CORES["perigo"]
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribuição por sexo
        if 'sexo' in df_sim.columns:
            fig = charts.distribuicao_sexo(df_sim, titulo="Distribuição por Sexo")
            st.plotly_chart(fig, use_container_width=True)
    
    # Segunda linha
    col3, col4 = st.columns(2)
    
    with col3:
        # Distribuição por faixa etária
        if 'idade' in df_sim.columns:
            fig = charts.distribuicao_faixa_etaria(df_sim, titulo="Distribuição por Faixa Etária")
            st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Distribuição por raça/cor
        if 'raca_cor' in df_sim.columns:
            fig = charts.distribuicao_raca_cor(df_sim, titulo="Distribuição por Raça/Cor")
            st.plotly_chart(fig, use_container_width=True)
    
    # Terceira linha - Causas principais
    if 'causa_basica' in df_sim.columns:
        st.subheader("Principais Causas de Óbito (CID)")
        fig = charts.top_causas(df_sim, n_top=10)
        st.plotly_chart(fig, use_container_width=True)
    
    # Heatmap mensal
    if 'ano' in df_sim.columns and 'mes' in df_sim.columns:
        st.subheader("Heatmap de Óbitos por Ano e Mês")
        fig = charts.heatmap_mensal(df_sim, titulo="")
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de dados
    with st.expander("📋 Ver dados detalhados"):
        st.dataframe(df_sim.head(100), use_container_width=True)


def render_tab_sinan(df_sinan: pd.DataFrame):
    """Renderiza aba do SINAN"""
    st.header("🦠 Sistema de Informação de Agravos de Notificação (SINAN)")
    
    if df_sinan.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    # Aviso de dados simulados
    if '_demo_data' in df_sinan.columns and df_sinan['_demo_data'].any():
        st.warning("⚠️ Estes dados são FICTÍCIOS (modo demonstração).")
    
    # Layout em colunas
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolução temporal
        if 'ano' in df_sinan.columns:
            evolucao = df_sinan.groupby('ano').size().reset_index(name='quantidade')
            fig = charts.evolucao_temporal(
                evolucao,
                titulo="Evolução de Notificações por Ano",
                cor=TEMA_CORES["alerta"]
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribuição por doença
        if 'doenca' in df_sinan.columns:
            doencas = df_sinan['doenca'].value_counts().head(8)
            fig = go.Figure(data=[
                go.Bar(
                    x=doencas.values,
                    y=doencas.index,
                    orientation='h',
                    marker_color=TEMA_CORES["alerta"]
                )
            ])
            fig.update_layout(
                title="Notificações por Doença",
                xaxis_title="Quantidade",
                yaxis_title="Doença"
            )
            st.plotly_chart(charts._apply_theme(fig), use_container_width=True)
    
    # Segunda linha
    col3, col4 = st.columns(2)
    
    with col3:
        # Distribuição por faixa etária
        if 'idade' in df_sinan.columns:
            fig = charts.distribuicao_faixa_etaria(df_sinan, titulo="Distribuição por Faixa Etária")
            st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        # Distribuição por sexo
        if 'sexo' in df_sinan.columns:
            fig = charts.distribuicao_sexo(df_sinan, titulo="Distribuição por Sexo")
            st.plotly_chart(fig, use_container_width=True)
    
    # Evolução por doença
    if 'ano' in df_sinan.columns and 'doenca' in df_sinan.columns:
        st.subheader("Evolução por Doença")
        evo_doencas = df_sinan.groupby(['ano', 'doenca']).size().reset_index(name='quantidade')
        
        fig = go.Figure()
        for doenca in evo_doencas['doenca'].unique()[:5]:
            dados = evo_doencas[evo_doencas['doenca'] == doenca]
            fig.add_trace(go.Scatter(
                x=dados['ano'],
                y=dados['quantidade'],
                mode='lines+markers',
                name=doenca
            ))
        
        fig.update_layout(
            title="Evolução das Principais Doenças",
            xaxis_title="Ano",
            yaxis_title="Notificações",
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        st.plotly_chart(charts._apply_theme(fig), use_container_width=True)
    
    # Tabela de dados
    with st.expander("📋 Ver dados detalhados"):
        st.dataframe(df_sinan.head(100), use_container_width=True)


def render_tab_sinasc(df_sinasc: pd.DataFrame):
    """Renderiza aba do SINASC"""
    st.header("👶 Sistema de Informações sobre Nascidos Vivos (SINASC)")
    
    if df_sinasc.empty:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return
    
    # Aviso de dados simulados
    if '_demo_data' in df_sinasc.columns and df_sinasc['_demo_data'].any():
        st.warning("⚠️ Estes dados são FICTÍCIOS (modo demonstração).")
    
    # Indicadores específicos
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_nasc = len(df_sinasc)
        st.metric("Total de Nascimentos", f"{total_nasc:,}".replace(",", "."))
    
    with col2:
        if 'peso' in df_sinasc.columns:
            baixo_peso = len(df_sinasc[df_sinasc['peso'] < 2500])
            pct_baixo_peso = (baixo_peso / total_nasc * 100) if total_nasc > 0 else 0
            st.metric("Baixo Peso (<2500g)", f"{pct_baixo_peso:.1f}%")
    
    with col3:
        if 'gestacao_semanas' in df_sinasc.columns:
            prematuro = len(df_sinasc[df_sinasc['gestacao_semanas'] < 37])
            pct_prematuro = (prematuro / total_nasc * 100) if total_nasc > 0 else 0
            st.metric("Prematuros (<37s)", f"{pct_prematuro:.1f}%")
    
    with col4:
        if 'idade_mae' in df_sinasc.columns:
            idade_media = df_sinasc['idade_mae'].mean()
            st.metric("Idade Média da Mãe", f"{idade_media:.1f} anos")
    
    st.markdown("---")
    
    # Layout em colunas
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolução temporal
        if 'ano' in df_sinasc.columns:
            evolucao = df_sinasc.groupby('ano').size().reset_index(name='quantidade')
            fig = charts.evolucao_temporal(
                evolucao,
                titulo="Evolução de Nascimentos por Ano",
                cor=TEMA_CORES["sucesso"]
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Distribuição por sexo
        if 'sexo' in df_sinasc.columns:
            fig = charts.distribuicao_sexo(df_sinasc, titulo="Distribuição por Sexo do RN")
            st.plotly_chart(fig, use_container_width=True)
    
    # Gráficos específicos do SINASC
    graficos_sinasc = charts.indicadores_sinasc(df_sinasc)
    
    col3, col4 = st.columns(2)
    
    with col3:
        if 'peso' in graficos_sinasc:
            st.plotly_chart(graficos_sinasc['peso'], use_container_width=True)
    
    with col4:
        if 'idade_mae' in graficos_sinasc:
            st.plotly_chart(graficos_sinasc['idade_mae'], use_container_width=True)
    
    # Tipo de parto
    if 'tipo_parto' in graficos_sinasc:
        st.plotly_chart(graficos_sinasc['tipo_parto'], use_container_width=True)
    
    # Tabela de dados
    with st.expander("📋 Ver dados detalhados"):
        st.dataframe(df_sinasc.head(100), use_container_width=True)


def render_tab_comparativo(df_sim: pd.DataFrame, df_sinan: pd.DataFrame, df_sinasc: pd.DataFrame):
    """Renderiza aba comparativa"""
    st.header("📈 Análise Comparativa entre Sistemas")
    
    dados = {}
    if not df_sim.empty:
        dados['SIM'] = df_sim
    if not df_sinan.empty:
        dados['SINAN'] = df_sinan
    if not df_sinasc.empty:
        dados['SINASC'] = df_sinasc
    
    if len(dados) < 2:
        st.warning("Selecione pelo menos dois sistemas para comparar.")
        return
    
    # Aviso de dados simulados
    has_demo_data = any(
        '_demo_data' in df.columns and df['_demo_data'].any()
        for df in dados.values()
    )
    if has_demo_data:
        st.warning("⚠️ Alguns dados exibidos são FICTÍCIOS (modo demonstração).")
    
    # Gráfico comparativo
    fig = charts.comparativo_sistemas(dados)
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabela resumo
    st.subheader("Resumo por Sistema e Ano")
    
    resumo = []
    for sistema, df in dados.items():
        if 'ano' in df.columns:
            for ano in sorted(df['ano'].unique()):
                count = len(df[df['ano'] == ano])
                resumo.append({
                    'Sistema': sistema,
                    'Ano': ano,
                    'Quantidade': count
                })
    
    if resumo:
        df_resumo = pd.DataFrame(resumo)
        pivot_resumo = df_resumo.pivot(index='Ano', columns='Sistema', values='Quantidade').fillna(0)
        st.dataframe(pivot_resumo, use_container_width=True)


def render_tab_mapa():
    """Renderiza aba do mapa"""
    st.header("🗺️ Localização Geográfica")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Mapa do município
        m = maps.create_base_map()
        st_folium(m, width=700, height=500)
    
    with col2:
        st.subheader("Informações do Município")
        
        info = f"""
        **Nome:** {MUNICIPIO['nome']}
        
        **UF:** {MUNICIPIO['uf']}
        
        **Código IBGE:** {MUNICIPIO['codigo_ibge']}
        
        **Região:** {MUNICIPIO['regiao']}
        
        **Mesorregião:** {MUNICIPIO['mesorregiao']}
        
        **Microrregião:** {MUNICIPIO['microrregiao']}
        
        **Latitude:** {MUNICIPIO['latitude']}
        
        **Longitude:** {MUNICIPIO['longitude']}
        """
        
        st.markdown(info)
        
        # Link para IBGE
        st.markdown(f"""
        [🔗 Ver no IBGE](https://www.ibge.gov.br/cidades-e-estados/pe/{MUNICIPIO['nome'].lower().replace(' ', '-')}.html)
        """)


def render_footer():
    """Renderiza o rodapé com informações de fonte de dados"""
    last_update = st.session_state.last_update_time.strftime('%d/%m/%Y %H:%M')
    
    st.markdown(f"""
    <div class="footer">
        <p><strong>Dashboard de Saúde - Arcoverde/PE</strong></p>
        <p>📊 Fonte dos dados: PySUS (DATASUS) + IBGE</p>
        <p>🕐 Última atualização: {last_update}</p>
        <p style="font-size: 0.8rem; color: #999;">
            Desenvolvido para a Vigilância Epidemiológica | Versão 2.0
        </p>
    </div>
    """, unsafe_allow_html=True)


# Função principal
def main():
    """Função principal do dashboard"""
    
    # Header
    render_header()
    
    # Banners de aviso
    render_demo_banner()
    render_connection_error_banner()
    
    # Sidebar e filtros
    anos_selecionados, sistemas_selecionados, doencas_selecionadas = render_sidebar()
    
    # Limpar erros anteriores
    st.session_state.connection_errors = []
    
    # Barra de progresso durante o carregamento
    with st.spinner("Carregando dados..."):
        # Carregar dados
        df_sim = pd.DataFrame()
        df_sinan = pd.DataFrame()
        df_sinasc = pd.DataFrame()
        
        if sistemas_selecionados['SIM']:
            try:
                df_sim = carregar_dados_sistema('SIM', anos_selecionados)
            except Exception as e:
                st.session_state.connection_errors.append(f"SIM: {str(e)}")
        
        if sistemas_selecionados['SINAN']:
            try:
                df_sinan = carregar_dados_sistema('SINAN', anos_selecionados)
            except Exception as e:
                st.session_state.connection_errors.append(f"SINAN: {str(e)}")
        
        if sistemas_selecionados['SINASC']:
            try:
                df_sinasc = carregar_dados_sistema('SINASC', anos_selecionados)
            except Exception as e:
                st.session_state.connection_errors.append(f"SINASC: {str(e)}")
        
        # Atualizar timestamp
        st.session_state.last_update_time = datetime.now()
    
    # Calcular indicadores
    indicadores = calcular_indicadores(df_sim, df_sinan, df_sinasc)
    
    # Renderizar indicadores
    render_indicadores(indicadores)
    
    st.markdown("---")
    
    # Abas
    tab_sim, tab_sinan, tab_sinasc, tab_comp, tab_mapa = st.tabs([
        "📊 SIM (Mortalidade)",
        "🦠 SINAN (Notificações)",
        "👶 SINASC (Nascimentos)",
        "📈 Comparativo",
        "🗺️ Mapa"
    ])
    
    with tab_sim:
        if sistemas_selecionados['SIM']:
            render_tab_sim(df_sim)
        else:
            st.info("Ative o SIM na barra lateral para visualizar dados.")
    
    with tab_sinan:
        if sistemas_selecionados['SINAN']:
            render_tab_sinan(df_sinan)
        else:
            st.info("Ative o SINAN na barra lateral para visualizar dados.")
    
    with tab_sinasc:
        if sistemas_selecionados['SINASC']:
            render_tab_sinasc(df_sinasc)
        else:
            st.info("Ative o SINASC na barra lateral para visualizar dados.")
    
    with tab_comp:
        render_tab_comparativo(df_sim, df_sinan, df_sinasc)
    
    with tab_mapa:
        render_tab_mapa()
    
    # Footer
    render_footer()


if __name__ == "__main__":
    main()
