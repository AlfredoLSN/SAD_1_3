import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

#Para executar o código use !streamlit run Desktop/teste/app.py --server.headless true
#O executavel estara disponivel no link loca http://localhost:8501/ 

# Configuração da página
st.set_page_config(page_title="Simulador de redução de energia consumida", layout="wide")
st.title("⚡ Simulador Interativo: Meta de Redução de Energia")
st.markdown("Informe o consumo atual, configure o potencial de cada ação e selecione-as para verificar o impacto no gráfico.")

# --- BARRA LATERAL (ENTRADAS E CONFIGURAÇÃO DE VALORES) ---
st.sidebar.header("⚙️ Configurações Gerais")

# Entrada do Consumo Atual
consumo_atual = st.sidebar.number_input(
    "Informe o Consumo Atual (kWh):", 
    min_value=1, 
    value=100000, 
    step=1000
)

st.sidebar.markdown("---")
st.sidebar.header("📋 Ajuste de Valores e Seleção")
st.sidebar.write("Configure o valor de redução e ative as ações:")

# Lista de ações padrão do enunciado
acoes_padrao = [
    ('Troca para LED', 2000), 
    ('Sensores de Presença', 1500), 
    ('Manutenção Ar-Condicionado', 5000),
    ('Painéis Solares (Parcial)', 8000), 
    ('Painéis Solares (Total)', 12000), 
    ('Modernização de Motores', 6500), 
    ('Desligamento Automático', 1200), 
    ('Reeducação de consumo', 800)
]

acoes_selecionadas_nomes = []
acoes_selecionadas_valores = []

# Loop para renderizar o controle customizado de cada ação
for i, (nome_acao, valor_padrao) in enumerate(acoes_padrao):
    with st.sidebar.expander(f"🔹 {nome_acao}", expanded=False):
        valor_customizado = st.number_input(
            f"Redução Estimada (kWh):", 
            min_value=0, 
            value=valor_padrao, 
            step=100,
            key=f"val_{i}"
        )
        ativada = st.checkbox("Ativar esta ação no cenário", value=False, key=f"chk_{i}")
        
        if ativada:
            acoes_selecionadas_nomes.append(nome_acao)
            acoes_selecionadas_valores.append(valor_customizado)

# --- CÁLCULOS DINÂMICOS ---
meta_percentual = 0.15
meta_reducao = consumo_atual * meta_percentual
consumo_alvo = consumo_atual - meta_reducao

total_reduzido = sum(acoes_selecionadas_valores)
consumo_projetado = max(0, consumo_atual - total_reduzido)
percentual_atingido = (total_reduzido / consumo_atual) * 100

# --- EXIBIÇÃO DE MÉTRICAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Consumo Atual Informado", f"{consumo_atual:,} kWh")
col2.metric("Meta de Redução (15%)", f"{meta_reducao:,.1f} kWh")

if total_reduzido >= meta_reducao:
    col3.metric("Status da Meta", "✅ ATINGIDA", f"{percentual_atingido:.1f}% reduzido", delta_color="normal")
    st.success(f"Parabéns! O conjunto de ações reduziu {total_reduzido:,} kWh, superando a meta de {meta_reducao:,.1f} kWh.")
else:
    col3.metric("Status da Meta", "❌ NÃO ATINGIDA", f"{percentual_atingido:.1f}% reduzido", delta_color="inverse")
    st.error(f"Atenção: Faltam {max(0.0, meta_reducao - total_reduzido):,.1f} kWh para atingir a meta.")

# --- RENDERIZAÇÃO DO GRÁFICO (BI COM DECOMPOSIÇÃO) ---
fig, ax = plt.subplots(figsize=(10, 6.5)) # Aumentado levemente a altura para acomodar a legenda embaixo

posicoes = [0, 1, 2]
largura = 0.55

# 1. Barras de referência estática
ax.bar(posicoes[0], consumo_atual, color='#5c5c5c', width=largura, label='Consumo Inicial')
ax.bar(posicoes[1], consumo_alvo, color='#d9534f', width=largura, label='Meta Alvo (Máxima)')

# 2. Barra de decomposição do Cenário Projetado (Empilhada)
cor_base_projetada = '#5cb85c' if total_reduzido >= meta_reducao else '#f0ad4e'
ax.bar(posicoes[2], consumo_projetado, color=cor_base_projetada, width=largura, label='Consumo Restante')

nivel_atual_empilhamento = consumo_projetado
cores_acoes = ['#4a90e2', '#50e3c2', '#b8e986', '#f5a623', '#bd10e0', '#9013fe', '#e67e22', '#16a085']

# Adiciona os blocos das ações modificadas dinamicamente
for i, (nome, valor) in enumerate(zip(acoes_selecionadas_nomes, acoes_selecionadas_valores)):
    if valor > 0:
        cor_acao = cores_acoes[i % len(cores_acoes)]
        ax.bar(posicoes[2], valor, bottom=nivel_atual_empilhamento, color=cor_acao, width=largura, alpha=0.85, label=f"Redução: {nome}")
        
        if valor > consumo_atual * 0.03:
            ax.text(posicoes[2], nivel_atual_empilhamento + (valor/2), f"-{valor:,} kWh\n({nome})", 
                    ha='center', va='center', fontsize=8, weight='bold', color='black')
            
        nivel_atual_empilhamento += valor

# --- ANOTAÇÕES DO TOPO ---
ax.annotate(f'{consumo_atual:,} kWh', xy=(posicoes[0], consumo_atual), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')
ax.annotate(f'{consumo_alvo:,.0f} kWh', xy=(posicoes[1], consumo_alvo), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')
ax.annotate(f'{consumo_atual:,} kWh', xy=(posicoes[2], consumo_atual), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')

# --- CONFIGURAÇÕES DE LAYOUT ---
ax.set_xticks(posicoes)
ax.set_xticklabels(['Consumo Atual', 'Meta Alvo', 'Decomposição do\nCenário Projetado'], fontsize=10, weight='bold')
ax.set_ylabel('Consumo de Energia (kWh)', fontsize=11, weight='bold')
ax.set_ylim(0, consumo_atual * 1.25)
ax.grid(axis='y', linestyle='--', alpha=0.4)

# Linha horizontal da meta
ax.axhline(consumo_alvo, color='#d9534f', linestyle='--', linewidth=1.8, label='Limite Máximo da Meta')

# --- LEGENDA NA PARTE INFERIOR COORDENADA ---
# loc='upper center' e bbox_to_anchor=(0.5, -0.15) joga a legenda para baixo do gráfico
# ncol=3 distribui os itens em até 3 colunas horizontais para não virar uma lista vertical gigante
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=9, frameon=True)

# Ajusta o layout para garantir que a legenda inferior não seja cortada na renderização
plt.tight_layout()

st.pyplot(fig)