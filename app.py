from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit
from models import db, User, Obra, Gasto
from config import Config
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import pandas as pd
import io
from flask import send_file, jsonify

import re

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Cria as tabelas assim que a app é carregada
with app.app_context():
    db.create_all()

    # Cria usuário padrão se não existir
    from werkzeug.security import generate_password_hash
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
            if not user.active:
                flash('Acesso restrito: usuário bloqueado.')
                return redirect(url_for('login'))
            login_user(user)
            return redirect(url_for('obras'))
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
@login_required
def obras():
    obras = Obra.query.all()
    return render_template('obras.html', obras=obras)

@app.route('/obras/add', methods=['POST'])
@login_required
def add_obra():
    nome = request.form['nome']
    if nome:
        db.session.add(Obra(nome=nome))
        db.session.commit()
    return redirect(url_for('obras'))

@app.route('/gastos/<int:obra_id>')
@login_required
def gastos(obra_id):
    obra = Obra.query.get_or_404(obra_id)
    return render_template('gastos.html', obra=obra)

@app.route('/gastos/add/<int:obra_id>', methods=['POST'])
@login_required
def add_gasto(obra_id):
    data = datetime.strptime(request.form['data_nota'], '%Y-%m-%d').date()
    # Parsing robusto do valor para suportar formatos com ponto e vírgula
    raw_valor = request.form['valor']
    num = re.sub(r'[^\d,\.]', '', raw_valor)
    num = num.replace('.', '').replace(',', '.')
    valor = float(num)
    gasto = Gasto(
        tipo_nota=request.form['tipo_nota'],
        valor=valor,
        data_nota=data,
        descricao=request.form['descricao'],
        aprovador=request.form['aprovador'],
        obra_id=obra_id
    )
    db.session.add(gasto)
    db.session.commit()
    return redirect(url_for('gastos', obra_id=obra_id))

@app.route('/graficos')
@login_required
def graficos():
    return render_template('graficos.html')

@app.route('/mensagens')
@login_required
def mensagens():
    return render_template('mensagens.html', user=current_user)

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

@app.route('/gastos/delete/<int:obra_id>/<int:gasto_id>', methods=['POST'])
@login_required
def delete_gasto(obra_id, gasto_id):
    gasto = Gasto.query.get_or_404(gasto_id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto removido.')
    return redirect(url_for('gastos', obra_id=obra_id))






@app.route('/export/excel/<int:obra_id>')
@login_required
def export_excel(obra_id):
    obra = Obra.query.get_or_404(obra_id)
    df = pd.DataFrame([{
        'Data': g.data_nota,
        'Tipo': g.tipo_nota,
        'Valor': g.valor,
        'Aprovador': g.aprovador,
        'Descrição': g.descricao
    } for g in obra.gastos])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Gastos')
    output.seek(0)
    return send_file(output, download_name=f'gastos_obra_{obra_id}.xlsx', as_attachment=True)

@app.route('/export/pdf/<int:obra_id>')
@login_required
def export_pdf(obra_id):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    obra = Obra.query.get_or_404(obra_id)
    data = [['Data', 'Tipo', 'Valor', 'Aprovador', 'Descrição']] + [
        [str(g.data_nota), g.tipo_nota, f"R$ {g.valor:.2f}", g.aprovador, g.descricao or '']
        for g in obra.gastos
    ]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    doc.build([table])
    buffer.seek(0)
    return send_file(buffer, download_name=f'gastos_obra_{obra_id}.pdf', as_attachment=True, mimetype='application/pdf')


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

@app.route('/users/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    user.active = False
    db.session.commit()
    flash(f'Usuário {user.nome} bloqueado.')
    return redirect(url_for('users'))

@app.route('/users/unblock/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    user.active = True
    db.session.commit()
    flash(f'Usuário {user.nome} desbloqueado.')
    return redirect(url_for('users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {user.nome} excluído.')
    return redirect(url_for('users'))



@app.route('/api/gastos_tipos')
@login_required
def api_gastos_tipos():
    # Totais por categoria de gasto
    categorias = [
        "Alimentação",
        "Aluguel de imoveis",
        "Locação de carro",
        "VR",
        "Gás de solda",
        "Salário mensal",
        "Locação de andaimes",
        "Locação de PTAs",
        "Locações de equipamentos",
        "Transporte de colaborador"
    ]
    labels = []
    data = []
    for cat in categorias:
        total = db.session.query(db.func.sum(Gasto.valor)).filter(Gasto.tipo_nota == cat).scalar() or 0
        labels.append(cat)
        data.append(total)
    return jsonify(labels=labels, data=data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)





@app.route('/export/excel/<int:obra_id>')
@login_required
def export_excel(obra_id):
    obra = Obra.query.get_or_404(obra_id)
    df = pd.DataFrame([{
        'Data': g.data_nota,
        'Tipo': g.tipo_nota,
        'Valor': g.valor,
        'Aprovador': g.aprovador,
        'Descrição': g.descricao
    } for g in obra.gastos])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Gastos')
    output.seek(0)
    return send_file(output, download_name=f'gastos_obra_{obra_id}.xlsx', as_attachment=True)

@app.route('/export/pdf/<int:obra_id>')
@login_required
def export_pdf(obra_id):
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    obra = Obra.query.get_or_404(obra_id)
    data = [['Data', 'Tipo', 'Valor', 'Aprovador', 'Descrição']] + [
        [str(g.data_nota), g.tipo_nota, f"R$ {g.valor:.2f}", g.aprovador, g.descricao or '']
        for g in obra.gastos
    ]
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer)
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.grey),
        ('GRID', (0,0), (-1,-1), 1, colors.black),
    ]))
    doc.build([table])
    buffer.seek(0)
    return send_file(buffer, download_name=f'gastos_obra_{obra_id}.pdf', as_attachment=True, mimetype='application/pdf')


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

@app.route('/users/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    user.active = False
    db.session.commit()
    flash(f'Usuário {user.nome} bloqueado.')
    return redirect(url_for('users'))

@app.route('/users/unblock/<int:user_id>', methods=['POST'])
@login_required
def unblock_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    user.active = True
    db.session.commit()
    flash(f'Usuário {user.nome} desbloqueado.')
    return redirect(url_for('users'))

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@login_required
def delete_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuário {user.nome} excluído.')
    return redirect(url_for('users'))



@app.route('/api/gastos_tipos')
@login_required
def api_gastos_tipos():
    # Totais por categoria de gasto
    categorias = [
        "Alimentação",
        "Aluguel de imoveis",
        "Locação de carro",
        "VR",
        "Gás de solda",
        "Salário mensal",
        "Locação de andaimes",
        "Locação de PTAs",
        "Locações de equipamentos",
        "Transporte de colaborador"
    ]
    labels = []
    data = []
    for cat in categorias:
        total = db.session.query(db.func.sum(Gasto.valor)).filter(Gasto.tipo_nota == cat).scalar() or 0
        labels.append(cat)
        data.append(total)
    return jsonify(labels=labels, data=data)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
