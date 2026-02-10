import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# --- 1. CONFIGURAÇÕES DE INTERFACE ---
st.set_page_config(page_title="Cliente Circular", layout="wide", initial_sidebar_state="collapsed")

def apply_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stTabs [data-baseweb="tab-list"] {
            gap: 0px; position: fixed; bottom: 0; left: 0; right: 0;
            background-color: #ffffff; border-top: 1px solid #eee;
            z-index: 1000; display: flex; justify-content: space-around;
        }
        .main .block-container { padding-bottom: 80px; }
        </style>
    """, unsafe_allow_html=True)

# --- 2. BANCO DE DADOS E SEGURANÇA ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

def init_db():
    with sqlite3.connect('cliente_circular.db') as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS usuarios(username TEXT PRIMARY KEY, password TEXT)')
        c.execute('''CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, whatsapp TEXT, 
            tamanho_roupa TEXT, interesse_genero TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT, nome_peca TEXT, tamanho TEXT, 
            genero_peca TEXT, valor REAL, data_entrada TEXT, status TEXT DEFAULT "Disponível")''')
        c.execute('CREATE TABLE IF NOT EXISTS vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, id_cliente INTEGER, id_peca INTEGER, data_venda TEXT, valor_final REAL)')
        
        c.execute("SELECT * FROM usuarios WHERE username = 'admin'")
        if not c.fetchone():
            c.execute("INSERT INTO usuarios VALUES (?,?)", ('admin', make_hashes('admin123')))
        conn.commit()

def get_data(query):
    with sqlite3.connect('cliente_circular.db') as conn:
        return pd.read_sql_query(query, conn)

def run_query(query, params=()):
    with sqlite3.connect('cliente_circular.db') as conn:
        c = conn.cursor()
        c.execute(query, params)
        conn.commit()

# --- 3. APLICATIVO PRINCIPAL ---
def main_app():
    apply_custom_css()
    st.markdown("<h2 style='text-align: center;'>♻️ Cliente Circular</h2>", unsafe_allow_html=True)
    
    tabs = st.tabs(["🏠 Início", "👥 Clientes", "👕 Estoque", "💰 Vendas", "📊 Insights", "⚙️ Ajustes"])

    # --- ABA INÍCIO ---
    with tabs[0]:
        st.subheader(f"Olá, {st.session_state.username}")
        v_df = get_data("SELECT valor_final FROM vendas")
        rec = v_df['valor_final'].sum() if not v_df.empty else 0.0
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        
        st.write("---")
        if st.button("Encerrar Sessão (Sair)"):
            st.session_state.logged_in = False
            st.rerun()

    # --- ABA CLIENTES ---
    with tabs[1]:
        st.subheader("Cadastro de Clientes")
        with st.form("f_cli", clear_on_submit=True):
            n = st.text_input("Nome")
            w = st.text_input("WhatsApp (Ex: 5511999998888)")
            t = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])
            g = st.radio("Interesse em:", ["Feminino", "Masculino", "Ambos"], horizontal=True)
            if st.form_submit_button("Salvar Cliente"):
                run_query("INSERT INTO clientes (nome, whatsapp, tamanho_roupa, interesse_genero) VALUES (?,?,?,?)", (n, w, t, g))
                st.success("Cliente cadastrado!")
                st.rerun()
        st.dataframe(get_data("SELECT nome, whatsapp, tamanho_roupa, interesse_genero FROM clientes"), use_container_width=True)

    # --- ABA ESTOQUE ---
    with tabs[2]:
        st.subheader("Entrada de Peças")
        with st.form("f_est", clear_on_submit=True):
            np = st.text_input("Peça")
            tp = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])
            gp = st.radio("Gênero da Peça:", ["Feminino", "Masculino", "Unissex"], horizontal=True)
            vp = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Adicionar"):
                hoje = datetime.now().strftime("%Y-%m-%d")
                run_query("INSERT INTO estoque (nome_peca, tamanho, genero_peca, valor, data_entrada) VALUES (?,?,?,?,?)", (np, tp, gp, vp, hoje))
                st.success("Estoque atualizado!")
                st.rerun()
        st.dataframe(get_data("SELECT nome_peca, tamanho, genero_peca, valor FROM estoque WHERE status='Disponível'"), use_container_width=True)

    # --- ABA VENDAS ---
    with tabs[3]:
        st.subheader("Registrar Venda")
        clis = get_data("SELECT id, nome FROM clientes")
        pecs = get_data("SELECT id, nome_peca, valor FROM estoque WHERE status='Disponível'")
        if not clis.empty and not pecs.
