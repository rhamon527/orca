# ORCA Gastos

Sistema web para controle de gastos por obra.

## Como executar localmente

1. Crie e ative um ambiente virtual:
   ```
   python -m venv venv
   source venv/bin/activate  # ou .\venv\Scripts\activate no Windows
   ```
2. Instale dependências:
   ```
   pip install -r requirements.txt
   ```
3. Configure variáveis de ambiente em um arquivo `.env`:
   ```
   SECRET_KEY=sua_chave_secreta
   DATABASE_URL=sqlite:///orca.db
   ```
4. Execute:
   ```
   python app.py
   ```
5. Acesse `http://localhost:5000/login`.

## Deploy no Heroku

1. Instale o Heroku CLI e faça login:
   ```
   heroku login
   ```
2. Crie o app:
   ```
   heroku create nome-do-app
   ```
3. Configure variáveis:
   ```
   heroku config:set SECRET_KEY=sua_chave DATABASE_URL=postgres://...
   ```
4. Faça commit e push:
   ```
   git add .
   git commit -m "Deploy"
   git push heroku master
   ```
5. Abra o app:
   ```
   heroku open
   ```

Agora seu sistema estará disponível publicamente.

## Uso Universal na Rede Local

Para facilitar o uso em **qualquer PC** da sua rede, você pode executar o script:

- **Windows**:  
  Dê um duplo clique no `run.bat` que exibe seu IP local e inicia o servidor.

- **Linux/macOS**:  
  No terminal, torne o script executável e execute:
  ```bash
  chmod +x run.sh
  ./run.sh
  ```

O script irá:
1. Detectar seu endereço IP na rede local.  
2. Exibir o link `http://<SEU_IP>:5000/login`.  
3. Iniciar o servidor Flask automaticamente.

---

