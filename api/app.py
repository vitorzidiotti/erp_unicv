import os
import datetime
import bcrypt
import re
import math
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

        if not email_input or not senha_input:
            flash('Email e senha são obrigatórios.', 'erro')
            return render_template('login.html')

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
                    
                    if session.get('is_admin'):
                        return redirect(url_for('admin_dashboard'))
                    else:
                        return redirect(url_for('inicio'))
                else:
                    flash('Email ou senha incorretos.', 'erro')
            else:
                flash('Email ou senha incorretos.', 'erro')
        except Exception as e:
            print(f"ERRO NO LOGIN: {e}")
            flash(f'Ocorreu um erro ao tentar fazer login: {e}', 'erro')

    return render_template('login.html')

@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro():
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')

        if not all([nome, cpf, email, senha]):
            flash('Todos os campos são obrigatórios.', 'erro')
            return render_template('cadastro.html')
            
        cpf_limpo = re.sub(r'\D', '', cpf)

        try:
            # Verifica se já existe usuário com o mesmo CPF
            existing_user = supabase.table("tb_usuario").select("cpf").eq("cpf", cpf_limpo).limit(1).execute()
            if existing_user.data:
                flash(f'O CPF {cpf} já está cadastrado.', 'erro')
                return render_template('cadastro.html')
            
            # Cria hash da senha
            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # Insere o usuário no banco
            supabase.table("tb_usuario").insert({
                "nome": nome,
                "cpf": cpf_limpo,
                "email": email,
                "senha": senha_hash,
                "is_admin": False  # Usuário padrão não é admin
            }).execute()

            # --- Loga o usuário automaticamente ---
            result = supabase.table("tb_usuario").select("id_usuario, nome, is_admin").eq("email", email).limit(1).execute()
            if result.data:
                usuario = result.data[0]
                session['logged_in'] = True
                session['id_usuario'] = usuario['id_usuario']
                session['nome_usuario'] = usuario['nome']
                session['is_admin'] = usuario.get('is_admin', False)

                flash(f"Bem-vindo(a), {usuario['nome']}! Cadastro realizado com sucesso.", 'sucesso')

                # Redireciona direto para admin ou inicio
                if session.get('is_admin'):
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('inicio'))

            else:
                # Caso não consiga buscar o usuário após cadastro
                flash('Cadastro realizado, mas não foi possível fazer login automaticamente. Por favor, faça login.', 'info')
                return redirect(url_for('login'))

        except Exception as e:
            print(f"ERRO NO CADASTRO: {e}")
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

# --- ROTAS PRINCIPAIS (INICIO, PERFIL) ---
@app.route('/inicio')
@login_required()
def inicio():
    return render_template('inicio.html')

@app.route('/perfil', methods=['GET', 'POST'])
@login_required()
def perfil():
    user_id = session.get('id_usuario')
    try:
        current_user_data = supabase.table("tb_usuario").select("id_usuario, nome, cpf, email, senha").eq("id_usuario", user_id).single().execute().data
        if not current_user_data:
            raise Exception("Usuário não encontrado.")
    except Exception as e:
        flash(f'Não foi possível carregar os dados do perfil: {e}', 'erro')
        return redirect(url_for('inicio'))

    if request.method == 'POST':
        dados_para_atualizar = {}
        houve_alteracao = False
        
        novo_nome = request.form.get('nome')
        if novo_nome and novo_nome != current_user_data.get('nome'):
            dados_para_atualizar['nome'] = novo_nome
            houve_alteracao = True
        
        novo_cpf_mascarado = request.form.get('cpf')
        if novo_cpf_mascarado:
            novo_cpf_limpo = re.sub(r'\D', '', novo_cpf_mascarado)
            if novo_cpf_limpo != current_user_data.get('cpf'):
                outro_usuario = supabase.table("tb_usuario").select("id_usuario").eq("cpf", novo_cpf_limpo).neq("id_usuario", user_id).execute().data
                if outro_usuario:
                    flash(f'O CPF {novo_cpf_mascarado} já está em uso por outro usuário.', 'erro')
                    return render_template('perfil.html', usuario=current_user_data)
                dados_para_atualizar['cpf'] = novo_cpf_limpo
                houve_alteracao = True
            
        novo_email = request.form.get('email')
        if novo_email and novo_email != current_user_data.get('email'):
            dados_para_atualizar['email'] = novo_email
            houve_alteracao = True

        nova_senha = request.form.get('nova_senha')
        if nova_senha:
            senha_atual = request.form.get('senha_atual')
            confirmar_senha = request.form.get('confirmar_senha')

            if not senha_atual:
                flash('Você precisa digitar sua senha ATUAL para definir uma nova.', 'erro')
                return render_template('perfil.html', usuario=current_user_data)

            stored_senha_hash = current_user_data['senha'].encode('utf-8')
            if not bcrypt.checkpw(senha_atual.encode('utf-8'), stored_senha_hash):
                flash('A senha atual está incorreta. Tente novamente.', 'erro')
                return render_template('perfil.html', usuario=current_user_data)

            if nova_senha != confirmar_senha:
                flash('A nova senha e a confirmação não coincidem.', 'erro')
                return render_template('perfil.html', usuario=current_user_data)
            
            senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            dados_para_atualizar['senha'] = senha_hash
            houve_alteracao = True
        
        if houve_alteracao:
            try:
                supabase.table("tb_usuario").update(dados_para_atualizar).eq("id_usuario", user_id).execute()
                if 'nome' in dados_para_atualizar:
                    session['nome_usuario'] = dados_para_atualizar['nome']
                flash('Perfil atualizado com sucesso!', 'sucesso')
                return redirect(url_for('perfil'))
            except Exception as e:
                flash(f'Ocorreu um erro ao salvar as alterações: {e}', 'erro')
        else:
            flash('Nenhuma alteração foi detectada.', 'info')
        
        return redirect(url_for('perfil'))
        
    return render_template('perfil.html', usuario=current_user_data)

@app.route('/vendas', methods=['GET', 'POST'])
@login_required()
def pagina_vendas():
    if request.method == 'POST':
        try:
            id_usuario = session.get('id_usuario')
            produtos_ids = request.form.getlist('produtos[]')
            quantidades = request.form.getlist('quantidades[]')
            
            if not produtos_ids or not quantidades:
                flash("Você precisa selecionar ao menos um produto.", "erro")
                return redirect(url_for('pagina_vendas'))

            itens = []
            total = 0.0

            for i, id_produto in enumerate(produtos_ids):
                qtd = int(quantidades[i])
                if qtd <= 0: continue

                produto = supabase.table("tb_produto").select("id_produto, preco, estoque").eq("id_produto", id_produto).single().execute().data
                if not produto:
                    flash(f"Produto com ID {id_produto} não encontrado.", "erro")
                    return redirect(url_for('pagina_vendas'))

                preco_unitario = float(produto['preco'])
                subtotal = preco_unitario * qtd
                total += subtotal
                itens.append({
                    "id_produto": id_produto, "quantidade": qtd, "preco_unitario": preco_unitario
                })

                supabase.table("tb_produto").update({"estoque": produto['estoque'] - qtd}).eq("id_produto", id_produto).execute()
                supabase.table("tb_estoque_mov").insert({
                    "id_produto": id_produto, "tipo_mov": "SAIDA", "quantidade": qtd, "motivo": f"Venda para usuário {id_usuario}"
                }).execute()

            venda_inserida = supabase.table("tb_venda").insert({"id_usuario": id_usuario, "total": total}).execute().data[0]
            id_venda = venda_inserida['id_venda']

            for item in itens:
                item['id_venda'] = id_venda
                supabase.table("tb_venda_item").insert(item).execute()
            
            flash("Venda registrada com sucesso!", "sucesso")
            return redirect(url_for('inicio'))

        except Exception as e:
            flash(f"Ocorreu um erro ao registrar a venda: {e}", "erro")
            return redirect(url_for('pagina_vendas'))

    try:
        produtos = supabase.table("tb_produto").select("*").order("nome").execute().data
        return render_template('adicionar_venda.html', produtos=produtos)
    except Exception as e:
        flash(f"Não foi possível carregar os produtos: {e}", "erro")
        return redirect(url_for('inicio'))


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
        flash(f"Não foi possível carregar a lista de usuários: {e}", "erro")
        return render_template('gerenciar_usuarios.html', usuarios=[], termo_busca=termo_busca)

@app.route('/admin/usuarios/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_usuario():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = request.form.get('cpf')
        senha = request.form.get('senha')
        is_admin = request.form.get('is_admin') == 'on'
        
        if not all([nome, email, cpf, senha]):
            flash('Nome, Email, CPF e Senha são obrigatórios.', 'erro')
            return render_template('adicionar_usuario.html')

        cpf_limpo = re.sub(r'\D', '', cpf)

        try:
            existing = supabase.table("tb_usuario").select("id_usuario").or_(f"cpf.eq.{cpf_limpo},email.eq.{email}").execute().data
            if existing:
                flash("Já existe um usuário com este CPF ou Email.", "erro")
                return render_template('adicionar_usuario.html')

            senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            supabase.table("tb_usuario").insert({
                "nome": nome, "email": email, "cpf": cpf_limpo, "senha": senha_hash, "is_admin": is_admin
            }).execute()
            flash("Usuário adicionado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_usuarios'))
        except Exception as e:
            flash(f"Erro ao adicionar usuário: {e}", "erro")
    
    return render_template('adicionar_usuario.html')

@app.route('/admin/usuarios/editar/<int:id_usuario>', methods=['GET', 'POST'])
@admin_required()
def editar_usuario(id_usuario):
    try:
        usuario = supabase.table("tb_usuario").select("*").eq("id_usuario", id_usuario).single().execute().data
        if not usuario:
            flash("Usuário não encontrado.", "erro")
            return redirect(url_for('gerenciar_usuarios'))
    except Exception as e:
        flash(f"Erro ao carregar dados do usuário: {e}", "erro")
        return redirect(url_for('gerenciar_usuarios'))
    
    if request.method == 'POST':
        dados_para_atualizar = {
            'nome': request.form.get('nome'),
            'email': request.form.get('email'),
            'is_admin': request.form.get('is_admin') == 'on'
        }
        cpf_limpo = re.sub(r'\D', '', request.form.get('cpf'))

        try:
            existing_conflict = supabase.table("tb_usuario").select("id_usuario").or_(f"cpf.eq.{cpf_limpo},email.eq.{dados_para_atualizar['email']}").neq("id_usuario", id_usuario).execute().data
            if existing_conflict:
                flash("O CPF ou Email informado já está em uso por outro usuário.", "erro")
                return render_template('editar_usuario.html', usuario=usuario)
            
            dados_para_atualizar['cpf'] = cpf_limpo
            
            nova_senha = request.form.get('senha')
            if nova_senha:
                senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                dados_para_atualizar['senha'] = senha_hash

            supabase.table("tb_usuario").update(dados_para_atualizar).eq("id_usuario", id_usuario).execute()
            flash("Usuário atualizado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_usuarios'))
        except Exception as e:
            flash(f"Erro ao atualizar usuário: {e}", "erro")

    return render_template('editar_usuario.html', usuario=usuario)

@app.route('/admin/usuarios/excluir/<int:id_usuario>', methods=['POST'])
@admin_required()
def excluir_usuario(id_usuario):
    if id_usuario == session.get('id_usuario'):
        flash("Você não pode excluir a sua própria conta.", "erro")
        return redirect(url_for('gerenciar_usuarios'))
    
    try:
        supabase.table("tb_usuario").delete().eq("id_usuario", id_usuario).execute()
        flash("Usuário excluído com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao excluir usuário: {e}", "erro")
    
    return redirect(url_for('gerenciar_usuarios'))

# --- GERENCIAMENTO DE PRODUTOS ---
@app.route('/admin/gerenciar-produtos')
@admin_required()
@nocache
def gerenciar_produtos():
    try:
        produtos = supabase.table("tb_produto").select("*").order("nome").execute()
        return render_template('gerenciar_produtos.html', produtos=produtos.data)
    except Exception as e:
        flash("Não foi possível carregar a lista de produtos.", "erro")
        return render_template('gerenciar_produtos.html', produtos=[])

@app.route('/admin/produtos/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_produto():
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')
        estoque = request.form.get('estoque') or 0
        try:
            supabase.table("tb_produto").insert({
                "nome": nome,
                "descricao": descricao,
                "preco": float(preco),
                "estoque": int(estoque)
            }).execute()
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
        if not produto:
            raise Exception("Produto não encontrado.")
    except Exception as e:
        flash(f"Não foi possível carregar o produto: {e}", "erro")
        return redirect(url_for('gerenciar_produtos'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')
        estoque = request.form.get('estoque')

        try:
            supabase.table("tb_produto").update({
                "nome": nome,
                "descricao": descricao,
                "preco": float(preco),
                "estoque": int(estoque)
            }).eq("id_produto", id_produto).execute()
            flash("Produto atualizado com sucesso!", "sucesso")
        except Exception as e:
            flash(f"Erro ao atualizar produto: {e}", "erro")
        return redirect(url_for('gerenciar_produtos'))

    return render_template('editar_produto.html', produto=produto)

@app.route('/admin/produtos/excluir', methods=['POST'])
@admin_required()
def excluir_produto():
    data = request.get_json()
    try:
        supabase.table("tb_produto").delete().eq("id_produto", data.get('id_produto')).execute()
        return jsonify({"status": "sucesso", "message": "Produto excluído."})
    except Exception as e:
        return jsonify({"status": "erro", "message": str(e)}), 500

# --- GERENCIAMENTO DE VENDAS ---
@app.route('/admin/gerenciar-vendas')
@admin_required()
@nocache
def gerenciar_vendas():
    try:
        vendas = supabase.table("tb_venda").select("*").order("data_venda", desc=True).execute()
        return render_template('gerenciar_vendas.html', vendas=vendas.data)
    except Exception as e:
        flash("Não foi possível carregar a lista de vendas.", "erro")
        return render_template('gerenciar_vendas.html', vendas=[])
    
@app.route('/admin/vendas/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_venda():
    if request.method == 'POST':
        id_usuario = session.get('id_usuario')
        produtos_ids = request.form.getlist('produtos[]')
        quantidades = request.form.getlist('quantidades[]')

        itens = []
        total = 0.0

        for i, id_produto in enumerate(produtos_ids):
            qtd = int(quantidades[i])
            produto = supabase.table("tb_produto").select("*").eq("id_produto", id_produto).single().execute().data
            if not produto:
                continue
            preco_unitario = float(produto['preco'])
            subtotal = preco_unitario * qtd
            total += subtotal
            itens.append({
                "id_produto": id_produto,
                "quantidade": qtd,
                "preco_unitario": preco_unitario
            })
            supabase.table("tb_produto").update({"estoque": produto['estoque'] - qtd}).eq("id_produto", id_produto).execute()
            supabase.table("tb_estoque_mov").insert({
                "id_produto": id_produto,
                "tipo_mov": "SAIDA",
                "quantidade": qtd,
                "motivo": "Venda"
            }).execute()

        venda = supabase.table("tb_venda").insert({
            "id_usuario": id_usuario,
            "total": total
        }).execute().data[0]

        for item in itens:
            supabase.table("tb_venda_item").insert({
                "id_venda": venda['id_venda'],
                "id_produto": item['id_produto'],
                "quantidade": item['quantidade'],
                "preco_unitario": item['preco_unitario']
            }).execute()

        flash("Venda registrada com sucesso!", "sucesso")
        return redirect(url_for('gerenciar_vendas'))

    produtos = supabase.table("tb_produto").select("*").order("nome").execute().data
    return render_template('adicionar_venda.html', produtos=produtos)

# --- GERENCIAMENTO DE ESTOQUE (movimentações) ---
@app.route('/admin/estoque')
@admin_required()
@nocache
def estoque_mov():
    try:
        movimentos = supabase.table("tb_estoque_mov").select("*").order("criado_em", desc=True).execute()
        return render_template('estoque.html', movimentos=movimentos.data)
    except Exception as e:
        flash("Não foi possível carregar o histórico de estoque.", "erro")
        return render_template('estoque.html', movimentos=[])

@app.route('/admin/estoque/adicionar', methods=['POST'])
@admin_required()
def adicionar_movimento():
    id_produto = request.form.get('id_produto')
    tipo_mov = request.form.get('tipo_mov')
    quantidade = int(request.form.get('quantidade'))
    motivo = request.form.get('motivo')

    try:
        produto = supabase.table("tb_produto").select("*").eq("id_produto", id_produto).single().execute().data
        if not produto:
            flash("Produto não encontrado.", "erro")
            return redirect(url_for('estoque_mov'))

        novo_estoque = produto['estoque'] + quantidade if tipo_mov == "ENTRADA" else produto['estoque'] - quantidade
        supabase.table("tb_produto").update({"estoque": novo_estoque}).eq("id_produto", id_produto).execute()

        supabase.table("tb_estoque_mov").insert({
            "id_produto": id_produto,
            "tipo_mov": tipo_mov,
            "quantidade": quantidade,
            "motivo": motivo
        }).execute()

        flash("Movimentação registrada com sucesso!", "sucesso")
    except Exception as e:
        flash(f"Erro ao registrar movimentação: {e}", "erro")

    return redirect(url_for('estoque_mov'))

# --- GERENCIAMENTO DE CLIENTES (ADMIN) ---
@app.route('/admin/gerenciar_clientes')
@admin_required()
def gerenciar_clientes():
    try:
        clientes = supabase.table("tb_cliente").select("*").order("nome").execute().data
        return render_template('gerenciar_clientes.html', clientes=clientes)
    except Exception as e:
        flash(f"Erro ao carregar clientes: {e}", "erro")
        return render_template('gerenciar_clientes.html', clientes=[])

@app.route('/admin/clientes/adicionar', methods=['GET', 'POST'])
@admin_required()
def adicionar_cliente():
    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = request.form.get('cpf')

        if not all([nome, email, cpf]):
            flash("Todos os campos são obrigatórios.", "erro")
            return redirect(url_for('adicionar_cliente'))

        cpf_limpo = re.sub(r'\D', '', cpf)

        try:
            existing = supabase.table("tb_cliente").select("id_cliente").eq("cpf", cpf_limpo).execute().data
            if existing:
                flash("Cliente já cadastrado com esse CPF.", "erro")
                return redirect(url_for('adicionar_cliente'))

            supabase.table("tb_cliente").insert({
                "nome": nome,
                "email": email,
                "cpf": cpf_limpo
            }).execute()

            flash("Cliente adicionado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_clientes'))
        except Exception as e:
            flash(f"Erro ao adicionar cliente: {e}", "erro")
            return redirect(url_for('gerenciar_clientes'))
            
    return render_template('adicionar_cliente.html')

@app.route('/admin/clientes/editar/<int:id_cliente>', methods=['GET', 'POST'])
@admin_required()
def editar_cliente(id_cliente):
    try:
        cliente = supabase.table("tb_cliente").select("*").eq("id_cliente", id_cliente).single().execute().data
        if not cliente:
            flash("Cliente não encontrado.", "erro")
            return redirect(url_for('gerenciar_clientes'))
    except Exception as e:
        flash(f"Erro ao carregar cliente: {e}", "erro")
        return redirect(url_for('gerenciar_clientes'))

    if request.method == 'POST':
        nome = request.form.get('nome')
        email = request.form.get('email')
        cpf = re.sub(r'\D', '', request.form.get('cpf'))

        if not all([nome, email, cpf]):
            flash("Todos os campos são obrigatórios.", "erro")
            return redirect(url_for('editar_cliente', id_cliente=id_cliente))

        try:
            existing = supabase.table("tb_cliente").select("id_cliente").eq("cpf", cpf).neq("id_cliente", id_cliente).execute().data
            if existing:
                flash("Outro cliente já possui esse CPF.", "erro")
                return redirect(url_for('editar_cliente', id_cliente=id_cliente))

            supabase.table("tb_cliente").update({
                "nome": nome,
                "email": email,
                "cpf": cpf
            }).eq("id_cliente", id_cliente).execute()

            flash("Cliente atualizado com sucesso!", "sucesso")
            return redirect(url_for('gerenciar_clientes'))
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

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

