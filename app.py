from flask import Flask, render_template, redirect, url_for, request, flash, send_file, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Obra, Gasto, Funcionario
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
import io
import re

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Cria as tabelas e dados iniciais
with app.app_context():
    db.create_all()
    # Cria obra padrão se não existir
    if not Obra.query.first():
        nova_obra = Obra(
            nome='Obra Teste',
            local='Cidade',
            estado='UF',
            cidade='Cidade',
            responsavel='Responsável',
            usina='Usina'
        )
        db.session.add(nova_obra)
        db.session.commit()
    # Cria usuário padrão se não existir
    if not User.query.filter_by(email='rhamonvieiraborges7@gmail.com').first():
        default_user = User(
            nome='Rhamon Vieira Borges',
            email='rhamonvieiraborges7@gmail.com',
            senha=generate_password_hash('3691'),
            tipo='editor'
        )
        db.session.add(default_user)
        db.session.commit()

login_manager = LoginManager(app)
login_manager.login_view = 'login'
socketio = SocketIO(app, cors_allowed_origins="*")

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        if user and check_password_hash(user.senha, request.form['senha']):
            login_user(user)
            return redirect(url_for('setor'))
        flash('Login inválido.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = generate_password_hash(request.form['senha'])
        tipo = request.form['tipo']
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.')
            return redirect(url_for('register'))
        user = User(nome=nome, email=email, senha=senha, tipo=tipo)
        db.session.add(user)
        db.session.commit()
        flash('Cadastro realizado com sucesso. Faça o login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/setor', methods=['GET', 'POST'])
@login_required
def setor():
    if request.method == 'POST':
        setor_escolhido = request.form.get('setor')
        obra_id = request.form.get('obra')
        if not obra_id or not setor_escolhido:
            flash('Selecione uma obra e um setor.')
            return redirect(url_for('setor'))
        # Salva na sessão
        from flask import session
        session['obra_id'] = obra_id
        session['setor'] = setor_escolhido
        return redirect(url_for('painel_geral'))
    obras = Obra.query.all()
    return render_template('setor.html', obras=obras)

@app.route('/painel_geral')
@login_required
def painel_geral():
    obra = Obra.query.first()
    obra_id = obra.id if obra else 1
    return render_template('painel_geral.html', user=current_user, obra_id=obra_id)

# ROTA FUNCIONÁRIOS - PARA NÃO DAR ERRO NO PAINEL
@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required
def funcionarios():
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        data_nascimento = request.form['data_nascimento']
        obra_id = request.form['obra_id']

        if not (nome and cpf and data_nascimento and obra_id):
            flash('Preencha todos os campos!')
        else:
            funcionario = Funcionario(
                nome=nome,
                cpf=cpf,
                data_nascimento=data_nascimento,
                obra_id=obra_id
            )
            db.session.add(funcionario)
            db.session.commit()
            flash('Funcionário cadastrado com sucesso!')
        return redirect(url_for('funcionarios'))

    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    return render_template('funcionarios.html', funcionarios=funcionarios)
    
@app.route('/holerite', methods=['GET', 'POST'])
@login_required
def holerite():
    if request.method == 'POST':
        nome = request.form['nome']
        salario_bruto = float(request.form['salario_bruto'])
        descontos = float(request.form.get('descontos', 0))
        impostos = float(request.form.get('impostos', 0))
        horas_50 = float(request.form.get('horas_50', 0))
        horas_100 = float(request.form.get('horas_100', 0))

        holerite = Holerite(
            nome=nome,
            salario_bruto=salario_bruto,
            descontos=descontos,
            impostos=impostos,
            horas_50=horas_50,
            horas_100=horas_100
        )
        db.session.add(holerite)
        db.session.commit()
        flash('Holerite cadastrado com sucesso!')
        return redirect(url_for('holerite'))

    # estas duas linhas precisam estar DENTRO da função:
    holerites = Holerite.query.all()
    return render_template('holerite.html', holerites=holerites)

@app.route('/holerite/delete/<int:id>', methods=['POST'])
@login_required
def delete_holerite(id):
    holerite = Holerite.query.get_or_404(id)
    db.session.delete(holerite)
    db.session.commit()
    flash('Holerite excluído!')
    return redirect(url_for('holerite'))

@app.route('/painel_rh', methods=['GET', 'POST'])
@login_required
def painel_rh():
    if request.method == 'POST':
        nome = request.form['nome']
        salario_bruto = float(request.form['salario_bruto'])
        descontos = float(request.form.get('descontos', 0))
        impostos = float(request.form.get('impostos', 0))
        horas_50 = float(request.form.get('horas_50', 0))
        horas_100 = float(request.form.get('horas_100', 0))

        holerite = Holerite(
            nome=nome,
            salario_bruto=salario_bruto,
            descontos=descontos,
            impostos=impostos,
            horas_50=horas_50,
            horas_100=horas_100
        )
        db.session.add(holerite)
        db.session.commit()
        flash('Holerite cadastrado com sucesso!')
        return redirect(url_for('painel_rh'))

    # aqui você deve usar o nome exato do seu HTML
    return render_template('holerite.html')

@app.route('/gastos', methods=['GET', 'POST'])
@login_required
def gastos():
    if request.method == 'POST':
        tipo = request.form['tipo']
        valor = float(request.form['valor'])
        descricao = request.form.get('descricao')
        obra = request.form.get('obra')
        aprovado_por = request.form.get('aprovado_por')

        novo_gasto = Gasto(
            tipo=tipo,
            valor=valor,
            descricao=descricao,
            obra=obra,
            aprovado_por=aprovado_por
        )
        db.session.add(novo_gasto)
        db.session.commit()
        flash('Gasto registrado com sucesso!')
        return redirect(url_for('gastos'))

    gastos = Gasto.query.all()
    return render_template('gastos.html', gastos=gastos)

@app.route('/adicionar_gasto', methods=['GET', 'POST'])
@login_required
def adicionar_gasto():
    if request.method == 'POST':
        tipo_nota = request.form['tipo_nota']
        valor = float(request.form['valor'])
        data = datetime.strptime(request.form['data'], '%Y-%m-%d')
        descricao = request.form['descricao']
        obra_id = int(request.form['obra_id'])
        aprovado_por = request.form['aprovado_por']

        novo_gasto = Gasto(
            tipo_nota=tipo_nota,
            valor=valor,
            data_nota=data,
            descricao=descricao,
            obra_id=obra_id,
            aprovador=aprovado_por
        )
        db.session.add(novo_gasto)
        db.session.commit()
        flash('Gasto adicionado com sucesso!', 'success')
        return redirect(url_for('gastos'))

    obras = Obra.query.all()
    return render_template('adicionar_gasto.html', obras=obras)


@app.route('/graficos')
@login_required
def graficos():
    obras = Obra.query.all()
    gastos_por_obra = []

    for obra in obras:
        gastos = Gasto.query.filter_by(obra_id=obra.id).all()
        total = sum([gasto.valor or 0 for gasto in gastos])  # Garante que None vira 0
        gastos_por_obra.append((obra.nome, total))

    labels = [x[0] for x in gastos_por_obra]
    valores = [x[1] for x in gastos_por_obra]

    return render_template('graficos.html', obras=labels, valores=valores)


@app.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    # Apenas editores podem gerenciar usuários
    if current_user.tipo != 'editor':
        flash('Acesso negado.')
        return redirect(url_for('obras'))
    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        senha = generate_password_hash(request.form['senha'])
        tipo = request.form['tipo']
        if User.query.filter_by(email=email).first():
            flash('E-mail já cadastrado.')
        else:
            user = User(nome=nome, email=email, senha=senha, tipo=tipo)
            db.session.add(user)
            db.session.commit()
            flash('Usuário criado com sucesso.')
    users_list = User.query.all()
    return render_template('users.html', users=users_list)

@app.route('/mensagens')
@login_required
def mensagens():
    return render_template('mensagens.html', user=current_user)

# --- O RESTANTE DAS ROTAS ORIGINAIS CONTINUA NORMAL ---

# Online users tracking
online_users = set()
@socketio.on('connect')
def handle_connect():
    online_users.add(current_user.nome)
    emit('user_list', list(online_users), broadcast=True)
@socketio.on('disconnect')
def handle_disconnect():
    online_users.discard(current_user.nome)
    emit('user_list', list(online_users), broadcast=True)
@socketio.on('send_message')
def handle_message(data):
    emit('new_message', {'user': current_user.nome, 'msg': data['msg']}, broadcast=True)

# Rotas de add, delete, export, bloqueio, desbloqueio etc
# ... (Seu restante de código pode ficar abaixo, igual já estava)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
