import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Livraria Aurora | Gestão', page_icon='📚', layout='wide')
ARQUIVO = Path(__file__).with_name('estoque_livraria.json')
LIMITE_BAIXO = 5

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --verde-profundo: #183B32;
    --verde-principal: #285C4D;
    --verde-suave: #8BAF9B;
    --verde-claro: #E4EDE5;
    --fundo: #F6F8F4;
    --texto: #243B32;
    --texto-secundario: #718078;
    --borda: #DCE6DD;
    --branco: #FFFFFF;
}

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: var(--fundo); color: var(--texto); }
[data-testid="stSidebar"] { background: var(--verde-profundo); }
[data-testid="stSidebar"] * { color: #F4F8F4 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 8px; }

.page-title {
    font-family: 'Playfair Display', serif;
    color: var(--verde-profundo);
    font-size: 34px;
    font-weight: 700;
}
.page-subtitle { color: var(--texto-secundario); margin: 0 0 24px; }
.metric-card {
    background: var(--branco);
    border: 1px solid var(--borda);
    border-radius: 13px;
    padding: 18px 20px;
    min-height: 120px;
}
.metric-label {
    color: var(--texto-secundario);
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.metric-value {
    color: var(--verde-profundo);
    font-size: 27px;
    font-weight: 700;
    margin-top: 9px;
}
.metric-help { color: var(--texto-secundario); font-size: 11px; }
.section-title {
    color: var(--verde-profundo);
    font-size: 18px;
    font-weight: 700;
    margin: 16px 0 12px;
}

.stButton > button[kind="primary"], .stFormSubmitButton > button {
    background: var(--verde-principal);
    border: 1px solid var(--verde-principal);
    color: white;
    font-weight: 700;
    border-radius: 8px;
}
.stButton > button[kind="primary"]:hover, .stFormSubmitButton > button:hover {
    background: var(--verde-profundo);
    border-color: var(--verde-profundo);
    color: white;
}
.stButton > button, .stDownloadButton > button { border-radius: 8px; }
[data-testid="stForm"] {
    background: var(--branco);
    border: 1px solid var(--borda);
    border-radius: 12px;
    padding: 18px;
}
[data-testid="stMetric"] {
    background: var(--branco);
    border: 1px solid var(--borda);
    border-radius: 10px;
    padding: 12px 15px;
}
[data-baseweb="input"] input,
[data-baseweb="textarea"] textarea,
[data-baseweb="select"] > div { border-radius: 8px; }
[data-testid="stDataFrame"] {
    border: 1px solid var(--borda);
    border-radius: 10px;
    overflow: hidden;
}
footer { visibility: hidden; }
</style>""", unsafe_allow_html=True)


def iniciais():
    return {'proximo_id':1,'categorias':['Romance','Didático','Infantil'],
            'metodos_pagamento':['Dinheiro','Pix','Cartão de crédito','Cartão de débito'],
            'produtos':{},'vendas':[]}

def carregar():
    if ARQUIVO.exists():
        try:
            with ARQUIVO.open(encoding='utf-8') as f: d=json.load(f)
            base=iniciais(); base.update(d); return base
        except (OSError,json.JSONDecodeError): st.warning('Não foi possível ler o arquivo de dados. Um cadastro inicial foi carregado.')
    return iniciais()

def salvar():
    tmp=ARQUIVO.with_suffix('.tmp')
    with tmp.open('w',encoding='utf-8') as f: json.dump(st.session_state.dados,f,ensure_ascii=False,indent=2)
    tmp.replace(ARQUIVO)

def brl(v):
    return 'R$ '+f'{float(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def ordenados(): return sorted(st.session_state.dados['produtos'].items(),key=lambda x:int(x[0]))
def resumo():
    ps=st.session_state.dados['produtos'].values()
    return (len(st.session_state.dados['produtos']),sum(p['quantidade'] for p in ps),
