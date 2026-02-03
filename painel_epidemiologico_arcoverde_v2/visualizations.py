"""
Módulo de visualizações para o Dashboard de Saúde
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import folium
from folium.plugins import HeatMap, MarkerCluster
import json

from config import (
    TEMA_CORES, PALETA_GRAFICOS, MUNICIPIO, 
    FAIXAS_ETARIAS, RACA_COR, ESCOLARIDADE, ESTADO_CIVIL
)


class DashboardCharts:
    """Classe para criar gráficos do dashboard"""
    
    def __init__(self):
        self.colors = PALETA_GRAFICOS
        self.theme = TEMA_CORES
        
    def _apply_theme(self, fig: go.Figure) -> go.Figure:
        """Aplica tema padrão aos gráficos"""
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12, color=self.theme["preto"]),
            paper_bgcolor=self.theme["branco"],
            plot_bgcolor=self.theme["cinza_claro"],
            margin=dict(l=40, r=40, t=60, b=40),
            title_font=dict(size=16, color=self.theme["primaria"], family="Arial, sans-serif"),
            legend=dict(
                bgcolor="rgba(255,255,255,0.8)",
                bordercolor=self.theme["cinza"],
                borderwidth=1
            )
        )
        return fig
    
    def indicadores_cards(self, dados: Dict[str, int]) -> go.Figure:
        """Cria cards de indicadores principais"""
        fig = go.Figure()
        
        indicadores = [
            ("Óbitos (SIM)", dados.get('obitos', 0), self.theme["perigo"]),
            ("Notificações (SINAN)", dados.get('notificacoes', 0), self.theme["alerta"]),
            ("Nascimentos (SINASC)", dados.get('nascimentos', 0), self.theme["sucesso"]),
            ("Taxa Mortalidade", f"{dados.get('taxa_mortalidade', 0):.1f}", self.theme["info"]),
        ]
        
        for i, (titulo, valor, cor) in enumerate(indicadores):
            fig.add_trace(go.Indicator(
                mode="number",
                value=float(str(valor).replace(',', '')) if isinstance(valor, str) else valor,
                title={"text": titulo, "font": {"size": 14, "color": self.theme["cinza"]}},
                number={"font": {"size": 36, "color": cor}, "suffix": ""},
                domain={'row': 0, 'column': i}
            ))
        
        fig.update_layout(
            grid={'rows': 1, 'columns': 4, 'pattern': "independent"},
            height=150
        )
        
        return self._apply_theme(fig)
    
    def evolucao_temporal(self, df: pd.DataFrame, x_col: str = 'ano', 
                          y_col: str = 'quantidade', titulo: str = "",
                          cor: str = None) -> go.Figure:
        """Gráfico de linha para evolução temporal"""
        if cor is None:
            cor = self.theme["primaria"]
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df[x_col],
            y=df[y_col],
            mode='lines+markers',
            name='Quantidade',
            line=dict(color=cor, width=3),
            marker=dict(size=8, color=cor),
            fill='tozeroy',
            fillcolor=f"rgba(19, 81, 180, 0.1)"
        ))
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Período",
            yaxis_title="Quantidade",
            showlegend=False,
            hovermode='x unified'
        )
        
        return self._apply_theme(fig)
    
    def distribuicao_faixa_etaria(self, df: pd.DataFrame, 
                                   coluna_idade: str = 'idade',
                                   titulo: str = "Distribuição por Faixa Etária") -> go.Figure:
        """Gráfico de barras para distribuição por faixa etária"""
        # Calcular faixas etárias
        df['faixa_etaria'] = df[coluna_idade].apply(
            lambda x: next(
                (faixa for faixa, (min_i, max_i) in FAIXAS_ETARIAS.items() 
                 if min_i <= x <= max_i), "Não informado"
            )
        )
        
        contagem = df['faixa_etaria'].value_counts().reindex(FAIXAS_ETARIAS.keys()).fillna(0)
        
        fig = go.Figure(data=[
            go.Bar(
                x=contagem.index,
                y=contagem.values,
                marker_color=self.colors[:len(contagem)],
                text=contagem.values,
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Faixa Etária",
            yaxis_title="Quantidade",
            showlegend=False,
            xaxis_tickangle=-45
        )
        
        return self._apply_theme(fig)
    
    def distribuicao_raca_cor(self, df: pd.DataFrame, 
                               coluna_raca: str = 'raca_cor',
                               titulo: str = "Distribuição por Raça/Cor") -> go.Figure:
        """Gráfico de pizza para distribuição por raça/cor"""
        contagem = df[coluna_raca].value_counts()
        
        # Mapear códigos para nomes
        labels = [RACA_COR.get(str(k), str(k)) for k in contagem.index]
        
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=contagem.values,
                hole=0.4,
                marker_colors=self.colors[:len(contagem)],
                textinfo='label+percent',
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2)
        )
        
        return self._apply_theme(fig)
    
    def distribuicao_sexo(self, df: pd.DataFrame, 
                          coluna_sexo: str = 'sexo',
                          titulo: str = "Distribuição por Sexo") -> go.Figure:
        """Gráfico de pizza para distribuição por sexo"""
        contagem = df[coluna_sexo].value_counts()
        
        # Mapear códigos
        sexo_map = {'M': 'Masculino', 'F': 'Feminino', 'I': 'Ignorado'}
        labels = [sexo_map.get(str(k), str(k)) for k in contagem.index]
        
        colors_sexo = [self.theme["primaria"], "#E91E63", self.theme["cinza"]]
        
        fig = go.Figure(data=[
            go.Pie(
                labels=labels,
                values=contagem.values,
                marker_colors=colors_sexo[:len(contagem)],
                textinfo='label+percent',
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            showlegend=True
        )
        
        return self._apply_theme(fig)
    
    def top_causas(self, df: pd.DataFrame, coluna_causa: str = 'causa_basica',
                   n_top: int = 10, titulo: str = "Principais Causas") -> go.Figure:
        """Gráfico de barras horizontais para top causas"""
        contagem = df[coluna_causa].value_counts().head(n_top).sort_values()
        
        fig = go.Figure(data=[
            go.Bar(
                y=[f"CID: {c}" for c in contagem.index],
                x=contagem.values,
                orientation='h',
                marker_color=self.theme["primaria"],
                text=contagem.values,
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Quantidade",
            yaxis_title="Causa (CID)",
            showlegend=False,
            height=400
        )
        
        return self._apply_theme(fig)
    
    def heatmap_mensal(self, df: pd.DataFrame, ano_col: str = 'ano',
                       mes_col: str = 'mes', valor_col: str = None,
                       titulo: str = "Heatmap Mensal") -> go.Figure:
        """Heatmap de dados por ano e mês"""
        if valor_col:
            pivot = df.pivot_table(values=valor_col, index=ano_col, 
                                   columns=mes_col, aggfunc='sum', fill_value=0)
        else:
            pivot = df.pivot_table(index=ano_col, columns=mes_col, 
                                   aggfunc='size', fill_value=0)
        
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=[meses[i-1] if 1 <= i <= 12 else str(i) for i in pivot.columns],
            y=pivot.index,
            colorscale='Blues',
            text=pivot.values,
            texttemplate="%{text}",
            textfont={"size": 10},
            hoverongaps=False
        ))
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Mês",
            yaxis_title="Ano",
            height=300
        )
        
        return self._apply_theme(fig)
    
    def comparativo_sistemas(self, dados: Dict[str, pd.DataFrame],
                             titulo: str = "Comparativo entre Sistemas") -> go.Figure:
        """Gráfico comparativo entre SIM, SINAN e SINASC"""
        fig = go.Figure()
        
        cores = {
            'SIM': self.theme["perigo"],
            'SINAN': self.theme["alerta"],
            'SINASC': self.theme["sucesso"]
        }
        
        for sistema, df in dados.items():
            if 'ano' in df.columns and len(df) > 0:
                agg = df.groupby('ano').size().reset_index(name='quantidade')
                fig.add_trace(go.Scatter(
                    x=agg['ano'],
                    y=agg['quantidade'],
                    mode='lines+markers',
                    name=sistema,
                    line=dict(color=cores.get(sistema, self.theme["primaria"]), width=2)
                ))
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Ano",
            yaxis_title="Quantidade",
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=-0.3)
        )
        
        return self._apply_theme(fig)
    
    def distribuicao_escolaridade(self, df: pd.DataFrame,
                                   coluna_esc: str = 'escolaridade',
                                   titulo: str = "Distribuição por Escolaridade") -> go.Figure:
        """Gráfico de barras para escolaridade"""
        contagem = df[coluna_esc].value_counts().sort_index()
        
        labels = [ESCOLARIDADE.get(str(k), str(k)) for k in contagem.index]
        
        fig = go.Figure(data=[
            go.Bar(
                x=labels,
                y=contagem.values,
                marker_color=self.theme["terciaria"],
                text=contagem.values,
                textposition='outside'
            )
        ])
        
        fig.update_layout(
            title=titulo,
            xaxis_title="Escolaridade",
            yaxis_title="Quantidade",
            showlegend=False,
            xaxis_tickangle=-30
        )
        
        return self._apply_theme(fig)
    
    def indicadores_sinasc(self, df: pd.DataFrame) -> Dict[str, go.Figure]:
        """Cria gráficos específicos para SINASC"""
        figs = {}
        
        # Peso ao nascer
        if 'peso' in df.columns:
            fig_peso = go.Figure(data=[
                go.Histogram(
                    x=df['peso'],
                    nbinsx=30,
                    marker_color=self.theme["sucesso"]
                )
            ])
            fig_peso.update_layout(
                title="Distribuição do Peso ao Nascer",
                xaxis_title="Peso (g)",
                yaxis_title="Frequência"
            )
            figs['peso'] = self._apply_theme(fig_peso)
        
        # Idade da mãe
        if 'idade_mae' in df.columns:
            fig_idade_mae = go.Figure(data=[
                go.Histogram(
                    x=df['idade_mae'],
                    nbinsx=20,
                    marker_color=self.theme["primaria"]
                )
            ])
            fig_idade_mae.update_layout(
                title="Distribuição da Idade da Mãe",
                xaxis_title="Idade (anos)",
                yaxis_title="Frequência"
            )
            figs['idade_mae'] = self._apply_theme(fig_idade_mae)
        
        # Tipo de parto
        if 'tipo_parto' in df.columns:
            parto_map = {'1': 'Vaginal', '2': 'Cesárea', '9': 'Ignorado'}
            contagem = df['tipo_parto'].value_counts()
            labels = [parto_map.get(str(k), str(k)) for k in contagem.index]
            
            fig_parto = go.Figure(data=[
                go.Pie(
                    labels=labels,
                    values=contagem.values,
                    marker_colors=[self.theme["sucesso"], self.theme["info"], self.theme["cinza"]]
                )
            ])
            fig_parto.update_layout(title="Tipo de Parto")
            figs['tipo_parto'] = self._apply_theme(fig_parto)
        
        return figs


class MapVisualization:
    """Visualizações de mapa"""
    
    def __init__(self):
        self.municipio = MUNICIPIO
        
    def create_base_map(self) -> folium.Map:
        """Cria mapa base do município"""
        m = folium.Map(
            location=[self.municipio['latitude'], self.municipio['longitude']],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Adicionar marcador do município
        folium.Marker(
            [self.municipio['latitude'], self.municipio['longitude']],
            popup=f"<b>{self.municipio['nome']}</b><br>{self.municipio['mesorregiao']}",
            icon=folium.Icon(color='red', icon='info-sign')
        ).add_to(m)
        
        return m
    
    def add_heatmap(self, m: folium.Map, pontos: List[Tuple[float, float, float]]) -> folium.Map:
        """Adiciona heatmap ao mapa"""
        HeatMap(pontos, radius=15, blur=25).add_to(m)
        return m
    
    def add_marker_cluster(self, m: folium.Map, 
                          pontos: List[Dict]) -> folium.Map:
        """Adiciona cluster de marcadores"""
        marker_cluster = MarkerCluster().add_to(m)
        
        for ponto in pontos:
            folium.Marker(
                [ponto['lat'], ponto['lon']],
                popup=ponto.get('popup', ''),
                icon=folium.Icon(color=ponto.get('color', 'blue'))
            ).add_to(marker_cluster)
        
        return m


# Instância global
charts = DashboardCharts()
maps = MapVisualization()
