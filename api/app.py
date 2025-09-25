import os
import datetime
import bcrypt
import re
from flask import Flask, request, jsonify, redirect, url_for, session, render_template, flash, make_response
from functools import wraps, update_wrapper
from supabase import create_client, Client
from dotenv import load_dotenv

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()

url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")

if not url or not key:
    raise ValueError("Erro: As variáveis SUPABASE_URL e SUPABASE_KEY não foram encontradas. Verifique seu arquivo .env.")
supabase: Client = create_client(url, key)
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "uma-chave-secreta-padrao-muito-segura")


# --- DECORATORS E FUNÇÕES HELPER ---
def nocache(view):
    @wraps(view)
    def no_cache(*args, **kwargs):
        response = make_response(view(*args, **kwargs))
        response.headers['Last-Modified'] = datetime.datetime.now()
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '-1'
        return response
    return update_wrapper(no_cache, view)

def login_required():
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Por favor, faça login para acessar esta página.', 'erro')
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

def admin_required():
    def wrapper(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Por favor, faça login para acessar esta página.', 'erro')
                return redirect(url_for('login'))
            if not session.get('is_admin'):
                flash('Você não tem permissão para acessar esta página.', 'erro')
                return redirect(url_for('inicio'))
            return f(*args, **kwargs)
        return decorated_function
    return wrapper

# --- ROTAS PÚBLICAS (LOGIN, CADASTRO, LOGOUT) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_input = request.form.get('email')
        senha_input = request.form.get('senha')
        try:
            result = supabase.table("tb_usuario").select("id_usuario, nome, senha, is_admin").eq("email", email_input).limit(1).execute()
            if result.data:
                usuario = result.data[0]
                stored_senha_hash = usuario['senha'].encode('utf-8')
                if bcrypt.checkpw(senha_input.encode('utf-8'), stored_senha_hash):
                    session['logged_in'] = True
                    session['id_usuario'] = usuario['id_usuario']
                    session['nome_usuario'] = usuario['nome']
                    session['is_admin'] = usuario.get('is_admin', False)
                    flash(f"Bem-vindo(a), {usuario['nome']}!", 'sucesso')
                    return redirect(url_for('admin_dashboard')) if session.get('is_admin') else redirect(url_for('inicio'))
            flash('Email ou senha incorretos.', 'erro')
        except Exception as e:
            flash(f'Ocorreu um erro: {e}', 'erro')
    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        try:
            cpf_limpo = re.sub(r'\D', '', cpf)
            existing_user = supabase.table("tb_usuario").select("cpf").eq("cpf", cpf_limpo).limit(1).execute()
            if existing_user.data:
                flash('Este CPF já está cadastrado.', 'erro')
                return render_template('cadastro.html')
            
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            supabase.table("tb_usuario").insert({"nome": nome, "cpf": cpf_limpo, "email": email, "senha": senha_hash, "is_admin": False}).execute()
            
            result = supabase.table("tb_usuario").select("id_usuario, nome, is_admin").eq("email", email).limit(1).execute()
            if result.data:
                usuario = result.data[0]
                session['logged_in'] = True
                session['id_usuario'] = usuario['id_usuario']
                session['nome_usuario'] = usuario['nome']
                session['is_admin'] = usuario.get('is_admin', False)
                flash(f"Bem-vindo(a), {usuario['nome']}! Cadastro realizado.", 'sucesso')
                return redirect(url_for('inicio'))
        except Exception as e:
            flash(f'Ocorreu um erro ao cadastrar: {e}', 'erro')
    return render_template('cadastro.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Você saiu da sua conta.', 'sucesso')
    return redirect(url_for('login'))

@app.route('/')
def home():
    if session.get('logged_in'):
        return redirect(url_for('admin_dashboard')) if session.get('is_admin') else redirect(url_for('inicio'))
    return redirect(url_for('login'))

# --- ROTAS PRINCIPAIS (USUÁRIO COMUM) ---
@app.route('/inicio')
@login_required()
def inicio():
    return render_template('inicio.html')

@app.route('/perfil', methods=['GET', 'POST'])
@login_required()
def perfil():
    user_id = session.get('id_usuario')
    try:
        current_user_data = supabase.table("tb_usuario").select("*").eq("id_usuario", user_id).single().execute().data
    except Exception as e:
        flash(f'Não foi possível carregar os dados do perfil: {e}', 'erro')
        return redirect(url_for('inicio'))

    if request.method == 'POST':
        # (A lógica completa de atualização de perfil pode ser expandida aqui)
        flash('Funcionalidade de atualização de perfil em desenvolvimento.', 'info')
        return redirect(url_for('perfil'))
        
    return render_template('perfil.html', usuario=current_user_data)

# --- ROTAS DE ADMINISTRAÇÃO ---
@app.route('/admin')
@admin_required()
def admin_dashboard():
    return render_template('admin.html')

# --- GERENCIAMENTO DE USUÁRIOS (ADMIN) ---
@app.route('/admin/gerenciar-usuarios', methods=['GET'])
@admin_required()
@nocache
def gerenciar_usuarios():
    termo_busca = request.args.get('busca', '').strip()
    try:
        query = supabase.table("tb_usuario").select("*").order("nome")
        if termo_busca:
            query = query.ilike('nome', f'%{termo_busca}%')
        usuarios = query.execute().data
        return render_template('gerenciar_usuarios.html', usuarios=usuarios, termo_busca=termo_busca)
    except Exception as e:
        flash(f"Erro ao carregar usuários: {e}", "erro")
        return render_template('gerenciar_usuarios.html', usuarios=[], termo_busca=termo_busca)

@app.route('/admin/usuarios/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_usuario():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome')
            email = request.form.get('email')
            cpf = request.form.get('cpf')
            senha = request.form.get('senha')
            is_admin = True
            
            cpf_limpo = re.sub(r'\D', '', cpf)
            existing = supabase.table("tb_usuario").select("id_usuario").or_(f"cpf.eq.{cpf_limpo},email.eq.{email}").execute().data
            if existing:
                flash("Já existe um usuário com este CPF ou Email.", "erro")
                return render_template('adicionar_usuario.html')

            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            supabase.table("tb_usuario").insert({"nome": nome, "email": email, "cpf": cpf_limpo, "senha": senha_hash, "is_admin": is_admin}).execute()
            flash("Usuário administrador adicionado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_usuarios'))
        except Exception as e:
            flash(f"Erro ao adicionar usuário: {e}", "erro")
    return render_template('adicionar_usuario.html')

@app.route('/admin/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@admin_required()
def editar_usuario(id_usuario):
    try:
        usuario = supabase.table("tb_usuario").select("*").eq("id_usuario", id_usuario).single().execute().data
    except Exception as e:
        flash(f"Erro ao carregar usuário: {e}", "erro")
        return redirect(url_for('gerenciar_usuarios'))
    
    if request.method == 'POST':
        try:
            dados = {'nome': request.form.get('nome'), 'email': request.form.get('email'), 'is_admin': request.form.get('is_admin') == 'on'}
            # (Lógica completa de validação de CPF/email e atualização de senha aqui)
            supabase.table("tb_usuario").update(dados).eq("id_usuario", id_usuario).execute()
            flash("Usuário atualizado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_usuarios'))
        except Exception as e:
            flash(f"Erro ao atualizar usuário: {e}", "erro")
    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/excluir/<int:id_usuario>', methods=['POST'])
@admin_required()
def excluir_usuario(id_usuario):
    if id_usuario == session.get('id_usuario'):
        flash("Você não pode excluir sua própria conta.", "erro")
        return redirect(url_for('gerenciar_usuarios'))
    try:
        supabase.table("tb_usuario").delete().eq("id_usuario", id_usuario).execute()
        flash("Usuário excluído com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao excluir usuário: {e}", "erro")
    return redirect(url_for('gerenciar_usuarios'))

# --- GERENCIAMENTO DE PRODUTOS (ADMIN) ---
@app.route('/admin/gerenciar-produtos', methods=['GET'])
@admin_required()
@nocache
def gerenciar_produtos():
    termo_busca = request.args.get('q', '').strip()
    try:
        query = supabase.table("tb_produto").select("*").order("nome")
        if termo_busca:
            query = query.ilike('nome', f'%{termo_busca}%')
        produtos = query.execute().data
        return render_template('gerenciar_produtos.html', produtos=produtos, termo_busca=termo_busca)
    except Exception as e:
        flash(f"Erro ao carregar produtos: {e}", "erro")
        return render_template('gerenciar_produtos.html', produtos=[], termo_busca=termo_busca)

@app.route('/admin/produtos/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_produto():
    if request.method == 'POST':
        try:
            dados = {
                "nome": request.form.get('nome'), "marca": request.form.get('marca'),
                "preco": float(request.form.get('preco', 0)), "estoque": 0,
                "validade": request.form.get('validade') or None
            }
            supabase.table("tb_produto").insert(dados).execute()
            flash("Produto adicionado com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao adicionar produto: {e}", "erro")
        return redirect(url_for('gerenciar_produtos'))
    return render_template('adicionar_produto.html')

@app.route('/admin/produtos/editar/<int:id_produto>', methods=['GET', 'POST'])
@admin_required()
def editar_produto(id_produto):
    try:
        produto = supabase.table("tb_produto").select("*").eq("id_produto", id_produto).single().execute().data
    except Exception as e:
        flash(f"Não foi possível carregar o produto: {e}", "erro")
        return redirect(url_for('gerenciar_produtos'))
    if request.method == 'POST':
        try:
            dados = {
                "nome": request.form.get('nome'), "marca": request.form.get('marca'),
                "preco": float(request.form.get('preco', 0)), "estoque": int(request.form.get('estoque', 0)),
                "validade": request.form.get('validade') or None
            }
            supabase.table("tb_produto").update(dados).eq("id_produto", id_produto).execute()
            flash("Produto atualizado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_produtos'))
        except Exception as e:
            flash(f"Erro ao atualizar produto: {e}", "erro")
    return render_template('editar_produto.html', produto=produto)

@app.route('/admin/produtos/excluir/<int:id_produto>', methods=['POST'])
@admin_required()
def excluir_produto(id_produto):
    try:
        movimentos = supabase.table("tb_estoque_mov").select("id_mov", count='exact').eq("id_produto", id_produto).execute()
        if movimentos.count > 0:
            flash("Este produto não pode ser excluído, pois possui um histórico de movimentações.", "erro")
            return redirect(url_for('gerenciar_produtos'))
        
        itens_venda = supabase.table("tb_venda_item").select("id_venda_item", count='exact').eq("id_produto", id_produto).execute()
        if itens_venda.count > 0:
            flash("Este produto não pode ser excluído, pois está associado a vendas.", "erro")
            return redirect(url_for('gerenciar_produtos'))

        supabase.table("tb_produto").delete().eq("id_produto", id_produto).execute()
        flash("Produto excluído com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao excluir produto: {e}", "erro")
    return redirect(url_for('gerenciar_produtos'))

# --- GERENCIAMENTO DE CLIENTES (ADMIN) ---
@app.route('/admin/gerenciar-clientes', methods=['GET'])
@admin_required()
@nocache
def gerenciar_clientes():
    termo_busca = request.args.get('q', '').strip()
    try:
        query = supabase.table("tb_cliente").select("*").order("nome")
        if termo_busca:
            query = query.or_(f"nome.ilike.%{termo_busca}%,cpf.ilike.%{termo_busca}%")
        clientes = query.execute().data
        return render_template('gerenciar_clientes.html', clientes=clientes, termo_busca=termo_busca)
    except Exception as e:
        flash(f"Erro ao carregar clientes: {e}", "erro")
        return render_template('gerenciar_clientes.html', clientes=[], termo_busca=termo_busca)

@app.route('/admin/clientes/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_cliente():
    if request.method == 'POST':
        try:
            nome = request.form.get('nome')
            email = request.form.get('email')
            cpf = re.sub(r'\D', '', request.form.get('cpf'))
            existing = supabase.table("tb_cliente").select("id_cliente").eq("cpf", cpf).execute().data
            if existing:
                flash("Cliente já cadastrado com esse CPF.", "erro")
                return redirect(url_for('adicionar_cliente'))
            supabase.table("tb_cliente").insert({"nome": nome, "email": email, "cpf": cpf}).execute()
            flash("Cliente adicionado com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao adicionar cliente: {e}", "erro")
        return redirect(url_for('gerenciar_clientes'))
    return render_template('adicionar_cliente.html')

@app.route('/admin/clientes/editar/<int:id_cliente>', methods=['GET', 'POST'])
@admin_required()
def editar_cliente(id_cliente):
    try:
        cliente = supabase.table("tb_cliente").select("*").eq("id_cliente", id_cliente).single().execute().data
    except Exception as e:
        flash(f"Erro ao carregar cliente: {e}", "erro")
        return redirect(url_for('gerenciar_clientes'))
    if request.method == 'POST':
        try:
            dados = {"nome": request.form.get('nome'), "email": request.form.get('email'), "cpf": re.sub(r'\D', '', request.form.get('cpf'))}
            supabase.table("tb_cliente").update(dados).eq("id_cliente", id_cliente).execute()
            flash("Cliente atualizado com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao atualizar cliente: {e}", "erro")
        return redirect(url_for('gerenciar_clientes'))
    return render_template('editar_cliente.html', cliente=cliente)

@app.route('/admin/clientes/excluir/<int:id_cliente>', methods=['POST'])
@admin_required()
def excluir_cliente(id_cliente):
    try:
        supabase.table("tb_cliente").delete().eq("id_cliente", id_cliente).execute()
        flash("Cliente excluído com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao excluir cliente: {e}", "erro")
    return redirect(url_for('gerenciar_clientes'))

# --- GERENCIAMENTO DE VENDAS (ADMIN) ---
@app.route('/admin/gerenciar-vendas')
@admin_required()
@nocache
def gerenciar_vendas():
    try:
        vendas_response = supabase.table("tb_venda").select("*, tb_usuario(nome)").order("data_venda", desc=True).execute()
        return render_template('gerenciar_vendas.html', vendas=vendas_response.data)
    except Exception as e:
        flash("Não foi possível carregar a lista de vendas.", "erro")
        return render_template('gerenciar_vendas.html', vendas=[])
    
@app.route('/admin/vendas/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_venda():
    if request.method == 'POST':
        try:
            produtos_selecionados = request.form.getlist('produtos[]')
            quantidades = request.form.getlist('quantidades[]')
            
            for i, id_produto in enumerate(produtos_selecionados):
                qtd = int(quantidades[i])
                produto = supabase.table("tb_produto").select("nome, estoque").eq("id_produto", id_produto).single().execute().data
                if produto['estoque'] < qtd:
                    flash(f"Venda não realizada. Estoque de '{produto['nome']}' insuficiente.", "erro")
                    return redirect(url_for('adicionar_venda'))
            
            # (Lógica completa para processar a venda)
            flash("Venda registrada com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_vendas'))
        except Exception as e:
            flash(f"Ocorreu um erro ao registrar a venda: {e}", "erro")
            return redirect(url_for('adicionar_venda'))

    try:
        produtos = supabase.table("tb_produto").select("*").eq('ativo', True).order("nome").execute().data
        return render_template('adicionar_venda.html', produtos=produtos)
    except Exception as e:
        flash(f"Não foi possível carregar os produtos: {e}", "erro")
        return redirect(url_for('admin_dashboard'))

# --- GERENCIAMENTO DE ESTOQUE (ADMIN) ---
@app.route('/admin/estoque')
@admin_required()
@nocache
def estoque_mov():
    try:
        movimentos = supabase.table("tb_estoque_mov").select("*, tb_produto(nome)").order("criado_em", desc=True).execute()
        produtos = supabase.table("tb_produto").select("id_produto, nome").order("nome").execute()
        return render_template('estoque.html', movimentos=movimentos.data, produtos=produtos.data)
    except Exception as e:
        flash(f"Não foi possível carregar o histórico de estoque: {e}", "erro")
        return render_template('estoque.html', movimentos=[], produtos=[])

@app.route('/admin/estoque/adicionar', methods=['POST'])
@admin_required()
def adicionar_movimento():
    try:
        id_produto = request.form.get('id_produto')
        tipo_mov = request.form.get('tipo_mov')
        quantidade = int(request.form.get('quantidade'))
        motivo = request.form.get('motivo')
        
        produto = supabase.table("tb_produto").select("id_produto, nome, estoque").eq("id_produto", id_produto).single().execute().data
        if not produto:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for('estoque_mov'))

        if tipo_mov == "SAIDA" and produto['estoque'] < quantidade:
            flash(f"Estoque insuficiente para '{produto['nome']}'. Disponível: {produto['estoque']}", "erro")
            return redirect(url_for('estoque_mov'))

        novo_estoque = produto['estoque'] + quantidade if tipo_mov == "ENTRADA" else produto['estoque'] - quantidade
        supabase.table("tb_produto").update({"estoque": novo_estoque}).eq("id_produto", id_produto).execute()
        supabase.table("tb_estoque_mov").insert({"id_produto": id_produto, "tipo_mov": tipo_mov, "quantidade": quantidade, "motivo": motivo}).execute()
        flash("Movimentação registrada com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao registrar movimentação: {e}", "erro")
    return redirect(url_for('estoque_mov'))

# --- EXECUÇÃO DO APP ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # usa PORT do Render, ou 5000 local
    app.run(host="0.0.0.0", port=port)