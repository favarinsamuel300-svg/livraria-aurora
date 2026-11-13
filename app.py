import json
import io
import hashlib
import hmac
import secrets
from datetime import datetime, date, time, timezone
from zoneinfo import ZoneInfo
from collections import Counter
import pandas as pd
import streamlit as st
from supabase import create_client
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

st.set_page_config(page_title='Livraria Aurora | Gestão', page_icon='📚', layout='wide')
LIMITE_BAIXO = 5
FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")

def agora_brasilia():
    return datetime.now(timezone.utc).astimezone(FUSO_BRASILIA)

def converter_para_brasilia(valor):
    """Converte datas antigas e novas para Brasília. Datas sem fuso antigas são tratadas como UTC (padrão do Streamlit Cloud)."""
    if isinstance(valor, str):
        try:
            dt = datetime.fromisoformat(valor)
        except ValueError:
            dt = datetime.strptime(valor, '%d/%m/%Y %H:%M')
    else:
        dt = valor
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(FUSO_BRASILIA)

# Credenciais configuradas em Streamlit Cloud > App settings > Secrets
try:
    supabase = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_KEY'])
    # Chave de serviço usada somente no servidor para administrar contas.
    supabase_admin = create_client(st.secrets['SUPABASE_URL'], st.secrets['SUPABASE_SERVICE_ROLE_KEY'])
except Exception as erro:
    st.error('Confira SUPABASE_URL, SUPABASE_KEY e SUPABASE_SERVICE_ROLE_KEY em Settings > Secrets no Streamlit Cloud.')
    st.stop()

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:wght@600;700&display=swap');

:root {
    --verde-profundo: #172B42;
    --verde-principal: #3478B9;
    --verde-suave: #65A5DF;
    --verde-claro: #29445F;
    --fundo: #172B42;
    --texto: #E6F0FA;
    --texto-secundario: #C4D8EC;
    --destaque: #8EC5FF;
    --borda: #527493;
    --branco: #203A56;
}

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: var(--fundo); color: var(--texto); }
[data-testid="stSidebar"] { background: var(--verde-profundo); }
[data-testid="stSidebar"] * { color: #F4F8F4 !important; }
[data-testid="stSidebar"] [data-testid="stRadio"] label { border-radius: 8px; }

.page-title {
    font-family: 'Playfair Display', serif;
    color: #EAF4FF;
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
    color: var(--destaque);
    font-size: 30px;
    font-weight: 700;
    margin-top: 9px;
}
.metric-help { color: var(--texto-secundario); font-size: 11px; }
.section-title {
    color: #B8DCFF;
    font-size: 18px;
    font-weight: 700;
    margin: 16px 0 12px;
}

/* Botões com acabamento mais sofisticado */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {
    background: linear-gradient(135deg, #3478B9, #285F96);
    color: #FFFFFF;
    border: 1px solid #82BDF2;
    border-radius: 10px;
    padding: 0.55rem 1rem;
    font-weight: 700;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18);
    transition: all 0.18s ease-in-out;
}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {
    background: #1E4D78;
    border-color: #B8DCFF;
    color: #FFFFFF;
    transform: translateY(-1px);
}
.stButton > button:focus,
.stDownloadButton > button:focus,
.stFormSubmitButton > button:focus {
    border-color: #B8DCFF;
    box-shadow: 0 0 0 2px rgba(142, 197, 255, 0.28);
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 7px 10px;
    margin: 2px 0;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {
    background: #294D70;
    border: 1px solid #75AEE2;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #8EC5FF !important;
    font-weight: 700;
}
[data-testid="stMetric"] label,
[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    color: #C4D8EC !important;
}
[data-testid="stForm"] {
    background: var(--branco);
    border: 1px solid var(--borda);
    border-radius: 12px;
    padding: 18px;
}
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
[data-baseweb="select"] > div {
    border-radius: 9px;
    border-color: #6689AA;
}
[data-baseweb="input"] input:focus,
[data-baseweb="textarea"] textarea:focus {
    border-color: #8EC5FF;
    box-shadow: 0 0 0 1px #8EC5FF;
}
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
            'maquinas_cartao':[], 'produtos':{},'vendas':[],'caixas':[],'ultimo_login':None}

def carregar():
    try:
        resposta = (supabase.table('app_state')
                    .select('dados')
                    .eq('id', 'livraria_aurora')
                    .limit(1)
                    .execute())
        if resposta.data:
            base = iniciais()
            base.update(resposta.data[0]['dados'])
            # Compatibilidade com dados salvos antes do controle de abertura/fechamento.
            base.setdefault('caixas', [])
            base.setdefault('maquinas_cartao', [])
            return base

        # Primeiro acesso: cria o registro inicial no banco.
        base = iniciais()
        supabase.table('app_state').upsert({
            'id': 'livraria_aurora',
            'dados': base
        }).execute()
        return base
    except Exception as erro:
        st.error(f'Erro ao carregar os dados do Supabase: {erro}')
        st.stop()

def salvar():
    try:
        supabase.table('app_state').upsert({
            'id': 'livraria_aurora',
            'dados': st.session_state.dados,
            'atualizado_em': agora_brasilia().isoformat()
        }).execute()
    except Exception as erro:
        st.error(f'Não foi possível salvar no banco de dados: {erro}')
        st.stop()

def brl(v):
    return 'R$ '+f'{float(v):,.2f}'.replace(',','X').replace('.',',').replace('X','.')

def ordenados(): return sorted(st.session_state.dados['produtos'].items(),key=lambda x:int(x[0]))
def resumo():
    ps=st.session_state.dados['produtos'].values()
    return (len(st.session_state.dados['produtos']),sum(p['quantidade'] for p in ps),
            sum(p['quantidade']*p['preco'] for p in ps),
            sum(p['quantidade']<=LIMITE_BAIXO for p in ps),
            sum(v['total'] for v in st.session_state.dados['vendas']))
def cabecalho(t,s): st.markdown(f'<div class="page-title">{t}</div><div class="page-subtitle">{s}</div>',unsafe_allow_html=True)
def cards(items):
    cols=st.columns(len(items))
    for c,(a,b,d) in zip(cols,items):
        with c: st.markdown(f'<div class="metric-card"><div class="metric-label">{a}</div><div class="metric-value">{b}</div><div class="metric-help">{d}</div></div>',unsafe_allow_html=True)
def df_produtos(lista=None):
    lista=ordenados() if lista is None else lista
    return pd.DataFrame([{'Código':i,'Produto':p['nome'],'Categoria':p['categoria'],'Quantidade':p['quantidade'],'Preço':brl(p['preco']),'Situação':'Estoque baixo' if p['quantidade']<=LIMITE_BAIXO else 'Disponível'} for i,p in lista],columns=['Código','Produto','Categoria','Quantidade','Preço','Situação'])



def buscar_usuarios():
    return supabase_admin.table('app_users').select('*').execute().data or []

def gerar_hash_senha(senha, salt=None):
    salt = salt or secrets.token_hex(16)
    senha_hash = hashlib.pbkdf2_hmac(
        'sha256', senha.encode('utf-8'), bytes.fromhex(salt), 310000
    ).hex()
    return salt, senha_hash

def criar_usuario(nome, senha, perfil):
    salt, senha_hash = gerar_hash_senha(senha)
    supabase_admin.table('app_users').insert({
        'nome': nome.strip(),
        'senha_hash': senha_hash,
        'salt': salt,
        'perfil': perfil
    }).execute()

def validar_login(nome, senha):
    resultado = (supabase_admin.table('app_users')
                 .select('*').eq('nome', nome.strip()).limit(1).execute())
    if not resultado.data:
        return None
    usuario = resultado.data[0]
    _, senha_hash = gerar_hash_senha(senha, usuario['salt'])
    if hmac.compare_digest(senha_hash, usuario['senha_hash']):
        return {'id': usuario['id'], 'nome': usuario['nome'], 'perfil': usuario['perfil']}
    return None

def tela_login():
    st.markdown("<div class='page-title'>Livraria Aurora</div><div class='page-subtitle'>Acesse sua conta para entrar no sistema.</div>", unsafe_allow_html=True)
    usuarios = buscar_usuarios()

    if not usuarios:
        st.info('Primeiro acesso: crie a conta principal de administrador.')
        with st.form('configurar_admin'):
            nome_admin = st.text_input('Nome do administrador')
            senha_admin = st.text_input('Criar senha', type='password')
            confirmar_admin = st.text_input('Confirmar senha', type='password')
            criar = st.form_submit_button('Criar administrador', type='primary')
        if criar:
            if not nome_admin.strip():
                st.error('Informe o nome do administrador.')
            elif len(senha_admin) < 8:
                st.error('A senha precisa ter pelo menos 8 caracteres.')
            elif senha_admin != confirmar_admin:
                st.error('As senhas não coincidem.')
            else:
                criar_usuario(nome_admin, senha_admin, 'admin')
                st.success('Administrador criado. Agora faça login.')
                st.rerun()
        return

    with st.form('login_aurora'):
        nome = st.text_input('Nome de usuário')
        senha = st.text_input('Senha', type='password')
        entrar = st.form_submit_button('Entrar', type='primary')
    if entrar:
        usuario = validar_login(nome, senha)
        if usuario:
            st.session_state.usuario = usuario
            st.session_state.dados = carregar()
            momento = agora_brasilia()
            st.session_state.dados['ultimo_login'] = {
                'nome': usuario['nome'],
                'perfil': usuario['perfil'],
                'data_hora': momento.strftime('%d/%m/%Y %H:%M')
            }
            salvar()
            st.rerun()
        else:
            st.error('Nome de usuário ou senha incorretos.')


def gerar_relatorio_pdf(vendas, inicio, fim, ultimo_login=None, tipo_relatorio='Relatório completo', hora_inicio='00:00', hora_fim='23:59'):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name='TituloAurora', parent=estilos['Title'], textColor=colors.HexColor('#172B42'), alignment=TA_LEFT, fontSize=19, spaceAfter=6))
    estilos.add(ParagraphStyle(name='SubAurora', parent=estilos['Normal'], textColor=colors.HexColor('#40566B'), fontSize=9, spaceAfter=12))
    elementos = [
        Paragraph('Livraria Aurora — ' + tipo_relatorio, estilos['TituloAurora']),
        Paragraph(f'Período: {inicio.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")} | Horário: {hora_inicio} a {hora_fim} | Gerado em {agora_brasilia().strftime("%d/%m/%Y às %H:%M")}', estilos['SubAurora'])
    ]
    if ultimo_login:
        elementos.append(Paragraph(f"Último login: {ultimo_login.get('nome', 'Não informado')} ({ultimo_login.get('perfil', 'perfil não informado')}) — {ultimo_login.get('data_hora', '')}", estilos['SubAurora']))
    faturamento = sum(float(v.get('total', 0)) for v in vendas)
    quantidade = len(vendas)
    if tipo_relatorio in ('Relatório completo', 'Total vendido'):
        resumo_data = [['Indicador', 'Resultado'], ['Total vendido', brl(faturamento)], ['Vendas realizadas', str(quantidade)]]
        tabela = Table(resumo_data, colWidths=[180, 180])
        tabela.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#EAF2FA')),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor('#172B42')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#9CB6CE')),('PADDING',(0,0),(-1,-1),7)]))
        elementos += [tabela, Spacer(1, 14)]
    if tipo_relatorio in ('Relatório completo', 'Vendas por forma de pagamento'):
        pagamentos = Counter(v.get('pagamento', 'Não informado') for v in vendas)
        elementos.append(Paragraph('Quantidade de vendas por forma de pagamento', estilos['Heading2']))
        dados_pag = [['Forma de pagamento', 'Quantidade de vendas']]
        dados_pag += [[nome, str(qtd)] for nome, qtd in pagamentos.items()] or [['Nenhuma venda no período', '0']]
        tpag = Table(dados_pag, colWidths=[280, 140], repeatRows=1)
        tpag.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#9CB6CE')),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor('#172B42')),('PADDING',(0,0),(-1,-1),6)]))
        elementos += [tpag, Spacer(1, 12)]
    if tipo_relatorio in ('Relatório completo', 'Vendas por data', 'Detalhamento das vendas'):
        titulo = 'Vendas por data' if tipo_relatorio == 'Vendas por data' else 'Histórico detalhado'
        elementos.append(Paragraph(titulo, estilos['Heading2']))
        estilo_cabecalho_tabela = ParagraphStyle(
            name='CabecalhoTabelaAurora',
            parent=estilos['BodyText'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=9,
            textColor=colors.white,
            alignment=1,
        )
        dados_vendas = [[
            Paragraph('Nº', estilo_cabecalho_tabela),
            Paragraph('Data e hora', estilo_cabecalho_tabela),
            Paragraph('Produtos', estilo_cabecalho_tabela),
            Paragraph('Pagamento', estilo_cabecalho_tabela),
            Paragraph('Recebido em<br/>dinheiro', estilo_cabecalho_tabela),
            Paragraph('Troco', estilo_cabecalho_tabela),
            Paragraph('Total', estilo_cabecalho_tabela),
        ]]
        for i, venda in enumerate(vendas, 1):
            itens = ', '.join(f"{x.get('quantidade', 0)}x {x.get('nome', '')}" for x in venda.get('itens', []))
            pagamento = venda.get('pagamento_detalhe') or venda.get('pagamento', 'Não informado')
            dados_vendas.append([str(i), venda.get('data', ''), Paragraph(itens, estilos['BodyText']), Paragraph(pagamento, estilos['BodyText']), brl(venda.get('dinheiro_recebido', 0)) if venda.get('dinheiro_recebido') is not None else '—', brl(venda.get('troco', 0)) if venda.get('dinheiro_recebido') is not None else '—', brl(venda.get('total', 0))])
        if len(dados_vendas) == 1:
            dados_vendas.append(['—', '—', 'Nenhuma venda no período', '—', '—', '—', '—'])
        tv = Table(dados_vendas, colWidths=[30, 85, 215, 120, 105, 60, 75], repeatRows=1)
        tv.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('TEXTCOLOR',(0,1),(-1,-1),colors.HexColor('#172B42')),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#9CB6CE')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]))
        elementos.append(tv)
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

if 'usuario' not in st.session_state:
    st.title('Acesso ao sistema')
    tela_login()
    st.stop()

if 'dados' not in st.session_state:
    st.session_state.dados = carregar()
if 'carrinho' not in st.session_state:
    st.session_state.carrinho = []
d = st.session_state.dados
usuario_atual = st.session_state.usuario

opcoes_menu = ['Visão geral','Produtos','Categorias','Estoque','Caixa','Histórico','Relatórios','Pagamentos']
if usuario_atual['perfil'] == 'admin':
    opcoes_menu.append('Usuários')

with st.sidebar:
    st.markdown('# AURORA')
    st.caption('L I V R A R I A')
    st.divider()
    st.write(f"**{usuario_atual['nome']}**")
    st.caption('Administrador' if usuario_atual['perfil'] == 'admin' else 'Voluntário')
    pagina = st.radio('MENU PRINCIPAL', opcoes_menu)
    st.divider()
    if st.button('Sair da conta'):
        st.session_state.pop('usuario', None)
        st.session_state.pop('carrinho', None)
        st.rerun()
    st.caption('Sistema de gestão • Versão web 1.0')

if pagina=='Visão geral':
    cabecalho('Visão geral','Acompanhe os principais números da sua livraria.')
    n,itens,val,baixos,vendido=resumo()
    cards_base = [('Produtos cadastrados',str(n),'Itens diferentes no catálogo'),('Unidades em estoque',str(itens),'Quantidade total disponível'),('Estoque baixo',str(baixos),f'Limite de alerta: {LIMITE_BAIXO} unidades')]
    if usuario_atual['perfil'] == 'admin':
        cards_base.insert(2, ('Valor em estoque',brl(val),'Estimativa pelo preço de venda'))
    cards(cards_base)
    a,b=st.columns([2,1])
    with a:
        st.markdown('<div class="section-title">Produtos com estoque baixo</div>',unsafe_allow_html=True)
        lista=[x for x in ordenados() if x[1]['quantidade']<=LIMITE_BAIXO]
        if lista: st.dataframe(df_produtos(lista),use_container_width=True,hide_index=True)
        else: st.success('Tudo em ordem. Nenhum produto está com estoque baixo.')
    with b:
        st.markdown('<div class="section-title">Resumo de vendas</div>',unsafe_allow_html=True)
        st.metric('Total vendido',brl(vendido)); st.metric('Vendas registradas',len(d['vendas']))
        st.info('Use o menu lateral para navegar pelo sistema.')

elif pagina=='Produtos':
    cabecalho('Produtos','Cadastre, consulte, edite e remova produtos.')
    with st.expander('＋ Cadastrar novo produto'):
        with st.form('novo_produto',clear_on_submit=True):
            nome=st.text_input('Nome do produto')
            cat=st.selectbox('Categoria',d['categorias']) if d['categorias'] else None
            c1,c2=st.columns(2); qtd=c1.number_input('Quantidade',min_value=0,step=1); preco=c2.number_input('Preço (R$)',min_value=0.0,step=.5,format='%.2f')
            ok=st.form_submit_button('Salvar produto',type='primary')
            if ok:
                if not nome.strip(): st.error('Informe o nome do produto.')
                elif not cat: st.error('Cadastre uma categoria primeiro.')
                else:
                    pid=str(d['proximo_id']); d['proximo_id']+=1
                    d['produtos'][pid]={'nome':nome.strip(),'categoria':cat,'quantidade':int(qtd),'preco':round(preco,2)}
                    salvar(); st.success('Produto cadastrado.'); st.rerun()
    x,y=st.columns([2,1]); termo=x.text_input('Buscar por nome'); filtro=y.selectbox('Categoria',['Todas']+d['categorias'])
    lista=[(i,p) for i,p in ordenados() if termo.lower() in p['nome'].lower() and (filtro=='Todas' or p['categoria']==filtro)]
    st.dataframe(df_produtos(lista),use_container_width=True,hide_index=True)
    if lista:
        pid=st.selectbox('Produto para editar/remover',[i for i,_ in lista],format_func=lambda i:f"{i} — {d['produtos'][i]['nome']}")
        p=d['produtos'][pid]
        with st.expander('Editar produto selecionado'):
            with st.form('editar_produto'):
                nn=st.text_input('Nome',p['nome']); nc=st.selectbox('Categoria',d['categorias'],index=d['categorias'].index(p['categoria']))
                a,b=st.columns(2); nq=a.number_input('Quantidade',min_value=0,step=1,value=int(p['quantidade'])); np=b.number_input('Preço',min_value=0.0,step=.5,value=float(p['preco']),format='%.2f')
                if st.form_submit_button('Salvar alterações',type='primary'):
                    if not nn.strip(): st.error('O nome é obrigatório.')
                    else:
                        p.update(nome=nn.strip(),categoria=nc,quantidade=int(nq),preco=round(np,2)); salvar(); st.success('Produto atualizado.'); st.rerun()
        if st.button('Remover produto selecionado'):
            st.session_state.confirmar=pid
        if st.session_state.get('confirmar')==pid:
            st.warning(f"Confirma remover {p['nome']}?")
            a,b=st.columns(2)
            if a.button('Sim, remover',type='primary'):
                del d['produtos'][pid]; st.session_state.pop('confirmar',None); salvar(); st.rerun()
            if b.button('Cancelar'): st.session_state.pop('confirmar',None); st.rerun()
    elif not d['produtos']: st.info('Ainda não há produtos cadastrados.')

elif pagina=='Categorias':
    cabecalho('Categorias','Organize os produtos por tipo ou seção.')
    with st.form('nova_categoria',clear_on_submit=True):
        nome=st.text_input('Nome da nova categoria')
        if st.form_submit_button('＋ Criar categoria',type='primary'):
            if not nome.strip(): st.error('Digite o nome da categoria.')
            elif any(x.lower()==nome.strip().lower() for x in d['categorias']): st.error('Essa categoria já existe.')
            else: d['categorias'].append(nome.strip()); salvar(); st.success('Categoria criada.'); st.rerun()
    linhas=[]
    for c in d['categorias']:
        ps=[p for p in d['produtos'].values() if p['categoria']==c]
        linhas.append({'Categoria':c,'Produtos cadastrados':len(ps),'Unidades em estoque':sum(p['quantidade'] for p in ps)})
    st.dataframe(pd.DataFrame(linhas),use_container_width=True,hide_index=True)
    if d['categorias']:
        c=st.selectbox('Categoria para remover',d['categorias']); em_uso=any(p['categoria']==c for p in d['produtos'].values())
        if em_uso: st.warning('Não é possível remover: há produtos usando essa categoria.')
        elif st.button('Remover categoria'): d['categorias'].remove(c); salvar(); st.rerun()

elif pagina=='Estoque':
    cabecalho('Controle de estoque','Visualize quantidades, valores e itens que precisam de reposição.')
    n,itens,val,baixos,_=resumo()
    cards_estoque = [('Produtos',str(n),'Itens diferentes'),('Unidades',str(itens),'Total disponível'),('Repor',str(baixos),'Cinco unidades ou menos')]
    if usuario_atual['perfil'] == 'admin':
        cards_estoque.insert(2, ('Valor estimado',brl(val),'Preço de venda em estoque'))
    cards(cards_estoque)
    linhas=[]
    for i,p in ordenados():
        linha={'Código':i,'Produto':p['nome'],'Categoria':p['categoria'],'Unidades':p['quantidade'],'Status':'Repor' if p['quantidade']<=LIMITE_BAIXO else 'Normal'}
        if usuario_atual['perfil'] == 'admin':
            linha['Valor unitário']=brl(p['preco'])
            linha['Valor em estoque']=brl(p['preco']*p['quantidade'])
        linhas.append(linha)
    st.dataframe(pd.DataFrame(linhas),use_container_width=True,hide_index=True)
    if d['produtos']:
        st.markdown('<div class="section-title">Ajustar quantidade</div>',unsafe_allow_html=True)
        pid=st.selectbox('Produto',[i for i,_ in ordenados()],format_func=lambda i:f"{i} — {d['produtos'][i]['nome']}")
        op=st.radio('Operação',['Dar entrada','Dar saída','Definir quantidade exata'],horizontal=True); qtd=st.number_input('Quantidade',min_value=0,step=1)
        if st.button('Atualizar estoque',type='primary'):
            p=d['produtos'][pid]
            if op!='Definir quantidade exata' and qtd==0: st.error('Informe quantidade maior que zero.')
            elif op=='Dar entrada': p['quantidade']+=int(qtd)
            elif op=='Dar saída':
                if qtd>p['quantidade']: st.error('Estoque insuficiente.'); st.stop()
                p['quantidade']-=int(qtd)
            else: p['quantidade']=int(qtd)
            salvar(); st.success('Estoque atualizado.'); st.rerun()

elif pagina=='Caixa':
    cabecalho('Caixa','Abra um turno, registre as vendas e feche o caixa quando terminar.')
    caixas = d.setdefault('caixas', [])
    caixa_aberto = next((c for c in reversed(caixas) if c.get('status') == 'aberto'), None)

    if caixa_aberto is None:
        st.warning('O caixa está fechado. Abra um caixa para começar a registrar vendas.')
        with st.form('abrir_caixa_form'):
            valor_abertura = st.number_input('Dinheiro inicial para troco (R$)', min_value=0.0, value=100.0, step=10.0, format='%.2f')
            observacao_abertura = st.text_input('Identificação do turno (opcional)', placeholder='Ex.: Manhã, tarde ou noite')
            abrir = st.form_submit_button('Abrir caixa', type='primary')
        if abrir:
            agora = agora_brasilia()
            novo_caixa = {
                'id': f"CX-{agora.strftime('%Y%m%d-%H%M%S')}",
                'aberto_em': agora.isoformat(),
                'fechado_em': None,
                'valor_abertura': round(float(valor_abertura), 2),
                'observacao': observacao_abertura.strip(),
                'aberto_por': usuario_atual.get('nome', ''),
                'fechado_por': None,
                'status': 'aberto'
            }
            caixas.append(novo_caixa)
            salvar()
            st.success('Caixa aberto. As próximas vendas serão vinculadas a este turno.')
            st.rerun()
    else:
        try:
            inicio_caixa = converter_para_brasilia(caixa_aberto['aberto_em'])
            texto_inicio = inicio_caixa.strftime('%d/%m/%Y às %H:%M')
        except Exception:
            texto_inicio = caixa_aberto.get('aberto_em', '')
        vendas_turno = [v for v in d['vendas'] if v.get('caixa_id') == caixa_aberto['id']]
        total_turno = sum(float(v.get('total', 0)) for v in vendas_turno)
        cards([
            ('Status', 'ABERTO', f"Desde {texto_inicio}"),
            ('Vendas neste turno', str(len(vendas_turno)), 'Transações concluídas'),
            ('Total vendido', brl(total_turno), 'Somente este turno')
        ])
        if caixa_aberto.get('observacao'):
            st.caption(f"Turno: {caixa_aberto['observacao']}")

        with st.expander('Fechar caixa', expanded=False):
            st.write(f"**Dinheiro inicial para troco:** {brl(caixa_aberto.get('valor_abertura', 0))}")
            resumo_formas = {}
            for venda in vendas_turno:
                forma = venda.get('pagamento_detalhe', venda.get('pagamento', 'Não informado'))
                resumo_formas[forma] = resumo_formas.get(forma, 0) + float(venda.get('total', 0))
            st.write('**Resumo das vendas deste turno:**')
            if resumo_formas:
                for forma, valor in resumo_formas.items():
                    st.write(f'- {forma}: {brl(valor)}')
            else:
                st.caption('Nenhuma venda registrada neste turno.')
            st.metric('Total vendido no turno', brl(total_turno))
            confirmar_fechamento = st.checkbox('Confirmo o fechamento deste caixa.', key=f"confirmar_fechamento_{caixa_aberto['id']}")
            if st.button('Confirmar fechamento', type='primary', disabled=not confirmar_fechamento):
                agora = agora_brasilia()
                caixa_aberto.update({
                    'status': 'fechado',
                    'fechado_em': agora.isoformat(),
                    'fechado_por': usuario_atual.get('nome', ''),
                    'total_vendido': round(total_turno, 2),
                    'quantidade_vendas': len(vendas_turno)
                })
                st.session_state.carrinho = []
                salvar()
                st.success('Caixa fechado e fechamento salvo.')
                st.rerun()

        st.markdown('<div class="section-title">Adicionar itens ao carrinho</div>',unsafe_allow_html=True)
        disponiveis=[(i,p) for i,p in ordenados() if p['quantidade']>0]
        if disponiveis:
            pid=st.selectbox('Produto',[i for i,_ in disponiveis],format_func=lambda i:f"{d['produtos'][i]['nome']} — {brl(d['produtos'][i]['preco'])} (disp.: {d['produtos'][i]['quantidade']})")
            qtd=st.number_input('Quantidade',min_value=1,step=1,value=1)
            if st.button('Adicionar ao carrinho'):
                p=d['produtos'][pid]; ja=sum(x['quantidade'] for x in st.session_state.carrinho if x['pid']==pid)
                if qtd+ja>p['quantidade']: st.error('Quantidade maior que o estoque disponível.')
                else:
                    existente=next((x for x in st.session_state.carrinho if x['pid']==pid),None)
                    if existente: existente['quantidade']+=int(qtd)
                    else: st.session_state.carrinho.append({'pid':pid,'nome':p['nome'],'quantidade':int(qtd),'preco':p['preco']})
                    st.rerun()
        else: st.info('Não há produtos com estoque disponível.')
        st.markdown('<div class="section-title">Carrinho</div>',unsafe_allow_html=True)
        if st.session_state.carrinho:
            st.dataframe(pd.DataFrame([{'Produto':x['nome'],'Quantidade':x['quantidade'],'Preço unitário':brl(x['preco']),'Subtotal':brl(x['quantidade']*x['preco'])} for x in st.session_state.carrinho]),use_container_width=True,hide_index=True)
            total=sum(x['quantidade']*x['preco'] for x in st.session_state.carrinho); st.subheader(f'Total: {brl(total)}')
            if not d['metodos_pagamento']: st.warning('Cadastre um método de pagamento primeiro.')
            else:
                tipo_operacao = st.radio('Como o cliente vai pagar?', ['Pagamento único', 'Dividir entre dinheiro e cartão'], horizontal=True, key='tipo_pagamento_caixa')
                detalhe_pagamento = ''
                numero_parcelas = 1
                valor_parcela = round(total, 2)
                maquina_escolhida = None
                taxa_juros = 0.0
                dinheiro_recebido = None
                troco = 0.0
                total_cobrado = round(total, 2)
                valor_dinheiro_venda = 0.0
                valor_cartao_base = 0.0

                if tipo_operacao == 'Pagamento único':
                    pag = st.selectbox('Forma de pagamento', d['metodos_pagamento'], key='forma_pagamento_unico')
                    detalhe_pagamento = pag
                    if pag.strip().lower() in ('cartão de crédito', 'cartão de débito'):
                        maquinas = d.setdefault('maquinas_cartao', [])
                        if maquinas:
                            maquina_escolhida = st.selectbox('Máquina de cartão', maquinas, format_func=lambda m: f"{m['nome']} — juros de {float(m.get('juros', 0)):.2f}%", key='maquina_pagamento_unico')
                            taxa_juros = float(maquina_escolhida.get('juros', 0))
                            total_cobrado = round(total * (1 + taxa_juros / 100), 2)
                            if taxa_juros:
                                st.caption(f"Juros da máquina ({taxa_juros:.2f}%): {brl(total_cobrado-total)}")
                                st.metric('Total com juros', brl(total_cobrado))
                        else:
                            st.warning('Nenhuma máquina cadastrada. Peça ao administrador para cadastrar uma na página Pagamentos.')
                        if pag.strip().lower() == 'cartão de crédito':
                            modalidade = st.radio('Como será o pagamento?', ['À vista', 'Parcelado'], horizontal=True, key='modalidade_cartao')
                            if modalidade == 'Parcelado':
                                numero_parcelas = st.selectbox('Quantidade de parcelas', list(range(2, 13)), format_func=lambda n: f'{n}x de {brl(total_cobrado/n)}', key='parcelas_pagamento_unico')
                            valor_parcela = round(total_cobrado / numero_parcelas, 2)
                            detalhe_pagamento = f"{pag} — {maquina_escolhida['nome']} — {numero_parcelas}x de {brl(valor_parcela)}" if maquina_escolhida else f'{pag} — {numero_parcelas}x de {brl(valor_parcela)}'
                        else:
                            detalhe_pagamento = f"{pag} — {maquina_escolhida['nome']}" if maquina_escolhida else pag
                    elif pag.strip().lower() == 'dinheiro':
                        valor_inicial = max(100.0, float(total))
                        dinheiro_recebido = st.number_input('Dinheiro recebido do cliente (R$)', min_value=float(total), value=float(valor_inicial), step=5.0, format='%.2f', key='dinheiro_recebido_caixa')
                        troco = round(float(dinheiro_recebido) - float(total), 2)
                        valor_dinheiro_venda = round(float(total), 2)
                        st.metric('Troco a devolver', brl(troco))
                    else:
                        detalhe_pagamento = pag

                else:
                    st.caption('Informe quanto será pago em dinheiro. O restante será cobrado no cartão.')
                    valor_dinheiro_venda = st.number_input('Parte da venda paga em dinheiro (R$)', min_value=0.01, max_value=float(total - 0.01), value=round(float(total) / 2, 2), step=5.0, format='%.2f', key='parte_dinheiro_dividida')
                    valor_cartao_base = round(float(total) - float(valor_dinheiro_venda), 2)
                    pag_cartao = st.selectbox('Forma do restante no cartão', ['Cartão de débito', 'Cartão de crédito'], key='cartao_pagamento_dividido')
                    maquinas = d.setdefault('maquinas_cartao', [])
                    if maquinas:
                        maquina_escolhida = st.selectbox('Máquina de cartão', maquinas, format_func=lambda m: f"{m['nome']} — juros de {float(m.get('juros', 0)):.2f}%", key='maquina_pagamento_dividido')
                        taxa_juros = float(maquina_escolhida.get('juros', 0))
                    else:
                        st.warning('Nenhuma máquina cadastrada. Peça ao administrador para cadastrar uma na página Pagamentos.')
                    if pag_cartao == 'Cartão de crédito':
                        modalidade_dividida = st.radio('Parcelamento da parte no cartão', ['À vista', 'Parcelado'], horizontal=True, key='modalidade_cartao_dividido')
                        if modalidade_dividida == 'Parcelado':
                            numero_parcelas = st.selectbox('Quantidade de parcelas', list(range(2, 13)), format_func=lambda n: f'{n}x', key='parcelas_cartao_dividido')
                    total_cartao = round(valor_cartao_base * (1 + taxa_juros / 100), 2)
                    total_cobrado = round(float(valor_dinheiro_venda) + total_cartao, 2)
                    valor_parcela = round(total_cartao / numero_parcelas, 2)
                    dinheiro_recebido = round(float(valor_dinheiro_venda), 2)
                    troco = 0.0
                    detalhe_maquina = maquina_escolhida['nome'] if maquina_escolhida else 'Máquina não selecionada'
                    detalhe_pagamento = f"Dinheiro: {brl(valor_dinheiro_venda)} + {pag_cartao}: {brl(total_cartao)} — {detalhe_maquina}"
                    if pag_cartao == 'Cartão de crédito':
                        detalhe_pagamento += f" — {numero_parcelas}x de {brl(valor_parcela)}"
                    st.write(f"**Parte no cartão antes dos juros:** {brl(valor_cartao_base)}")
                    if taxa_juros:
                        st.caption(f"Juros ({taxa_juros:.2f}%) aplicados somente à parte do cartão: {brl(total_cartao - valor_cartao_base)}")
                    st.metric('Total final da venda', brl(total_cobrado))

                a,b=st.columns(2)
                if a.button('Concluir venda',type='primary'):
                    pagamento_registro = pag if tipo_operacao == 'Pagamento único' else 'Pagamento dividido'
                    if tipo_operacao == 'Pagamento único' and pag.strip().lower() == 'dinheiro' and dinheiro_recebido is not None and dinheiro_recebido < total:
                        st.error('O valor recebido não pode ser menor que o total da venda.')
                    elif (tipo_operacao == 'Pagamento único' and pag.strip().lower() in ('cartão de crédito', 'cartão de débito') or tipo_operacao == 'Dividir entre dinheiro e cartão') and not maquina_escolhida:
                        st.error('Cadastre e selecione uma máquina de cartão antes de concluir a venda.')
                    else:
                        for x in st.session_state.carrinho: d['produtos'][x['pid']]['quantidade']-=x['quantidade']
                        d['vendas'].append({'caixa_id':caixa_aberto['id'],'data':agora_brasilia().strftime('%d/%m/%Y %H:%M'),'itens':[{'nome':x['nome'],'quantidade':x['quantidade'],'preco':x['preco']} for x in st.session_state.carrinho],'subtotal':round(total,2),'total':total_cobrado,'pagamento':pagamento_registro,'pagamento_detalhe':detalhe_pagamento,'maquina_cartao':maquina_escolhida['nome'] if maquina_escolhida else None,'parcelas':numero_parcelas,'valor_parcela':valor_parcela,'juros':round(total_cobrado-total,2),'taxa_juros':taxa_juros,'dinheiro_recebido':round(float(dinheiro_recebido),2) if dinheiro_recebido is not None else None,'valor_dinheiro_venda':round(float(valor_dinheiro_venda),2),'valor_cartao':round(float(valor_cartao_base),2) if tipo_operacao == 'Dividir entre dinheiro e cartão' else (round(float(total),2) if pag.strip().lower() in ('cartão de crédito','cartão de débito') else 0.0),'troco':troco})
                        st.session_state.carrinho=[]; salvar(); st.success('Venda registrada e estoque atualizado.'); st.rerun()
                if b.button('Esvaziar carrinho'): st.session_state.carrinho=[]; st.rerun()

        else: st.caption('Nenhum item adicionado ainda.')

    caixas_fechados = [c for c in caixas if c.get('status') == 'fechado']
    if caixas_fechados:
        st.markdown('<div class="section-title">Fechamentos anteriores</div>',unsafe_allow_html=True)
        linhas_fechamentos = []
        for c in reversed(caixas_fechados):
            try:
                abertura_txt = converter_para_brasilia(c.get('aberto_em', '')).strftime('%d/%m/%Y %H:%M')
            except Exception:
                abertura_txt = c.get('aberto_em', '')
            try:
                fechamento_txt = converter_para_brasilia(c.get('fechado_em', '')).strftime('%d/%m/%Y %H:%M')
            except Exception:
                fechamento_txt = c.get('fechado_em', '')
            linhas_fechamentos.append({
                'Turno': c.get('observacao') or c.get('id', 'Caixa'),
                'Abertura': abertura_txt,
                'Fechamento': fechamento_txt,
                'Fundo inicial': brl(c.get('valor_abertura', 0)),
                'Total vendido': brl(c.get('total_vendido', 0)),
            })
        st.dataframe(pd.DataFrame(linhas_fechamentos), use_container_width=True, hide_index=True)

elif pagina=='Histórico':
    cabecalho('Histórico de vendas','Consulte as transações realizadas na livraria.')
    total=sum(float(v.get('total', 0)) for v in d['vendas'])
    st.metric('Faturamento registrado',brl(total))
    linhas=[]
    for i,v in enumerate(d['vendas'],1):
        itens=', '.join(f"{x.get('quantidade', 0)}x {x.get('nome', '')}" for x in v.get('itens', []))
        linhas.append({'Nº':i,'Data e hora':v.get('data',''),'Itens':itens,
                       'Pagamento':v.get('pagamento_detalhe') or v.get('pagamento','Não informado'),
                       'Total':brl(v.get('total',0))})
    if linhas:
        st.dataframe(pd.DataFrame(linhas),use_container_width=True,hide_index=True)
    else:
        st.info('Nenhuma venda registrada até o momento.')

    if usuario_atual['perfil'] == 'admin':
        st.divider()
        st.markdown('### Limpar histórico de vendas')
        st.warning('A exclusão remove os registros dos relatórios e do histórico. As quantidades do estoque não serão alteradas automaticamente.')
        modo_limpeza = st.radio('O que deseja apagar?', ['Vendas até uma data', 'Todas as vendas'], horizontal=True, key='modo_limpeza_historico')
        data_limite = None
        if modo_limpeza == 'Vendas até uma data':
            datas_validas = []
            for venda in d['vendas']:
                try:
                    datas_validas.append(converter_para_brasilia(venda['data']).date())
                except (KeyError, ValueError, TypeError):
                    pass
            valor_padrao = max(datas_validas) if datas_validas else date.today()
            data_limite = st.date_input('Apagar vendas realizadas até', value=valor_padrao, key='data_limite_exclusao')
        confirmar_limpeza = st.checkbox('Confirmo que desejo excluir esses registros permanentemente.', key='confirmar_limpeza_vendas')
        if st.button('Excluir histórico selecionado', type='primary', key='btn_excluir_historico'):
            if not confirmar_limpeza:
                st.error('Marque a confirmação antes de excluir.')
            elif modo_limpeza == 'Todas as vendas':
                d['vendas'] = []
                salvar()
                st.success('Todo o histórico de vendas foi apagado.')
                st.rerun()
            else:
                vendas_restantes = []
                removidas = 0
                for venda in d['vendas']:
                    try:
                        data_venda = converter_para_brasilia(venda['data']).date()
                    except (KeyError, ValueError, TypeError):
                        vendas_restantes.append(venda)
                        continue
                    if data_venda <= data_limite:
                        removidas += 1
                    else:
                        vendas_restantes.append(venda)
                d['vendas'] = vendas_restantes
                salvar()
                st.success(f'{removidas} venda(s) removida(s) do histórico.')
                st.rerun()

elif pagina=='Relatórios':
    cabecalho('Relatórios de vendas','Escolha o tipo de relatório, as datas e o intervalo de horários.')
    vendas_com_data=[]
    for venda in d['vendas']:
        try:
            data_hora_venda=converter_para_brasilia(venda['data'])
            vendas_com_data.append((data_hora_venda, venda))
        except (KeyError, ValueError, TypeError):
            continue
    if vendas_com_data:
        primeira_data=min(x[0].date() for x in vendas_com_data)
        ultima_data=max(x[0].date() for x in vendas_com_data)
    else:
        primeira_data=ultima_data=date.today()
    tipo_relatorio = st.selectbox('Tipo de relatório', ['Relatório completo', 'Vendas por data', 'Total vendido', 'Vendas por forma de pagamento', 'Detalhamento das vendas'])
    c1,c2=st.columns(2)
    inicio=c1.date_input('Data inicial', value=primeira_data, key='relatorio_inicio')
    fim=c2.date_input('Data final', value=ultima_data, key='relatorio_fim')
    h1,h2=st.columns(2)
    hora_inicio=h1.time_input('Horário inicial', value=time(0,0), key='relatorio_hora_inicio')
    hora_fim=h2.time_input('Horário final', value=time(23,59), key='relatorio_hora_fim')
    if inicio > fim:
        st.error('A data inicial não pode ser posterior à data final.')
    elif hora_inicio > hora_fim:
        st.error('O horário inicial não pode ser posterior ao horário final. Para consultar um período noturno que atravesse a meia-noite, selecione as datas correspondentes.')
    else:
        vendas_periodo=[v for momento,v in vendas_com_data if inicio <= momento.date() <= fim and hora_inicio <= momento.time() <= hora_fim]
        faturamento=sum(float(v.get('total',0)) for v in vendas_periodo)
        if tipo_relatorio in ('Relatório completo', 'Total vendido'):
            cards([('Total vendido',brl(faturamento),'No período selecionado'),('Vendas realizadas',str(len(vendas_periodo)),'No período selecionado')])
        if tipo_relatorio in ('Relatório completo', 'Vendas por forma de pagamento'):
            st.markdown('**Quantidade de vendas por forma de pagamento**')
            pagamentos_periodo = Counter(v.get('pagamento','Não informado') for v in vendas_periodo)
            df_pagamentos = pd.DataFrame([{'Forma de pagamento':k,'Quantidade de vendas':v} for k,v in pagamentos_periodo.items()])
            if not df_pagamentos.empty:
                st.dataframe(df_pagamentos,use_container_width=True,hide_index=True)
            else:
                st.info('Não existem vendas nesse período.')
        if tipo_relatorio in ('Relatório completo', 'Vendas por data', 'Detalhamento das vendas'):
            st.markdown('**Vendas incluídas no relatório**')
            tabela_vendas = pd.DataFrame([{'Data e hora':v.get('data',''),'Produtos':', '.join(f"{x.get('quantidade',0)}x {x.get('nome','')}" for x in v.get('itens',[])),'Pagamento':v.get('pagamento_detalhe') or v.get('pagamento','Não informado'),'Recebido em dinheiro':brl(v.get('dinheiro_recebido')) if v.get('dinheiro_recebido') is not None else '—','Troco':brl(v.get('troco',0)) if v.get('dinheiro_recebido') is not None else '—','Total':brl(v.get('total',0))} for v in vendas_periodo])
            if not tabela_vendas.empty:
                st.dataframe(tabela_vendas,use_container_width=True,hide_index=True)
            else:
                st.info('Não existem vendas nesse período.')
        if tipo_relatorio == 'Vendas por data':
            st.caption('As vendas estão organizadas cronologicamente conforme as datas e horários registrados.')
        pdf=gerar_relatorio_pdf(vendas_periodo,inicio,fim,d.get('ultimo_login'),tipo_relatorio,hora_inicio.strftime('%H:%M'),hora_fim.strftime('%H:%M'))
        st.download_button('Baixar relatório em PDF',data=pdf,file_name=f'relatorio_{tipo_relatorio.lower().replace(" ","_")}_{inicio:%Y%m%d}_{fim:%Y%m%d}.pdf',mime='application/pdf',type='primary')

elif pagina=='Pagamentos':
    cabecalho('Métodos de pagamento','Gerencie as formas aceitas e as máquinas de cartão.')
    if usuario_atual['perfil'] == 'admin':
        with st.form('novo_pagamento',clear_on_submit=True):
            nome=st.text_input('Nome do método')
            if st.form_submit_button('＋ Adicionar método',type='primary'):
                if not nome.strip(): st.error('Digite o nome do método.')
                elif any(x.lower()==nome.strip().lower() for x in d['metodos_pagamento']): st.error('Esse método já existe.')
                else: d['metodos_pagamento'].append(nome.strip()); salvar(); st.success('Método adicionado.'); st.rerun()
        st.dataframe(pd.DataFrame({'Métodos cadastrados':d['metodos_pagamento']}),use_container_width=True,hide_index=True)
        if d['metodos_pagamento']:
            m=st.selectbox('Método para remover',d['metodos_pagamento'])
            if st.button('Remover método selecionado'): d['metodos_pagamento'].remove(m); salvar(); st.rerun()
        st.divider()
        st.markdown('### Máquinas de cartão')
        with st.form('nova_maquina_cartao', clear_on_submit=True):
            nome_maquina=st.text_input('Nome da máquina',placeholder='Ex.: Máquina amarela')
            juros_maquina=st.number_input('Juros da máquina (%)',min_value=0.0,max_value=100.0,value=0.0,step=0.5,format='%.2f')
            cadastrar_maquina=st.form_submit_button('＋ Cadastrar máquina',type='primary')
        if cadastrar_maquina:
            maquinas=d.setdefault('maquinas_cartao', [])
            if not nome_maquina.strip(): st.error('Informe o nome da máquina.')
            elif any(m['nome'].strip().lower()==nome_maquina.strip().lower() for m in maquinas): st.error('Já existe uma máquina com esse nome.')
            else:
                maquinas.append({'nome':nome_maquina.strip(),'juros':round(float(juros_maquina),2)})
                salvar(); st.success('Máquina cadastrada.'); st.rerun()
        maquinas=d.setdefault('maquinas_cartao', [])
        if maquinas:
            st.dataframe(pd.DataFrame([{'Máquina':m['nome'],'Juros (%)':f"{float(m.get('juros',0)):.2f}%"} for m in maquinas]),use_container_width=True,hide_index=True)
            maquina_editar=st.selectbox('Máquina para alterar ou remover',maquinas,format_func=lambda m:m['nome'],key='maquina_editar')
            with st.form('editar_maquina_cartao'):
                novo_nome_maquina=st.text_input('Nome',value=maquina_editar['nome'])
                novos_juros=st.number_input('Juros (%)',min_value=0.0,max_value=100.0,value=float(maquina_editar.get('juros',0)),step=0.5,format='%.2f')
                salvar_maquina=st.form_submit_button('Salvar alterações')
            if salvar_maquina:
                if not novo_nome_maquina.strip(): st.error('O nome não pode ficar vazio.')
                elif any(m is not maquina_editar and m['nome'].strip().lower()==novo_nome_maquina.strip().lower() for m in maquinas): st.error('Já existe uma máquina com esse nome.')
                else:
                    maquina_editar.update({'nome':novo_nome_maquina.strip(),'juros':round(float(novos_juros),2)})
                    salvar(); st.success('Máquina atualizada.'); st.rerun()
            if st.button('Remover máquina selecionada',key='remover_maquina'):
                maquinas.remove(maquina_editar); salvar(); st.rerun()
        else:
            st.info('Nenhuma máquina cadastrada ainda.')
    else:
        st.info('Somente administradores podem gerenciar formas de pagamento e máquinas de cartão.')

elif pagina=='Usuários':
    cabecalho('Gerenciar usuários','Cadastre administradores e voluntários e consulte quem tem acesso ao sistema.')
    st.markdown('**Cadastrar usuário**')
    with st.form('novo_voluntario', clear_on_submit=True):
        nome_voluntario = st.text_input('Nome da pessoa')
        perfil_novo = st.selectbox('Tipo de acesso', ['Voluntário', 'Administrador'])
        senha_voluntario = st.text_input('Senha (mínimo de 8 caracteres)', type='password')
        confirmar_voluntario = st.text_input('Confirmar senha', type='password')
        cadastrar = st.form_submit_button('Cadastrar usuário', type='primary')
    if cadastrar:
        nomes_existentes = [u['nome'].strip().lower() for u in buscar_usuarios()]
        if not nome_voluntario.strip():
            st.error('Informe o nome do voluntário.')
        elif nome_voluntario.strip().lower() in nomes_existentes:
            st.error('Já existe um usuário com esse nome.')
        elif len(senha_voluntario) < 8:
            st.error('A senha precisa ter pelo menos 8 caracteres.')
        elif senha_voluntario != confirmar_voluntario:
            st.error('As senhas não coincidem.')
        else:
            perfil_banco = 'admin' if perfil_novo == 'Administrador' else 'voluntario'
            criar_usuario(nome_voluntario, senha_voluntario, perfil_banco)
            st.success(f'{perfil_novo} cadastrado com sucesso.')
            st.rerun()

    st.divider()
    st.markdown('**Usuários cadastrados**')
    usuarios = buscar_usuarios()
    tabela_usuarios = pd.DataFrame([
        {'Nome': u['nome'], 'Perfil': 'Administrador' if u['perfil'] == 'admin' else 'Voluntário'}
        for u in usuarios
    ])
    st.dataframe(tabela_usuarios, use_container_width=True, hide_index=True)

    voluntarios = [u for u in usuarios if u['perfil'] == 'voluntario']
    if voluntarios:
        st.markdown('**Remover acesso de um voluntário**')
        usuario_remover = st.selectbox(
            'Selecione o voluntário',
            voluntarios,
            format_func=lambda u: u['nome'],
            key='usuario_remover'
        )
        if st.button('Remover voluntário selecionado'):
            supabase_admin.table('app_users').delete().eq('id', usuario_remover['id']).execute()
            st.success('Acesso do voluntário removido.')
            st.rerun()
