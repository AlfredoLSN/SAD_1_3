import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pulp

# Configuração da página
st.set_page_config(page_title="Simulador de redução de energia consumida", layout="wide")
st.title("⚡ Simulador Interativo: Meta de Redução de Energia")
st.markdown("Informe o consumo atual, configure as ações e selecione suas escolhas. O otimizador calculará o menor complemento para atingir a meta de forma justa.")

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
st.sidebar.write("Configure o valor de redução e ative as ações de sua preferência:")

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

todas_acoes = []

# Loop para renderizar os controles na barra lateral
for i, (nome_acao, valor_padrao) in enumerate(acoes_padrao):
    with st.sidebar.expander(f"🔹 {nome_acao}", expanded=False):
        valor_customizado = st.number_input(
            f"Redução Estimada (kWh):",
            min_value=0,
            value=valor_padrao,
            step=100,
            key=f"val_{i}"
        )
        ativada = st.checkbox("Forçar ativação desta ação", value=False, key=f"chk_{i}")

        todas_acoes.append({
            'id': i,
            'Ação': nome_acao,
            'Reducao_kWh': valor_customizado,
            'Forçada': ativada
        })

df_acoes = pd.DataFrame(todas_acoes)

# --- CÁLCULOS DINÂMICOS DO CENÁRIO ATUAL ---
meta_percentual = 0.15
meta_reducao = consumo_atual * meta_percentual
consumo_alvo = consumo_atual - meta_reducao

# Filtra o que o usuário escolheu manualmente na barra lateral
df_forcadas = df_acoes[df_acoes['Forçada'] == True]
total_reduzido_usuario = df_forcadas['Reducao_kWh'].sum()

# --- OTIMIZAÇÃO MATEMÁTICA MULTIOBJETIVO (MÍNIMO DE AÇÕES + MÍNIMO DESPERDÍCIO) ---
falta_para_meta = max(0.0, meta_reducao - total_reduzido_usuario)

acoes_recomendadas_pelo_modelo = []
sucesso_otimizacao = False

if falta_para_meta > 0:
    # Filtra apenas as ações que o usuário NÃO ativou manualmente e que possuem redução > 0
    df_disponiveis = df_acoes[(df_acoes['Forçada'] == False) & (df_acoes['Reducao_kWh'] > 0)]

    if not df_disponiveis.empty:
        # Criando o problema de programação linear inteira (Minimizar número de ações + Sobra)
        prob = pulp.LpProblem("Minimo_Acoes_Eficiente", pulp.LpMinimize)

        # Variáveis binárias para cada ação disponível (1 se escolhida, 0 se não)
        var_decisao = pulp.LpVariable.dicts("Adotar", df_disponiveis.index, cat='Binary')

        # Variável contínua para capturar o "Desperdício/Sobra" acima da meta
        folga_reducao = pulp.LpVariable("Sobra_Reducao", lowBound=0, cat='Continuous')

        # NOVA FUNÇÃO OBJETIVO:
        # Minimiza (Quantidade de Ações) + (Sobra de energia mitigada além do necessário com peso menor)
        # O peso de 0.0001 garante que o critério primário ainda seja a menor quantidade de ações.
        prob += pulp.lpSum([var_decisao[idx] for idx in df_disponiveis.index]) + (0.0001 * folga_reducao)

        # Restrição 1: Garantir que a meta complementar seja cumprida considerando a folga
        prob += pulp.lpSum([df_disponiveis.loc[idx, 'Reducao_kWh'] * var_decisao[idx] for idx in df_disponiveis.index]) == falta_para_meta + folga_reducao

        # Resolve o problema silenciosamente
        prob.solve(pulp.PULP_CBC_CMD(msg=False))

        # Se encontrou uma solução ótima, extrai as ações complementares ideais
        if pulp.LpStatus[prob.status] == 'Optimal':
            sucesso_otimizacao = True
            for idx in df_disponiveis.index:
                if var_decisao[idx].varValue == 1:
                    acoes_recomendadas_pelo_modelo.append(df_disponiveis.loc[idx].to_dict())
else:
    sucesso_otimizacao = True

# Preparação das listas para plotagem do Gráfico Empilhado
lista_final_grafico_nomes = list(df_forcadas['Ação'])
lista_final_grafico_valores = list(df_forcadas['Reducao_kWh'])

for acao_opt in acoes_recomendadas_pelo_modelo:
    lista_final_grafico_nomes.append(acao_opt['Ação'] + " (Sugerida)")
    lista_final_grafico_valores.append(acao_opt['Reducao_kWh'])

total_reduzido_geral = sum(lista_final_grafico_valores)
consumo_projetado_geral = max(0, consumo_atual - total_reduzido_geral)
percentual_atingido_geral = (total_reduzido_geral / consumo_atual) * 100

# --- EXIBIÇÃO DE MÉTRICAS ---
col1, col2, col3 = st.columns(3)
col1.metric("Consumo Atual Informado", f"{consumo_atual:,} kWh")
col2.metric("Meta de Redução (15%)", f"{meta_reducao:,.1f} kWh")

if total_reduzido_usuario >= meta_reducao:
    col3.metric("Status das SUAS Escolhas", "✅ META ATINGIDA", f"{(total_reduzido_usuario/consumo_atual)*100:.1f}% reduzido")
    st.success(f"As ações que você selecionou manualmente já são suficientes para reduzir {total_reduzido_usuario:,} kWh e bater a meta!")
else:
    col3.metric("Status das SUAS Escolhas", "❌ INSUFICIENTE", f"{(total_reduzido_usuario/consumo_atual)*100:.1f}% reduzido", delta_color="inverse")
    st.warning(f"Suas escolhas atuais somam {total_reduzido_usuario:,} kWh. O otimizador projetou o complemento ideal abaixo.")

# --- RENDERIZAÇÃO DO GRÁFICO EMPILHADO DINÂMICO ---
fig, ax = plt.subplots(figsize=(10, 5.5))
posicoes = [0, 1, 2]
largura = 0.55

ax.bar(posicoes[0], consumo_atual, color='#5c5c5c', width=largura, label='Consumo Inicial')
ax.bar(posicoes[1], consumo_alvo, color='#d9534f', width=largura, label='Meta Alvo (Máxima)')
ax.bar(posicoes[2], consumo_projetado_geral, color='#5cb85c' if total_reduzido_geral >= meta_reducao else '#f0ad4e', width=largura, label='Consumo Restante')

nivel_atual_empilhamento = consumo_projetado_geral
cores_acoes = ['#4a90e2', '#50e3c2', '#b8e986', '#f5a623', '#bd10e0', '#9013fe', '#e67e22', '#16a085']

for i, (nome, valor) in enumerate(zip(lista_final_grafico_nomes, lista_final_grafico_valores)):
    if valor > 0:
        cor_acao = cores_acoes[i % len(cores_acoes)]
        if "(Sugerida)" in nome:
            ax.bar(posicoes[2], valor, bottom=nivel_atual_empilhamento, color=cor_acao, width=largura, alpha=0.9, hatch="//")
        else:
            ax.bar(posicoes[2], valor, bottom=nivel_atual_empilhamento, color=cor_acao, width=largura, alpha=0.7)

        # Ajuste adaptável para rótulos pequenos em consumos baixos
        if valor > consumo_atual * 0.02:
            ax.text(posicoes[2], nivel_atual_empilhamento + (valor/2), f"-{valor:,} kWh\n{nome}",
                    ha='center', va='center', fontsize=8, weight='bold', color='black')
        nivel_atual_empilhamento += valor

ax.annotate(f'{consumo_atual:,} kWh', xy=(posicoes[0], consumo_atual), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')
ax.annotate(f'{consumo_alvo:,.1f} kWh', xy=(posicoes[1], consumo_alvo), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')
ax.annotate(f'{consumo_projetado_geral:,.1f} kWh', xy=(posicoes[2], consumo_projetado_geral), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, weight='bold')

ax.set_xticks(posicoes)
ax.set_xticklabels(['Consumo Atual', 'Meta Alvo', 'Projeção Otimizada\n(Suas Escolhas + Sugestões)'], fontsize=10, weight='bold')
ax.set_ylabel('Consumo de Energia (kWh)', fontsize=11, weight='bold')
ax.set_ylim(0, consumo_atual * 1.25)
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.axhline(consumo_alvo, color='#d9534f', linestyle='--')
ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=9, frameon=True)
plt.tight_layout()
st.pyplot(fig)

# --- PAINEL DINÂMICO DE RECOMENDAÇÃO ---
st.markdown("---")
st.header("🎯 Inteligência do Cenário: Complemento Mínimo de Ações")

if total_reduzido_usuario >= meta_reducao:
    st.info("💡 **Análise do Sistema:** Nenhuma ação adicional é necessária. Suas escolhas cumprem a meta perfeitamente.")
elif len(acoes_recomendadas_pelo_modelo) > 0 and sucesso_otimizacao:
    st.markdown(f"Para atingir o objetivo com o **menor número de ações** e evitando cortes excessivos desnecessários, ative:")

    col_cards = st.columns(max(2, len(acoes_recomendadas_pelo_modelo)))
    for idx, acao_opt in enumerate(acoes_recomendadas_pelo_modelo):
        with col_cards[idx]:
            st.metric(
                label=f"Sugestão Eficiente {idx+1}",
                value=acao_opt['Ação'],
                delta=f"-{acao_opt['Reducao_kWh']:,} kWh",
                delta_color="inverse"
            )
    st.caption(f"**Economia Total Estimada com o Conjunto Mínimo Otimizado:** {total_reduzido_geral - total_reduzido_usuario:,} kWh adicionais.")
else:
    total_possivel = df_acoes['Reducao_kWh'].sum()
    if total_possivel < meta_reducao:
        st.error(f"⚠️ **Cenário Inviável:** Mesmo ativando todas as ações, a redução máxima seria de {total_possivel:,} kWh, não alcançando a meta de {meta_reducao:,.1f} kWh.")
    else:
        st.error("⚠️ Não foi possível calcular uma combinação extra precisa.")