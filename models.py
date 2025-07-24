from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __table_args__ = {'extend_existing': True}  # ← adiciona isso para evitar erro

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha = db.Column(db.String(128), nullable=False)
    tipo = db.Column(db.String(20), nullable=False)  # 'visualizador' ou 'editor'
    ativo = db.Column(db.Boolean, default=False)

    @property
    def is_active(self):
        return self.ativo

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cpf = db.Column(db.String(20), nullable=False)
    data_nascimento = db.Column(db.String(20), nullable=False)
    obra_id = db.Column(db.Integer, nullable=False)

class Gasto(db.Model):
    __tablename__ = 'gastos'
    __table_args__ = {'extend_existing': True}  

    id = db.Column(db.Integer, primary_key=True)
    tipo_nota = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    data_nota = db.Column(db.Date, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    aprovador = db.Column(db.String(100), nullable=False)
    obra_id = db.Column(db.Integer, db.ForeignKey('obras.id'), nullable=False)  
    obra = db.relationship('Obra', backref='gastos')

    
class Obra(db.Model):
    __tablename__ = 'obras'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    local = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(100), nullable=False)
    cidade = db.Column(db.String(100), nullable=False)
    responsavel = db.Column(db.String(200), nullable=False)
    usina = db.Column(db.String(200), nullable=True)

class Holerite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    funcionario = db.Column(db.String(100))
    salario_bruto = db.Column(db.Float)
    impostos = db.Column(db.Float)
    horas_extras_50 = db.Column(db.Integer)
    horas_extras_100 = db.Column(db.Integer)
    dsr = db.Column(db.Float)
    dsr_extra = db.Column(db.Float)
    data = db.Column(db.Date, default=date.today)
    
class Locacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(100))
    valor = db.Column(db.Float)
    data = db.Column(db.Date)
    nf = db.Column(db.String(50))
    obra_destino = db.Column(db.String(100))


class EntregaEPI(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'))
    funcao = db.Column(db.String(100))
    epi = db.Column(db.String(100))
    data = db.Column(db.Date)
    assinatura = db.Column(db.String(100))

    funcionario = db.relationship('Funcionario', backref='entregas_epi')

