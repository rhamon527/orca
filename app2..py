from flask import Flask, render_template, request, redirect, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_required
from datetime import datetime
from models import db, Funcionario, Obra

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # ou sua string do PostgreSQL
app.config['SECRET_KEY'] = 'minha_chave_secreta'
db.init_app(app)

login_manager = LoginManager(app)

@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required
def funcionarios():
    if request.method == 'POST':
        nome = request.form['nome']
        cpf = request.form['cpf']
        data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d')
        obra_id = int(request.form['obra_id'])

        novo_func = Funcionario(nome=nome, cpf=cpf, data_nascimento=data_nascimento, obra_id=obra_id)
        db.session.add(novo_func)
        db.session.commit()
        flash("Funcionário cadastrado com sucesso!")
        return redirect('/funcionarios')

    return render_template('funcionarios.html')
