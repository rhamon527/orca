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

@app.route('/obras/add', methods=['POST'])
@login_required
def add_obra():
    nome = request.form['nome']
    if nome:
        db.session.add(Obra(nome=nome))
        db.session.commit()
    return redirect(url_for('obras'))
    
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

        # Redireciona sempre pro painel geral
        return redirect(url_for('painel_geral'))

    # GET → mostra o template com a lista de obras
    obras = Obra.query.all()
    return render_template('setor.html', obras=obras)

@app.route('/painel/rh')
@login_required
def painel_rh():
    return render_template('painel_rh.html', user=current_user)
@app.route('/painel/fiscal')
@login_required
def painel_fiscal():
    return render_template('painel_fiscal.html', user=current_user)

@app.route('/fiscal/registrar', methods=['POST'])
@login_required
def registrar_locacao():
    from datetime import datetime
    tipo = request.form['tipo']
    valor = float(request.form['valor'].replace(',', '.'))
    data = datetime.strptime(request.form['data'], '%Y-%m-%d')
    nf = request.form['nf']
    obra_destino = request.form['obra_destino']

    locacao = Locacao(
        tipo=tipo,
        valor=valor,
        data=data,
        nf=nf,
        obra_destino=obra_destino
    )
    db.session.add(locacao)
    db.session.commit()
    flash('Locação registrada com sucesso!')
    return redirect(url_for('painel_fiscal'))
@app.route('/painel/seguranca')
@login_required
def painel_seguranca():
    return render_template('painel_seguranca.html', user=current_user)


@app.route('/seguranca/registrar_epi', methods=['GET', 'POST'])
@login_required
def registrar_epi():
    from datetime import datetime
    if request.method == 'POST':
        funcionario_id = request.form['funcionario_id']
        funcao = request.form['funcao']
        epi = request.form['epi']
        data = datetime.strptime(request.form['data'], '%Y-%m-%d')
        assinatura = request.form['assinatura']

        entrega = EntregaEPI(
            funcionario_id=funcionario_id,
            funcao=funcao,
            epi=epi,
            data=data,
            assinatura=assinatura
        )
        db.session.add(entrega)
        db.session.commit()
        flash('Entrega registrada com sucesso!')
        return redirect(url_for('painel_seguranca'))

    funcionarios = Funcionario.query.all()
    return render_template('painel_seguranca.html', funcionarios=funcionarios)


@app.route('/funcionarios/add', methods=['POST'])
@login_required
def add_funcionario():
    nome = request.form['nome']
    cpf = request.form['cpf']
    data_nascimento = request.form['data_nascimento']

    if nome and cpf and data_nascimento:
        funcionario = Funcionario(
            nome=nome,
            cpf=cpf,
            data_nascimento=datetime.strptime(data_nascimento, '%Y-%m-%d')
        )
        db.session.add(funcionario)
        db.session.commit()
        flash('Funcionário cadastrado com sucesso.')
    return redirect(url_for('painel_geral'))

@app.route('/holerites/add', methods=['POST'])
@login_required
def add_holerite():
    funcionario_id = request.form['funcionario_id']
    data_referencia = request.form['data_referencia']
    valor_bruto = float(request.form['valor_bruto'])
    descontos = float(request.form.get('descontos', 0))
    impostos = float(request.form.get('impostos', 0))
    horas_50 = float(request.form.get('horas_50', 0))
    horas_100 = float(request.form.get('horas_100', 0))

    valor_liquido = valor_bruto - descontos - impostos

    holerite = Holerite(
        funcionario_id=funcionario_id,
        data_referencia=data_referencia,
        valor_bruto=valor_bruto,
        descontos=descontos,
        impostos=impostos,
        horas_50=horas_50,
        horas_100=horas_100,
        valor_liquido=valor_liquido
    )
    db.session.add(holerite)
    db.session.commit()
    flash('Holerite cadastrado com sucesso.')
    return redirect(url_for('painel_rh'))

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


@app.route('/users/block/<int:user_id>', methods=['POST'])
@login_required
def block_user(user_id):
    if current_user.tipo != 'editor': return redirect(url_for('obras'))
    user = User.query.get_or_404(user_id)
    user.active = False
    db.session.commit()
    flash(f'Usuário {user.nome} bloqueado.')
    return redirect(url_for('users'))





if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)



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
# Final do app.py
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
