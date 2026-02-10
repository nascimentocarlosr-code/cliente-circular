import streamlit as st
import sqlite3
import pandas as pd
import hashlib
from datetime import datetime

# --- 1. CONFIGURAÇÕES DE INTERFACE ---
st.set_page_config(page_title="Cliente Circular", layout="wide")

# CSS Simplificado: Foco em legibilidade e botões grandes para mobile
def apply_custom_css():
    st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stButton>button {
            width: 100%;
            border-radius: 10px;
            height: 3em;
            background-color: #f0f2f6;
        }
        .main .block-container { padding-top: 2rem; }
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
        c.execute('CREATE TABLE IF NOT EXISTS clientes (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT, whatsapp TEXT, tamanho_roupa TEXT)')
        c.execute('CREATE TABLE IF NOT EXISTS estoque (id INTEGER PRIMARY KEY AUTOINCREMENT, nome_peca TEXT, tamanho TEXT, valor REAL, data_entrada TEXT, status TEXT DEFAULT "Disponível")')
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
    
    # Abas no topo para garantir vis
