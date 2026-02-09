import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- Configuração Inicial do Streamlit (Aparência de App) ---
st.set_page_config(layout="wide", initial_sidebar_state="collapsed")

# Remover o "Made with Streamlit"
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- Funções do Banco de Dados SQLite ---
def init_db():
    conn = sqlite3.connect('cliente_circular.db')
    c = conn.cursor()
    
    # Tabela Clientes
    c.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            whatsapp TEXT NOT NULL,
            genero_interesse TEXT,
            tamanho_roupa TEXT,
            tamanho_calcado TEXT,
            categorias_favoritas TEXT
        )
    ''')
    
    # Tabela Estoque
    c.execute('''
        CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_peca TEXT NOT NULL,
            tamanho TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            data_entrada TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Disponível'
        )
    ''')
    
    # Tabela Vendas
    c.execute('''
        CREATE TABLE IF NOT EXISTS vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_cliente INTEGER NOT NULL,
            id_peca INTEGER NOT NULL,
            data_venda TEXT NOT NULL,
            valor_final REAL NOT NULL,
            FOREIGN KEY (id_cliente) REFERENCES clientes(id),
            FOREIGN KEY (id_peca) REFERENCES estoque(id)
        )
    ''')
    conn.commit()
    conn.close()

def add_cliente(nome, whatsapp, genero, tamanho_roupa, tamanho_calcado, categorias):
    conn = sqlite3.connect('cliente_circular.db')
    c = conn.cursor()
    c.execute("INSERT INTO clientes (nome, whatsapp, genero_interesse, tamanho_roupa, tamanho_calcado, categorias_favoritas) VALUES (?, ?, ?, ?, ?, ?)",
              (nome, whatsapp, genero, tamanho_roupa, tamanho_calcado, categorias))
    conn.commit()
    conn.close()

def get_all_clientes():
    conn = sqlite3.connect('cliente_circular.db')
    df = pd.read_sql_query("SELECT * FROM clientes", conn)
    conn.close()
    return df

def add_peca(nome_peca, tamanho, categoria, valor):
    conn = sqlite3.connect('cliente_circular.db')
    c = conn.cursor()
    data_entrada = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO estoque (nome_peca, tamanho, categoria, valor, data_entrada) VALUES (?, ?, ?, ?, ?)",
              (nome_peca, tamanho, categoria, valor, data_entrada))
    conn.commit()
    conn.close()

def get_all_pecas():
    conn = sqlite3.connect('cliente_circular.db')
    df = pd.read_sql_query("SELECT * FROM estoque", conn)
    conn.close()
    return df

def registrar_venda(id_cliente, id_peca, valor_final):
    conn = sqlite3.connect('cliente_circular.db')
    c = conn.cursor()
    data_venda = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Insere a venda
    c.execute("INSERT INTO vendas (id_cliente, id_peca, data_venda, valor_final) VALUES (?, ?, ?, ?)",
              (id_cliente, id_peca, data_venda, valor_final))
    
    # Atualiza o status da peça para 'Vendido'
    c.execute("UPDATE estoque SET status = 'Vendido' WHERE id = ?", (id_peca,))
    
    conn.commit()
    conn.close()

def get_all_vendas():
    conn = sqlite3.connect('cliente_circular.db')
    df = pd.read_sql_query("""
        SELECT 
            v.id,
            c.nome AS cliente_nome,
            e.nome_peca AS peca_nome,
            v.data_venda,
            v.valor_final
        FROM vendas v
        JOIN clientes c ON v.id_cliente = c.id
        JOIN estoque e ON v.id_peca = e.id
    """, conn)
    conn.close()
    return df

# --- Lógica de Sugestão de Peças (Motor de Match) ---
def get_sugestoes_para_cliente(cliente_id):
    conn = sqlite3.connect('cliente_circular.db')
    
    cliente = pd.read_sql_query(f"SELECT * FROM clientes WHERE id = {cliente_id}", conn).iloc[0]
    
    tamanho_cliente = cliente['tamanho_roupa']
    categorias_cliente = cliente['categorias_favoritas'].split(',') if cliente['categorias_favoritas'] else []

    # Busca peças disponíveis, priorizando as mais antigas no estoque
    pecas_disponiveis = pd.read_sql_query(f"""
        SELECT * FROM estoque 
        WHERE status = 'Disponível' 
          AND tamanho = '{tamanho_cliente}' 
        ORDER BY data_entrada ASC
    """, conn)
    
    sugestoes = []
    for index, peca in pecas_disponiveis.iterrows():
        # Lógica de categorização mais robusta aqui se necessário
        if any(cat.strip().lower() in peca['categoria'].lower() for cat in categorias_cliente):
            sugestoes.append(peca)
            if len(sugestoes) >= 3: # Limita a 3 sugestões
                break
    
    conn.close()
    return pd.DataFrame(sugestoes)

# --- Funções de Dashboard ---
def get_dashboard_data():
    conn = sqlite3.connect('cliente_circular.db')
    
    total_receita_bruta = pd.read_sql_query("SELECT SUM(valor_final) FROM vendas", conn).iloc[0,0] or 0
    total_vendas = pd.read_sql_query("SELECT COUNT(*) FROM vendas", conn).iloc[0,0] or 0
    
    ticket_medio = total_receita_bruta / total_vendas if total_vendas > 0 else 0
    
    total_pecas_estoque = pd.read_sql_query("SELECT COUNT(*) FROM estoque", conn).iloc[0,0] or 0
    pecas_vendidas = pd.read_sql_query("SELECT COUNT(*) FROM estoque WHERE status = 'Vendido'", conn).iloc[0,0] or 0
    
    taxa_giro = (pecas_vendidas / total_pecas_estoque) * 100 if total_pecas_estoque > 0 else 0
    
    conn.close()
    return {
        "receita_bruta": total_receita_bruta,
        "ticket_medio": ticket_medio,
        "taxa_giro": taxa_giro
    }

# --- Inicializa o Banco de Dados ---
init_db()

# --- Estrutura da Interface do Usuário ---
st.title("♻️ Cliente Circular")

# Menu de Navegação na parte inferior para simular um app
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 0px; /* Remove gap entre as abas */
    position: fixed; /* Fixa no final da tela */
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #f0f2f6; /* Cor de fundo */
    border-top: 1px solid #ddd; /* Borda superior */
    padding: 10px 0; /* Padding */
    z-index: 9999; /* Garante que fique acima de outros elementos */
    width: 100%;
    display: flex;
    justify-content: space-around; /* Distribui os itens igualmente */
    
}
.stTabs [data-baseweb="tab"] {
    flex: 1; /* Faz as abas ocuparem o mesmo espaço */
    text-align: center;
    font-size: 14px;
    padding: 10px 0;
    margin: 0; /* Remove margens extras */
    color: #333;
    cursor: pointer;
    border-radius: 0; /* Remove borda arredondada */
}
.stTabs [data-baseweb="tab"]:hover {
    background-color: #e0e0e0;
}
.stTabs [aria-selected="true"] {
    background-color: #d1e7dd; /* Cor de destaque para aba selecionada */
    color: #155724; /* Cor do texto da aba selecionada */
    font-weight: bold;
    border-bottom: 3px solid #155724; /* Linha de destaque */
}
</style>
""", unsafe_allow_html=True)


tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏠 Início", "👥 Clientes", "👕 Estoque", "💰 Vendas", "📊 Insights"])

with tab1:
    st.header("Bem-vindo ao Cliente Circular!")
    st.subheader("Seu CRM inteligente para brechós de moda.")
    
    # Exibir um resumo rápido no início
    dashboard_data = get_dashboard_data()
    st.metric(label="Receita Bruta Total", value=f"R$ {dashboard_data['receita_bruta']:.2f}")
    st.metric(label="Ticket Médio", value=f"R$ {dashboard_data['ticket_medio']:.2f}")
    st.metric(label="Taxa de Giro de Estoque", value=f"{dashboard_data['taxa_giro']:.2f}%")
    
    st.markdown("---")
    st.subheader("Ações Rápidas")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Novo Cliente", use_container_width=True):
            st.session_state.current_tab = "Clientes"
            st.experimental_rerun() # Força a atualização para ir para a aba
    with col2:
        if st.button("📦 Nova Peça", use_container_width=True):
            st.session_state.current_tab = "Estoque"
            st.experimental_rerun()

with tab2:
    st.header("👥 Clientes")
    st.subheader("Gerencie sua base de clientes.")

    with st.expander("Cadastrar Novo Cliente"):
        with st.form("form_cliente"):
            nome = st.text_input("Nome")
            whatsapp = st.text_input("WhatsApp (Ex: 5511999998888)")
            genero_interesse = st.selectbox("Gênero de Interesse", ["Feminino", "Masculino", "Unissex", "Não Informado"])
            tamanho_roupa = st.selectbox("Tamanho de Roupa", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Único"])
            tamanho_calcado = st.text_input("Tamanho de Calçado (Ex: 37, 42)")
            categorias_favoritas = st.text_input("Categorias Favoritas (separadas por vírgula)")
            submit_cliente = st.form_submit_button("Salvar Cliente")
            if submit_cliente:
                add_cliente(nome, whatsapp, genero_interesse, tamanho_roupa, tamanho_calcado, categorias_favoritas)
                st.success("Cliente cadastrado com sucesso!")
                st.experimental_rerun() # Recarrega a página para mostrar o novo cliente

    st.subheader("Clientes Cadastrados")
    clientes_df = get_all_clientes()
    if not clientes_df.empty:
        st.dataframe(clientes_df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Sugestões de Peças para Clientes")
        
        cliente_para_sugestao = st.selectbox(
            "Selecione um cliente para ver sugestões:",
            clientes_df['nome'].unique()
        )
        
        if cliente_para_sugestao:
            cliente_id = clientes_df[clientes_df['nome'] == cliente_para_sugestao]['id'].iloc[0]
            sugestoes_df = get_sugestoes_para_cliente(cliente_id)
            
            if not sugestoes_df.empty:
                st.write(f"Sugestões para {cliente_para_sugestao}:")
                for index, peca in sugestoes_df.iterrows():
                    st.markdown(f"**{peca['nome_peca']}** (Tam: {peca['tamanho']}) - R$ {peca['valor']:.2f}")
                    # Gerar link do WhatsApp para a sugestão
                    msg = f"Olá {cliente_para_sugestao}, chegou uma {peca['nome_peca']} no seu tamanho ({peca['tamanho']}) por apenas R$ {peca['valor']:.2f}! Quer reservar?"
                    whatsapp_link = f"https://wa.me/{clientes_df[clientes_df['id'] == cliente_id]['whatsapp'].iloc[0]}?text={msg}"
                    st.markdown(f"[Enviar no WhatsApp]({whatsapp_link})", unsafe_allow_html=True)
                    st.markdown("---")
            else:
                st.info("Nenhuma sugestão encontrada para este cliente no estoque disponível.")
    else:
        st.info("Nenhum cliente cadastrado ainda.")

with tab3:
    st.header("👕 Estoque")
    st.subheader("Gerencie suas peças.")

    with st.expander("Cadastrar Nova Peça"):
        with st.form("form_peca"):
            nome_peca = st.text_input("Nome da Peça")
            tamanho_peca = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3", "Único"])
            categoria_peca = st.text_input("Categoria (Ex: Jaqueta, Vestido, Calça)")
            valor_peca = st.number_input("Valor (R$)", min_value=0.0, format="%.2f")
            submit_peca = st.form_submit_button("Salvar Peça")
            if submit_peca:
                add_peca(nome_peca, tamanho_peca, categoria_peca, valor_peca)
                st.success("Peça cadastrada com sucesso!")
                st.experimental_rerun()

    st.subheader("Estoque Atual")
    estoque_df = get_all_pecas()
    if not estoque_df.empty:
        st.dataframe(estoque_df, use_container_width=True)
    else:
        st.info("Nenhuma peça em estoque ainda.")

with tab4:
    st.header("💰 Vendas")
    st.subheader("Registre suas vendas e mantenha o estoque atualizado.")

    clientes_df_venda = get_all_clientes()
    pecas_disponiveis_df = get_all_pecas()
    pecas_disponiveis_df = pecas_disponiveis_df[pecas_disponiveis_df['status'] == 'Disponível']

    if not clientes_df_venda.empty and not pecas_disponiveis_df.empty:
        with st.form("form_venda"):
            cliente_selecionado = st.selectbox(
                "Cliente:",
                options=clientes_df_venda['nome'].tolist(),
                format_func=lambda x: f"{x}"
            )
            peca_selecionada = st.selectbox(
                "Peça (Disponível):",
                options=pecas_disponiveis_df.apply(lambda row: f"{row['nome_peca']} (Tam: {row['tamanho']}) - R$ {row['valor']:.2f}", axis=1).tolist()
            )
            
            # Recuperar o valor original da peça para preencher o campo
            peca_id_selecionada = pecas_disponiveis_df.loc[pecas_disponiveis_df.apply(lambda row: f"{row['nome_peca']} (Tam: {row['tamanho']}) - R$ {row['valor']:.2f}", axis=1) == peca_selecionada, 'id'].iloc[0]
            valor_original = pecas_disponiveis_df[pecas_disponiveis_df['id'] == peca_id_selecionada]['valor'].iloc[0]
            
            valor_final_venda = st.number_input("Valor Final da Venda (R$)", min_value=0.0, value=valor_original, format="%.2f")
            
            submit_venda = st.form_submit_button("Registrar Venda")
            
            if submit_venda:
                cliente_id = clientes_df_venda[clientes_df_venda['nome'] == cliente_selecionado]['id'].iloc[0]
                
                if peca_id_selecionada:
                    registrar_venda(cliente_id, peca_id_selecionada, valor_final_venda)
                    st.success("Venda registrada e peça removida do estoque disponível!")
                    st.experimental_rerun()
                else:
                    st.error("Por favor, selecione uma peça disponível.")
    else:
        st.info("Cadastre clientes e peças no estoque para registrar vendas.")

    st.subheader("Histórico de Vendas")
    vendas_df = get_all_vendas()
    if not vendas_df.empty:
        st.dataframe(vendas_df, use_container_width=True)
    else:
        st.info("Nenhuma venda registrada ainda.")

with tab5:
    st.header("📊 Insights do Negócio")
    st.subheader("Análises para impulsionar suas vendas.")

    dashboard_data = get_dashboard_data()
    
    st.metric(label="Receita Bruta Total", value=f"R$ {dashboard_data['receita_bruta']:.2f}")
    st.metric(label="Ticket Médio", value=f"R$ {dashboard_data['ticket_medio']:.2f}")
    st.metric(label="Taxa de Giro de Estoque", value=f"{dashboard_data['taxa_giro']:.2f}%")

    st.markdown("---")
    st.subheader("Peças no Estoque Paradas")
    conn = sqlite3.connect('cliente_circular.db')
    pecas_paradas_df = pd.read_sql_query("""
        SELECT * FROM estoque 
        WHERE status = 'Disponível' 
          AND date(data_entrada) < date('now', '-15 days') 
        ORDER BY data_entrada ASC
    """, conn)
    conn.close()

    if not pecas_paradas_df.empty:
        st.warning("Essas peças estão no estoque há mais de 15 dias! Considere promoções ou reengajamento.")
        st.dataframe(pecas_paradas_df, use_container_width=True)
    else:
        st.info("Nenhuma peça parada no estoque há mais de 15 dias. Ótimo trabalho!")

    st.markdown("---")
    st.subheader("Clientes para Reengajar")
    # Exemplo: Clientes que não compraram nos últimos 30 dias
    conn = sqlite3.connect('cliente_circular.db')
    clientes_ativos_recentemente = pd.read_sql_query("""
        SELECT DISTINCT id_cliente FROM vendas WHERE date(data_venda) >= date('now', '-30 days')
    """, conn)
    
    todos_clientes = get_all_clientes()
    clientes_para_reengajar_df = todos_clientes[~todos_clientes['id'].isin(clientes_ativos_recentemente['id_cliente'])]
    
    conn.close()
    
    if not clientes_para_reengajar_df.empty:
        st.info("Considere entrar em contato com esses clientes para reativá-los!")
        st.dataframe(clientes_para_reengajar_df[['nome', 'whatsapp']], use_container_width=True)
        # Opcional: botão para disparar mensagem para todos esses clientes
    else:
        st.info("Todos os clientes ativos fizeram uma compra recente (últimos 30 dias).")

# --- Executando o aplicativo ---
# Para rodar, salve este código como um arquivo .py (ex: app_cliente_circular.py)
# Abra o terminal na pasta onde salvou e digite:
# streamlit run app_cliente_circular.py
