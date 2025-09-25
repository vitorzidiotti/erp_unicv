Sistema de Gestão de Vendas e Estoque
Um sistema web completo para gestão de vendas, controle de estoque, produtos e clientes, desenvolvido com Flask e Supabase.

Visão Geral
Este projeto é uma aplicação web robusta que serve como um Ponto de Venda (PDV) e sistema de gestão para pequenas empresas. Ele permite que administradores gerenciem o catálogo de produtos, controlem as movimentações de estoque, registrem vendas e administrem usuários e clientes. A arquitetura modular com Blueprints garante que o projeto seja organizado, escalável e fácil de manutenir.

Tecnologias Utilizadas
Backend:

Flask: Um micro-framework Python leve e poderoso para a construção do servidor e da lógica da aplicação.

Supabase: Utilizado como backend-as-a-service, fornecendo banco de dados PostgreSQL, autenticação e APIs automáticas.

python-dotenv: Para gerenciamento de variáveis de ambiente.

bcrypt: Para hashing seguro de senhas de usuários.

Frontend:

HTML5: Para a estruturação das páginas.

CSS3: Para estilização, com um design limpo e responsivo.

JavaScript: Para interatividade no lado do cliente, como validações de formulário e notificações.

Ambiente de Desenvolvimento:

Git & GitHub: Para controle de versão e hospedagem do código.

Ambiente Virtual Python (venv): Para isolar as dependências do projeto.

Funcionalidades
Autenticação: Sistema completo de login, cadastro e logout para usuários.

Controle de Acesso: Distinção entre usuários comuns e administradores, com rotas e funcionalidades protegidas.

Painel de Administração: Uma área central para administradores gerenciarem todas as facetas do sistema.

Gerenciamento de Produtos (CRUD): Criar, Ler, Atualizar e Excluir produtos do catálogo.

Controle de Estoque: Registrar entradas e saídas de produtos, com atualização automática do inventário.

Registro de Vendas: Uma interface para registrar novas vendas, selecionando produtos e atualizando o estoque.

Gerenciamento de Usuários e Clientes (CRUD): Administrar contas de usuários e cadastros de clientes.

Como Configurar e Rodar o Projeto
Siga os passos abaixo para configurar o ambiente e rodar o projeto localmente.

1. Pré-requisitos
Python 3.8 ou superior

Git

2. Clone o Repositório
git clone [https://github.com/seu-usuario/sistema-vendas.git](https://github.com/seu-usuario/sistema-vendas.git)
cd sistema-vendas

3. Crie e Ative um Ambiente Virtual
No Windows:

python -m venv venv
.\venv\Scripts\activate

No macOS/Linux:

python3 -m venv venv
source venv/bin/activate

4. Instale as Dependências
Com o ambiente virtual ativado, instale todas as bibliotecas necessárias a partir do arquivo requirements.txt.

pip install -r requirements.txt

5. Configure as Variáveis de Ambiente
Crie um arquivo chamado .env na raiz do projeto. Este arquivo não deve ser enviado para o GitHub. Adicione suas chaves do Supabase e uma chave secreta para o Flask.

# .env
SUPABASE_URL="[https://sua-url-do-projeto.supabase.co](https://sua-url-do-projeto.supabase.co)"
SUPABASE_KEY="sua-chave-anon-publica-do-supabase"
FLASK_SECRET_KEY="crie-uma-chave-secreta-forte-e-aleatoria-aqui"

Onde encontrar as chaves do Supabase?

Vá para o seu projeto no Supabase.

No menu da esquerda, vá em Project Settings (ícone de engrenagem) > API.

Copie a URL e a chave anon public.

6. Execute a Aplicação
Finalmente, inicie o servidor de desenvolvimento do Flask.

flask --app app run --reload --port 8000

A aplicação estará rodando em http://127.0.0.1:8000.

Este projeto foi desenvolvido como uma solução prática para gestão de negócios, aplicando as melhores práticas de desenvolvimento web com Flask.
