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
        # Adicionado campo interesse_genero
        c.execute('''CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome TEXT, 
            whatsapp TEXT, 
            tamanho_roupa TEXT, 
            interesse_genero TEXT)''')
        # Adicionado campo genero_peca
        c.execute('''CREATE TABLE IF NOT EXISTS estoque (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            nome_peca TEXT, 
            tamanho TEXT, 
            genero_peca TEXT,
            valor REAL, 
            data_entrada TEXT, 
            status TEXT DEFAULT "Disponível")''')
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
    st.markdown("<h2 style='text-align: center;'>👗 Cliente Circular</h2>", unsafe_allow_html=True)
    
    tabs = st.tabs(["🏠 Início", "👥 Clientes", "👕 Estoque", "💰 Vendas", "📊 Insights"])

    with tabs[0]:
        st.subheader(f"Olá, {st.session_state.username}")
        v_df = get_data("SELECT valor_final FROM vendas")
        rec = v_df['valor_final'].sum() if not v_df.empty else 0.0
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        if st.button("Sair"):
            st.session_state.logged_in = False
            st.rerun()

    with tabs[1]:
        st.subheader("Cadastro de Clientes")
        with st.form("f_cli"):
            n = st.text_input("Nome")
            w = st.text_input("WhatsApp")
            t = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])
            g = st.radio("Interesse em vestuário:", ["Feminino", "Masculino", "Ambos"], horizontal=True)
            if st.form_submit_button("Salvar Cliente"):
                run_query("INSERT INTO clientes (nome, whatsapp, tamanho_roupa, interesse_genero) VALUES (?,?,?,?)", (n, w, t, g))
                st.success(f"Cliente {n} salvo!")
                st.rerun()
        st.dataframe(get_data("SELECT nome, whatsapp, tamanho_roupa, interesse_genero FROM clientes"), use_container_width=True)

    with tabs[2]:
        st.subheader("Entrada de Estoque")
        with st.form("f_est"):
            np = st.text_input("Peça")
            tp = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"], key="est_t")
            gp = st.radio("Gênero da Peça:", ["Feminino", "Masculino", "Unissex"], horizontal=True)
            vp = st.number_input("Preço", min_value=0.0)
            if st.form_submit_button("Adicionar ao Estoque"):
                hoje = datetime.now().strftime("%Y-%m-%d")
                run_query("INSERT INTO estoque (nome_peca, tamanho, genero_peca, valor, data_entrada) VALUES (?,?,?,?,?)", (np, tp, gp, vp, hoje))
                st.success("Peça adicionada!")
                st.rerun()
        st.dataframe(get_data("SELECT nome_peca, tamanho, genero_peca, valor FROM estoque WHERE status='Disponível'"), use_container_width=True)

    with tabs[3]:
        st.subheader("Vendas")
        clis = get_data("SELECT id, nome FROM clientes")
        pecs = get_data("SELECT id, nome_peca, valor FROM estoque WHERE status='Disponível'")
        if not clis.empty and not pecs.empty:
            with st.form("f_ven"):
                sel_c = st.selectbox("Cliente", clis['nome'])
                sel_p = st.selectbox("Peça", pecs['nome_peca'])
                if st.form_submit_button("Confirmar Venda"):
                    c_id = int(clis[clis['nome'] == sel_c]['id'].iloc[0])
                    p_row = pecs[pecs['nome_peca'] == sel_p].iloc[0]
                    hoje = datetime.now().strftime("%Y-%m-%d")
                    run_query("INSERT INTO vendas (id_cliente, id_peca, data_venda, valor_final) VALUES (?,?,?,?)", (c_id, int(p_row['id']), hoje, float(p_row['valor'])))
                    run_query("UPDATE estoque SET status='Vendido' WHERE id=?", (int(p_row['id']),))
                    st.success("Venda realizada!")
                    st.rerun()
        else:
            st.warning("Cadastre clientes e peças primeiro.")

    with tabs[4]:
        st.subheader("Insights de Vendas")
        # SQL Otimizado: Combina tamanho E gênero (Ambos/Unissex incluídos na lógica)
        query_insights = """
            SELECT c.nome, c.whatsapp, e.nome_peca, e.valor, e.tamanho, e.genero_peca
            FROM clientes c 
            JOIN estoque e ON c.tamanho_roupa = e.tamanho 
            WHERE e.status = 'Disponível' 
            AND (c.interesse_genero = e.genero_peca OR c.interesse_genero = 'Ambos' OR e.genero_peca = 'Unissex')
        """
        df_m = get_data(query_insights)
        
        if not df_m.empty:
            for _, row in df_m.iterrows():
                msg = f"Oi {row['nome']}, chegou uma peça que é a sua cara! {row['nome_peca']} ({row['genero_peca']}), Tam {row['tamanho']} por R$ {row['valor']}. Quer reservar?"
                link = f"https://wa.me/{row['whatsapp']}?text={msg.replace(' ', '%20')}"
                
                with st.container():
                    col_info, col_btn = st.columns([3, 1])
                    col_info.write(f"🎯 **{row['nome']}** pode gostar de: **{row['nome_peca']}**")
                    col_btn.markdown(f"[Zap 📲]({link})")
                    st.divider()
        else:
            st.info("Nenhum match encontrado para o estoque atual.")

# --- 4. FLUXO DE LOGIN ---
def main():
    init_db()
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        st.markdown("<h2 style='text-align: center;'>♻️ Cliente Circular</h2>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            u = st.text_input("Usuário")
            p = st.text_input("Senha", type='password')
            if st.button("Entrar", use_container_width=True):
                with sqlite3.connect('cliente_circular.db') as conn:
                    c = conn.cursor()
                    c.execute('SELECT password FROM usuarios WHERE username=?', (u,))
                    res = c.fetchone()
                if res and check_hashes(p, res[0]):
                    st.session_state.logged_in = True
                    st.session_state.username = u
                    st.rerun()
                else:
                    st.error("Usuário ou senha incorretos")
    else:
        main_app()

if __name__ == '__main__':
    main()
