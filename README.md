# Livraria Aurora — versão web

Sistema de controle de estoque para livraria, feito com Python e Streamlit.

## Funcionalidades
- Painel com indicadores de estoque e vendas
- Cadastro, edição, busca e remoção de produtos
- Gerenciamento de categorias
- Entrada, saída e ajuste de estoque
- Carrinho e registro de vendas com baixa automática
- Histórico de vendas
- Cadastro e remoção de métodos de pagamento

## Executar no computador
1. Instale Python 3.10 ou superior.
2. Abra o terminal nesta pasta.
3. Instale as dependências: `pip install -r requirements.txt`
4. Inicie: `streamlit run app.py`

## Publicar com GitHub + Streamlit Community Cloud
1. Crie um repositório no GitHub.
2. Envie `app.py` e `requirements.txt` para a raiz do repositório.
3. Acesse https://share.streamlit.io/ e conecte sua conta GitHub.
4. Selecione o repositório, a branch e o arquivo `app.py`.
5. Clique em Deploy.

## Persistência dos dados
Localmente, os dados são salvos em `estoque_livraria.json` ao lado do `app.py`. Em hospedagens gratuitas com armazenamento efêmero, esse arquivo pode ser perdido quando a aplicação reinicia ou é recriada. Para manter dados importantes em produção, conecte um banco de dados persistente, como PostgreSQL ou Supabase.
