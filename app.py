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
            tipo='editor',
            ativo=True  # ESSENCIAL para liberar o login
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

        # 🔓 Ativa automaticamente apenas o seu usuário admin
        ativo = True if email == 'rhamonvieiraborges7@gmail.com' else False

        user = User(nome=nome, email=email, senha=senha, tipo=tipo, ativo=ativo)
        db.session.add(user)
        db.session.commit()

        if ativo:
            flash('Cadastro realizado com sucesso. Faça o login.')
        else:
            flash('Cadastro enviado para aprovação do administrador.')

        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/exportar_funcionarios')
def exportar_funcionarios():
    from flask import send_file
    import csv
    import io

    funcionarios = Funcionario.query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nome', 'CPF', 'Data de Nascimento', 'Obra ID'])  # cabeçalhos

    for f in funcionarios:
        writer.writerow([f.id, f.nome, f.cpf, f.data_nascimento, f.obra_id])

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype='text/csv',
        as_attachment=True,
        download_name='funcionarios.csv'
    )

@app.route('/importar_funcionarios', methods=['POST'])
def importar_funcionarios():
    import pandas as pd
    from flask import request, redirect, url_for

    file = request.files.get('arquivo')
    if not file:
        return 'Nenhum arquivo enviado', 400

    try:
        df = pd.read_excel(file, engine='openpyxl')

        for index, row in df.iterrows():
            data_nasc_str = row['data_nascimento']
            data_nascimento = datetime.strptime(data_nasc_str, '%d/%m/%Y').date()

            novo_func = Funcionario(
                nome=row['nome'],
                cpf=row['cpf'],
                data_nascimento=data_nascimento,
                obra_id=int(row['obra_id'])
            )
            db.session.add(novo_func)

        db.session.commit()
        return redirect(url_for('funcionarios'))

    except Exception as e:
        return f'Erro ao importar: {str(e)}', 500

@app.route('/aprovar_usuarios')
@login_required
def aprovar_usuarios():
    if current_user.tipo != 'editor':
        return "Acesso restrito", 403
    usuarios_pendentes = User.query.filter_by(ativo=False).all()
    return render_template('aprovar_usuarios.html', usuarios=usuarios_pendentes)

@app.route('/ativar_usuario/<int:user_id>', methods=['POST'])
@login_required
def ativar_usuario(user_id):
    if current_user.tipo != 'editor':
        return "Acesso restrito", 403
    
    user = User.query.get(user_id)
    if user:
        user.ativo = True
        db.session.commit()
    
    return redirect(url_for('aprovar_usuarios'))

@app.route('/autorizar/<int:user_id>')
@login_required
def autorizar(user_id):
    if current_user.tipo != 'editor':
        return "Acesso restrito", 403
    usuario = User.query.get(user_id)
    usuario.ativo = True
    db.session.commit()
    return redirect(url_for('aprovar_usuarios'))


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
        data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date()
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
        salario_bruto = request.form.get('salario_bruto')
        descontos = request.form.get('descontos')
        impostos = request.form.get('impostos')
        horas_50 = request.form.get('horas_50')
        horas_100 = request.form.get('horas_100')

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

@app.route('/excluir_funcionario/<int:id>', methods=['POST'])
def excluir_funcionario(id):
    func = Funcionario.query.get_or_404(id)
    db.session.delete(func)
    db.session.commit()
    return redirect(url_for('funcionarios'))


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
        salario_bruto = float(request.form.get('salario_bruto', 0))
        impostos = float(request.form.get('impostos', 0))
        horas_50 = float(request.form.get('horas_50', 0))
        horas_100 = float(request.form.get('horas_100', 0))
        dsr = float(request.form.get('dsr', 0))
        dsr_extra = float(request.form.get('dsr_extra', 0))
        data = request.form.get('data')

        holerite = Holerite(
            nome=nome,
            salario_bruto=salario_bruto,
            impostos=impostos,
            horas_50=horas_50,
            horas_100=horas_100,
            dsr=dsr,
            dsr_extra=dsr_extra,
            data=data
        )

        db.session.add(holerite)
        db.session.commit()
        flash('Holerite cadastrado com sucesso!')
        return redirect(url_for('painel_rh'))

    return render_template('holerite.html')

@app.route('/painel_fiscal', methods=['GET', 'POST'])
@login_required
def painel_fiscal():
    if request.method == 'POST':
        tipo = request.form['tipo']
        valor = request.form['valor']
        data = request.form['data']
        nf = request.form['nf']
        obra_destino = request.form['obra_destino']

        nova = Locacao(
            tipo=tipo,
            valor=valor,
            data=data,
            nf=nf,
            obra_destino=obra_destino
        )
        db.session.add(nova)
        db.session.commit()
        flash('✅ Registro fiscal salvo com sucesso!')

    return render_template('painel_fiscal.html')

@app.route('/painel_seguranca')
@login_required
def painel_seguranca():
    funcionarios = Funcionario.query.order_by(Funcionario.nome).all()
    return render_template('painel_seguranca.html', funcionarios=funcionarios)

@app.route('/registrar_epi', methods=['POST'])
def registrar_epi():
    nome = request.form['nome']
    funcao = request.form['funcao']
    cpf = request.form['cpf']
    data = datetime.strptime(request.form['data_requisicao'], "%Y-%m-%d").date()
    epi = request.form['epi']
    assinatura = request.form['assinatura']  # imagem base64

    nova_requisicao = RequisicaoEPI(
        nome=nome,
        funcao=funcao,
        cpf=cpf,
        data_requisicao=data,
        epi=epi,
        imagem=assinatura
    )
    db.session.add(nova_requisicao)
    db.session.commit()
    return redirect(url_for('painel_seguranca'))

@app.route('/historico_epis')
def historico_epis():
    registros = RegistroEPI.query.all()
    return render_template('historico_epis.html', registros=registros)


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

@app.route('/obras', methods=['GET', 'POST'])
@login_required
def obras():
    if request.method == 'POST':
        nome = request.form['nome']
        local = request.form['local']
        estado = request.form['estado']
        cidade = request.form['cidade']
        responsavel = request.form['responsavel']
        usina = request.form['usina']

        nova_obra = Obra(
            nome=nome,
            local=local,
            estado=estado,
            cidade=cidade,
            responsavel=responsavel,
            usina=usina
        )
        db.session.add(nova_obra)
        db.session.commit()
        flash('✅ Obra cadastrada com sucesso!')

    obras = Obra.query.order_by(Obra.nome).all()
    return render_template('obras.html', obras=obras)


@app.route('/graficos')
@login_required
def graficos():
    from sqlalchemy import func  # certifica que isso está importado no topo
    resultados = db.session.query(
        Obra.nome,
        func.sum(Gasto.valor)
    ).join(Gasto).group_by(Obra.nome).all()

    obras = [resultado[0] for resultado in resultados]
    valores = [float(resultado[1]) for resultado in resultados]

    return render_template('graficos.html', obras=obras, valores=valores)


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
