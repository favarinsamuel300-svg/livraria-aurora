import json
import io
import hashlib
import hmac
import secrets
from datetime import datetime, date
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
    --texto-secundario: #B5C7D9;
    --borda: #3A5875;
    --branco: #203A56;
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
            'produtos':{},'vendas':[],'ultimo_login':None}

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
            'atualizado_em': datetime.now().astimezone().isoformat()
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
            momento = datetime.now().astimezone()
            st.session_state.dados['ultimo_login'] = {
                'nome': usuario['nome'],
                'perfil': usuario['perfil'],
                'data_hora': momento.strftime('%d/%m/%Y %H:%M')
            }
            salvar()
            st.rerun()
        else:
            st.error('Nome de usuário ou senha incorretos.')


def gerar_relatorio_pdf(vendas, inicio, fim, ultimo_login=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    estilos = getSampleStyleSheet()
    estilos.add(ParagraphStyle(name='TituloAurora', parent=estilos['Title'], textColor=colors.HexColor('#172B42'), alignment=TA_LEFT, fontSize=19, spaceAfter=6))
    estilos.add(ParagraphStyle(name='SubAurora', parent=estilos['Normal'], textColor=colors.HexColor('#5B6B7A'), fontSize=9, spaceAfter=12))
    elementos = [Paragraph('Livraria Aurora — Relatório de vendas', estilos['TituloAurora']),
                 Paragraph(f'Período: {inicio.strftime("%d/%m/%Y")} a {fim.strftime("%d/%m/%Y")}  |  Gerado em {datetime.now().strftime("%d/%m/%Y às %H:%M")}', estilos['SubAurora'])]
    if ultimo_login:
        elementos.append(Paragraph(
            f"Último login: {ultimo_login.get('nome', 'Não informado')} "
            f"({ultimo_login.get('perfil', 'perfil não informado')}) — "
            f"{ultimo_login.get('data_hora', '')}",
            estilos['SubAurora']
        ))
    faturamento = sum(float(v.get('total', 0)) for v in vendas)
    quantidade = len(vendas)
    ticket = faturamento / quantidade if quantidade else 0
    resumo_data = [['Indicador', 'Resultado'], ['Total vendido', brl(faturamento)], ['Vendas realizadas', str(quantidade)], ['Ticket médio', brl(ticket)]]
    t = Table(resumo_data, colWidths=[180, 180])
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('BACKGROUND',(0,1),(-1,-1),colors.HexColor('#29445F')),('GRID',(0,0),(-1,-1),0.4,colors.HexColor('#3A5875')),('PADDING',(0,0),(-1,-1),7)]))
    elementos += [t, Spacer(1, 14)]
    pagamentos = Counter()
    for v in vendas:
        pagamentos[v.get('pagamento_detalhe') or v.get('pagamento', 'Não informado')] += float(v.get('total', 0))
    elementos += [Spacer(1, 12), Paragraph('Vendas por forma de pagamento', estilos['Heading2'])]
    dados_pag = [['Forma de pagamento', 'Total']]
    dados_pag += [[nome, brl(valor)] for nome, valor in pagamentos.items()] or [['Nenhuma venda no período', '—']]
    tpag = Table(dados_pag, colWidths=[280, 120], repeatRows=1)
    tpag.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#3A5875')),('PADDING',(0,0),(-1,-1),6)]))
    elementos.append(tpag)
    elementos += [Spacer(1, 12), Paragraph('Histórico detalhado', estilos['Heading2'])]
    dados_vendas = [['Nº', 'Data e hora', 'Produtos', 'Pagamento', 'Total']]
    for i, v in enumerate(vendas, 1):
        itens = ', '.join(f"{x.get('quantidade', 0)}x {x.get('nome', '')}" for x in v.get('itens', []))
        pagamento = v.get('pagamento_detalhe') or v.get('pagamento', 'Não informado')
        dados_vendas.append([str(i), v.get('data', ''), Paragraph(itens, estilos['BodyText']), Paragraph(pagamento, estilos['BodyText']), brl(v.get('total', 0))])
    if len(dados_vendas) == 1:
        dados_vendas.append(['—', '—', 'Nenhuma venda no período', '—', '—'])
    tv = Table(dados_vendas, colWidths=[35, 105, 300, 150, 85], repeatRows=1)
    tv.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#3478B9')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#3A5875')),('VALIGN',(0,0),(-1,-1),'TOP'),('PADDING',(0,0),(-1,-1),6)]))
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

opcoes_menu = ['Visão geral','Produtos','Categorias','Estoque','Vendas','Histórico','Relatórios','Pagamentos']
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
    cards([('Produtos cadastrados',str(n),'Itens diferentes no catálogo'),('Unidades em estoque',str(itens),'Quantidade total disponível'),('Valor em estoque',brl(val),'Estimativa pelo preço de venda'),('Estoque baixo',str(baixos),f'Limite de alerta: {LIMITE_BAIXO} unidades')])
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
    n,itens,val,baixos,_=resumo(); cards([('Produtos',str(n),'Itens diferentes'),('Unidades',str(itens),'Total disponível'),('Valor estimado',brl(val),'Preço de venda em estoque'),('Repor',str(baixos),'Cinco unidades ou menos')])
    linhas=[{'Código':i,'Produto':p['nome'],'Categoria':p['categoria'],'Unidades':p['quantidade'],'Valor unitário':brl(p['preco']),'Valor em estoque':brl(p['preco']*p['quantidade']),'Status':'Repor' if p['quantidade']<=LIMITE_BAIXO else 'Normal'} for i,p in ordenados()]
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

elif pagina=='Vendas':
    cabecalho('Vendas','Registre uma venda e atualize o estoque automaticamente.')
    total=sum(v['total'] for v in d['vendas']); cards([('Vendas registradas',str(len(d['vendas'])),'Transações concluídas'),('Total vendido',brl(total),'Soma das vendas')])
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
            pag=st.selectbox('Forma de pagamento',d['metodos_pagamento'])
            detalhe_pagamento = pag
            numero_parcelas = 1
            valor_parcela = round(total, 2)
            if pag.strip().lower() == 'cartão de crédito':
                modalidade = st.radio('Como será o pagamento?', ['À vista', 'Parcelado'], horizontal=True, key='modalidade_cartao')
                if modalidade == 'Parcelado':
                    numero_parcelas = st.selectbox('Quantidade de parcelas', list(range(2, 13)), format_func=lambda n: f'{n}x de {brl(total/n)} sem juros')
                    valor_parcela = round(total / numero_parcelas, 2)
                    detalhe_pagamento = f'Cartão de crédito — {numero_parcelas}x de {brl(valor_parcela)} sem juros'
                else:
                    detalhe_pagamento = 'Cartão de crédito — à vista'
            a,b=st.columns(2)
            if a.button('Concluir venda',type='primary'):
                for x in st.session_state.carrinho: d['produtos'][x['pid']]['quantidade']-=x['quantidade']
                d['vendas'].append({'data':datetime.now().strftime('%d/%m/%Y %H:%M'),'itens':[{'nome':x['nome'],'quantidade':x['quantidade'],'preco':x['preco']} for x in st.session_state.carrinho],'total':round(total,2),'pagamento':pag,'pagamento_detalhe':detalhe_pagamento,'parcelas':numero_parcelas,'valor_parcela':valor_parcela,'juros':0})
                st.session_state.carrinho=[]; salvar(); st.success('Venda registrada e estoque atualizado.'); st.rerun()
            if b.button('Esvaziar carrinho'): st.session_state.carrinho=[]; st.rerun()
    else: st.caption('Nenhum item adicionado ainda.')

elif pagina=='Histórico':
    cabecalho('Histórico de vendas','Consulte as transações realizadas na livraria.')
    total=sum(v['total'] for v in d['vendas']); st.metric('Faturamento registrado',brl(total))
    linhas=[]
    for i,v in enumerate(d['vendas'],1):
        itens=', '.join(f"{x['quantidade']}x {x['nome']}" for x in v['itens'])
        linhas.append({'Nº':i,'Data e hora':v['data'],'Itens':itens,'Pagamento':v.get('pagamento_detalhe') or v['pagamento'],'Total':brl(v['total'])})
    st.dataframe(pd.DataFrame(linhas),use_container_width=True,hide_index=True)
    if not linhas: st.info('Nenhuma venda registrada até o momento.')

elif pagina=='Relatórios':
    cabecalho('Relatórios de vendas','Gere um relatório em PDF com os resultados da livraria.')
    vendas_com_data=[]
    for venda in d['vendas']:
        try:
            data_venda=datetime.strptime(venda['data'], '%d/%m/%Y %H:%M').date()
            vendas_com_data.append((data_venda, venda))
        except (KeyError, ValueError, TypeError):
            continue
    if vendas_com_data:
        primeira_data=min(x[0] for x in vendas_com_data)
        ultima_data=max(x[0] for x in vendas_com_data)
    else:
        primeira_data=ultima_data=date.today()
    c1,c2=st.columns(2)
    inicio=c1.date_input('Data inicial', value=primeira_data, key='relatorio_inicio')
    fim=c2.date_input('Data final', value=ultima_data, key='relatorio_fim')
    if inicio > fim:
        st.error('A data inicial não pode ser posterior à data final.')
    else:
        vendas_periodo=[v for data_venda,v in vendas_com_data if inicio <= data_venda <= fim]
        faturamento=sum(float(v.get('total',0)) for v in vendas_periodo)
        ticket=faturamento/len(vendas_periodo) if vendas_periodo else 0
        cards([('Total vendido',brl(faturamento),'No período selecionado'),('Vendas realizadas',str(len(vendas_periodo)),'No período selecionado'),('Ticket médio',brl(ticket),'Por venda')])
        if vendas_periodo:
            st.markdown('**Vendas incluídas no relatório**')
            st.dataframe(pd.DataFrame([{'Data':v['data'],'Pagamento':v.get('pagamento_detalhe') or v.get('pagamento','Não informado'),'Total':brl(v.get('total',0))} for v in vendas_periodo]),use_container_width=True,hide_index=True)
        else:
            st.info('Não existem vendas nesse período.')
        pdf=gerar_relatorio_pdf(vendas_periodo,inicio,fim,d.get('ultimo_login'))
        st.download_button('Baixar relatório em PDF',data=pdf,file_name=f'relatorio_vendas_{inicio:%Y%m%d}_{fim:%Y%m%d}.pdf',mime='application/pdf',type='primary')

elif pagina=='Pagamentos':
    cabecalho('Métodos de pagamento','Gerencie as formas aceitas no momento da venda.')
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

elif pagina=='Usuários':
    cabecalho('Gerenciar usuários','Cadastre contas de voluntários e consulte quem tem acesso ao sistema.')
    st.markdown('**Cadastrar voluntário**')
    with st.form('novo_voluntario', clear_on_submit=True):
        nome_voluntario = st.text_input('Nome do voluntário')
        senha_voluntario = st.text_input('Senha (mínimo de 8 caracteres)', type='password')
        confirmar_voluntario = st.text_input('Confirmar senha', type='password')
        cadastrar = st.form_submit_button('Cadastrar voluntário', type='primary')
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
            criar_usuario(nome_voluntario, senha_voluntario, 'voluntario')
            st.success('Voluntário cadastrado com sucesso.')
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
