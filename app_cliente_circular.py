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
        /* Esconde elementos nativos do Streamlit que atrapalham no celular */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stAppDeployButton {display:none;}
        [data-testid="stStatusWidget"] {display:none;}
        
        /* Menu de Abas Estilo "Ilha Flutuante" - Foge da barra de propaganda */
        .stTabs [data-baseweb="tab-list"] {
            gap: 5px; 
            position: fixed; 
            bottom: 25px; /* Sobe o menu para não brigar com a barra do Streamlit */
            left: 10px; 
            right: 10px;
            background-color: #ffffff; 
            border: 1px solid #ddd;
            border-radius: 20px; 
            padding: 12px 10px;
            z-index: 10000; 
            display: flex; 
            justify-content: space-around;
            box-shadow: 0px 4px 15px rgba(0,0,0,0.2);
        }

        /* Aumenta os ícones das abas para facilitar o toque */
        .stTabs [data-baseweb="tab"] {
            height: 55px;
            background-color: transparent !important;
            border: none !important;
        }
        
        .stTabs [data-baseweb="tab"] div {
            font-size: 24px !important; /* Ícones grandes */
        }

        /* Espaço de segurança no final da página */
        .main .block-container { padding-bottom: 150px !important; }
        
        /* Botões mais amigáveis para o polegar */
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3.5em;
        }
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
            c.execute("INSERT INTO usuarios VALUES (?,?)", ('admin', make_hashes('ver.beta376@')))
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
    st.markdown("<h3 style='text-align: center;'>♻️ Cliente Circular</h3>", unsafe_allow_html=True)
    
    # Abas representadas por Emojis para máximo espaço no mobile
    tabs = st.tabs(["🏠", "👥", "👕", "💰", "📊", "⚙️"])

    # INÍCIO
    with tabs[0]:
        st.subheader(f"Olá, {st.session_state.username}")
        v_df = get_data("SELECT valor_final FROM vendas")
        rec = v_df['valor_final'].sum() if not v_df.empty else 0.0
        st.metric("Receita Bruta", f"R$ {rec:,.2f}")
        st.write("---")
        if st.button("Sair do App"):
            st.session_state.logged_in = False
            st.rerun()

    # CLIENTES
    with tabs[1]:
        st.subheader("Clientes")
        with st.form("f_cli", clear_on_submit=True):
            n = st.text_input("Nome")
            w = st.text_input("WhatsApp")
            t = st.selectbox("Tamanho", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])
            g = st.radio("Interesse:", ["Feminino", "Masculino", "Ambos"], horizontal=True)
            if st.form_submit_button("Salvar"):
                run_query("INSERT INTO clientes (nome, whatsapp, tamanho_roupa, interesse_genero) VALUES (?,?,?,?)", (n, w, t, g))
                st.success("Salvo!")
        st.dataframe(get_data("SELECT nome, tamanho_roupa, interesse_genero FROM clientes"), use_container_width=True)

    # ESTOQUE
    with tabs[2]:
        st.subheader("Estoque")
        with st.form("f_est", clear_on_submit=True):
            np = st.text_input("Peça")
            tp = st.selectbox("Tam", ["PP", "P", "M", "G", "GG", "G1", "G2", "G3"])
            gp = st.radio("Gênero:", ["Feminino", "Masculino", "Unissex"], horizontal=True)
            vp = st.number_input("Valor", min_value=0.0)
            if st.form_submit_button("Adicionar"):
                hoje = datetime.now().strftime("%Y-%m-%d")
                run_query("INSERT INTO estoque (nome_peca, tamanho, genero_peca, valor, data_entrada) VALUES (?,?,?,?,?)", (np, tp, gp, vp, hoje))
                st.success("Adicionado!")
        st.dataframe(get_data("SELECT nome_peca, tamanho, valor FROM estoque WHERE status='Disponível'"), use_container_width=True)

    # VENDAS
    with tabs[3]:
        st.subheader("Vendas")
        clis = get_data("SELECT id, nome FROM clientes")
        pecs = get_data("SELECT id, nome_peca, valor FROM estoque WHERE status='Disponível'")
        if not clis.empty and not pecs.empty:
            with st.form("f_ven"):
                sel_c = st.selectbox("Cliente", clis['nome'])
                sel_p = st.selectbox("Peça", pecs['nome_peca'])
                if st.form_submit_button("Vender"):
                    c_id = int(clis[clis['nome'] == sel_c]['id'].iloc[0])
                    p_row = pecs[pecs['nome_peca'] == sel_p].iloc[0]
                    hoje = datetime.now().strftime("%Y-%m-%d")
                    run_query("INSERT INTO vendas (id_cliente, id_peca, data_venda, valor_final) VALUES (?,?,?,?)", (c_id, int(p_row['id']), hoje, float(p_row['valor'])))
                    run_query("UPDATE estoque SET status='Vendido' WHERE id=?", (int(p_row['id']),))
                    st.success("Vendido!")
                    st.rerun()
        else:
            st.warning("Cadastre dados primeiro.")

    # INSIGHTS
    with tabs[4]:
        st.subheader("Matches Zap")
        df_m = get_data("""
            SELECT c.nome, c.whatsapp, e.nome_peca, e.valor, e.tamanho, e.genero_peca
            FROM clientes c JOIN estoque e ON c.tamanho_roupa = e.tamanho 
            WHERE e.status = 'Disponível'
            AND (c.interesse_genero = e.genero_peca OR c.interesse_genero = 'Ambos' OR e.genero_peca = 'Unissex')
        """)
        if not df_m.empty:
            for _, row in df_m.iterrows():
                msg = f"Oi {row['nome']}, chegou {row['nome_peca']} Tam {row['tamanho']} por R$ {row['valor']}. Reservar?"
                link = f"https://wa.me/{row['whatsapp']}?text={msg.replace(' ', '%20')}"
                st.info(f"🎯 **{row['nome']}** veste **{row['nome_peca']}**")
                st.markdown(f"[📲 Enviar WhatsApp]({link})")
                st.divider()
        else:
            st.info("Sem matches.")

    # AJUSTES
    with tabs[5]:
        st.subheader("Ajustes")
        with st.form("f_aj"):
            nu = st.text_input("Novo Usuário", value=st.session_state.username)
            ns = st.text_input("Nova Senha", type="password")
            if st.form_submit_button("Atualizar Acesso"):
                if nu and ns:
                    run_query("DELETE FROM usuarios")
                    run_query("INSERT INTO usuarios VALUES (?,?)", (nu, make_hashes(ns)))
                    st.success("Atualizado! Faça login novamente.")
                else:
                    st.error("Preencha tudo.")

# --- 4. FLUXO DE LOGIN ---
def main():
    init_db()
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if not st.session_state.logged_in:
        apply_custom_css()
        st.markdown("<h2 style='text-align: center;'>♻️ Cliente Circular</h2>", unsafe_allow_html=True)
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type='password')
        if st.button("Entrar"):
            with sqlite3.connect('cliente_circular.db') as conn:
                c = conn.cursor()
                c.execute('SELECT password FROM usuarios WHERE username=?', (u,))
                res = c.fetchone()
            if res and check_hashes(p, res[0]):
                st.session_state.logged_in = True
                st.session_state.username = u
                st.rerun()
            else:
                st.error("Login inválido")
    else:
        main_app()

if __name__ == '__main__':
    main()


