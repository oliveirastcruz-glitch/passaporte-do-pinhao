
"""
Projeto: Passaporte do Pinhão
Autor: Marcos Oliveira (oliveirastcruz-glitch)
Email: oliveirastcruz@gmail.com
Descrição: Aplicação Flask principal.
"""

import sqlite3
import os
import bcrypt
import uuid
import smtplib
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet


app = Flask(__name__)
app.secret_key = 'segredo_super_secreto'

# Rota para a agenda modelo (barbearia)
@app.route('/agenda-modelo')
def agenda_modelo():
    return render_template('AGENDA_MODELO.html')

# Página detalhada da empresa para admin
@app.route('/admin/empresa/<int:empresa_id>')
def admin_ver_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('PRAGMA table_info(empresas)')
    colunas = [row[1] for row in cursor.fetchall()]
    cursor.execute('SELECT * FROM empresas WHERE id = ?', (empresa_id,))
    empresa = cursor.fetchone()
    conn.close()
    if not empresa:
        return '<h2>Empresa não encontrada.</h2>', 404
    # Monta dicionário coluna: valor
    empresa_dict = dict(zip(colunas, empresa))
    return render_template('admin_ver_empresa.html', empresa=empresa_dict)
## ...existing code...



# Chave de criptografia Fernet (deve ser mantida segura!)
FERNET_KEY = os.environ.get('FERNET_KEY')
if not FERNET_KEY:
    # Gera uma chave nova se não existir (em produção, defina via variável de ambiente)
    FERNET_KEY = Fernet.generate_key()
    print(f"Chave Fernet gerada: {FERNET_KEY.decode()}")
fernet = Fernet(FERNET_KEY)



@app.route('/cadastros', methods=['GET', 'POST'])
def cadastros():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Buscar cidades cadastradas para o select da empresa
    cursor.execute('SELECT nome FROM cidades WHERE ativo = 1')
    cidades_empresa = [row[0] for row in cursor.fetchall()]
    if request.method == 'POST':
        # Coleta todos os campos do formulário
        nome = request.form.get('nome')
        sobrenome = request.form.get('sobrenome')
        sexo = request.form.get('sexo')
        data_nascimento = request.form.get('data_nascimento')
        telefone = request.form.get('telefone')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais')  # Só um campo pais
        tipo_documento = request.form.get('tipo_documento')
        documento = request.form.get('documento')
        email = request.form.get('email')
        email2 = request.form.get('email2')
        senha = request.form.get('senha')
        senha2 = request.form.get('senha2')
        tipo_usuario = request.form.get('tipo_usuario')
        aceitar_termos = request.form.get('aceitar_termos')
        foto = request.files.get('foto')
        # Campos de empresa
        empresa = request.form.get('empresa')
        nome_fantasia = request.form.get('nome_fantasia')
        cnpj = request.form.get('cnpj')
        telefone_empresa = request.form.get('telefone_empresa')
        cidade_empresa = request.form.get('cidade_empresa')
        bairro = request.form.get('bairro')
        endereco = request.form.get('endereco')
        numero = request.form.get('numero')
        ponto_referencia = request.form.get('ponto_referencia')
        tipo_servico = request.form.get('tipo_servico')
        # Processamento detalhado dos horários
        dias_abrev = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom']
        horarios_dict = {}
        for dia in dias_abrev:
            aberto = request.form.get(f'abre_{dia}') == dia
            h1 = request.form.get(f'horario_abre1_{dia}') or ''
            f1 = request.form.get(f'horario_fecha1_{dia}') or ''
            h2 = request.form.get(f'horario_abre2_{dia}') or ''
            f2 = request.form.get(f'horario_fecha2_{dia}') or ''
            if aberto:
                if h1 and f1 and not (h2 or f2):
                    horarios_dict[dia] = {'status':'aberto','abre1':h1,'fecha1':f1,'abre2':'','fecha2':'','obs':'sem pausa'}
                elif h1 and f1 and h2 and f2:
                    horarios_dict[dia] = {'status':'aberto','abre1':h1,'fecha1':f1,'abre2':h2,'fecha2':f2,'obs':'com pausa'}
                else:
                    horarios_dict[dia] = {'status':'aberto','abre1':h1,'fecha1':f1,'abre2':h2,'fecha2':f2,'obs':'parcial'}
            else:
                horarios_dict[dia] = {'status':'fechado'}
        import json
        dias_funcionamento = json.dumps(horarios_dict, ensure_ascii=False)

        # Validações básicas
        if not nome or not sobrenome or not sexo or not data_nascimento or not telefone or not cidade or not estado or not pais or not documento or not email or not senha or not aceitar_termos:
            flash('Preencha todos os campos obrigatórios.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa)
        if email != email2:
            flash('Os e-mails não coincidem.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa)
        if senha != senha2:
            flash('As senhas não coincidem.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa)
        if not tipo_usuario:
            flash('Selecione se deseja comprar ou vender.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa)

        # Validação de CPF ou CNPJ
        def validar_cpf_cnpj(doc):
            return len(doc) in [11, 14] and doc.isdigit()
        if not validar_cpf_cnpj(documento):
            flash('CPF ou CNPJ inválido.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa)

        # Salvar foto se enviada
        foto_filename = ''
        if foto and foto.filename:
            foto_filename = f"foto_{uuid.uuid4().hex}.jpg"
            upload_path = os.path.join('static', 'uploads', foto_filename)
            foto.save(upload_path)

        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
        if isinstance(senha_hash, bytes):
            senha_hash = senha_hash.decode('utf-8')

        # Verifica se o e-mail já está cadastrado em empresas ou usuarios
        cursor.execute('SELECT id FROM empresas WHERE email = ?', (email,))
        existe_empresa = cursor.fetchone()
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        existe_usuario = cursor.fetchone()
        # Verifica se o documento (CPF/CNPJ) já está cadastrado em empresas ou usuarios
        cursor.execute('SELECT id FROM empresas WHERE cnpj = ?', (documento,))
        existe_doc_empresa = cursor.fetchone()
        cursor.execute('SELECT id FROM usuarios WHERE cpf = ?', (documento,))
        existe_doc_usuario = cursor.fetchone()
        if existe_empresa or existe_usuario:
            conn.close()
            flash('E-mail já cadastrado.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa, erro_email=True, email=email)
        if existe_doc_empresa or existe_doc_usuario:
            conn.close()
            flash('CNPJ/CPF já cadastrado.')
            return render_template('cadastros.html', cidades_empresa=cidades_empresa, erro_cnpj=True, cnpj=documento)

        if tipo_usuario == 'vendedor':
            # Validação dos campos obrigatórios de empresa
            obrigatorios_empresa = [empresa, cnpj, telefone_empresa]
            if not all(obrigatorios_empresa):
                flash('Preencha todos os campos obrigatórios da empresa.')
                return render_template('cadastros.html', cidades_empresa=cidades_empresa)
            cursor.execute('''
                INSERT INTO empresas (nome, nome_fantasia, cnpj, telefone, email, senha_hash, empresa, documento, cidade, estado, pais, aceitar_termos, foto, bairro, endereco, numero, ponto_referencia, tipo_servico, dias_funcionamento, pausa_meio_dia, horario_abre, horario_fecha, tipo_usuario, data_nascimento, sobrenome, cidade_empresa, telefone_empresa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                empresa, nome_fantasia, cnpj, telefone_empresa, email, senha_hash, empresa, documento, cidade, estado, pais, 1 if aceitar_termos else 0, foto_filename, bairro, endereco, numero, ponto_referencia, tipo_servico, dias_funcionamento, '', '', '', tipo_usuario, data_nascimento, sobrenome, cidade_empresa, telefone_empresa
            ))

            # Cadastro de pessoa física/comprador
            dummy_cnpj = f'SEMEMPRESA-{uuid.uuid4().hex[:8]}'
            cursor.execute('''
                INSERT INTO usuarios (nome, email, senha_hash, tipo, telefone, cidade, estado, pais, sobrenome, cpf, sexo, data_nascimento, foto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                nome, email, senha_hash, 'comprador', telefone, cidade, estado, pais, sobrenome, documento, sexo, data_nascimento, foto_filename
            ))
            conn.commit()
            usuario_id = cursor.lastrowid
            # Também insere um registro dummy na tabela empresas para evitar erro de join futuro
            cursor.execute('''
                INSERT OR IGNORE INTO empresas (nome, nome_fantasia, cnpj, telefone, email, senha_hash, empresa, documento, cidade, estado, pais, aceitar_termos, foto, bairro, endereco, numero, ponto_referencia, tipo_servico, dias_funcionamento, pausa_meio_dia, horario_abre, horario_fecha, tipo_usuario, data_nascimento, sobrenome, cidade_empresa, telefone_empresa)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                '', '', dummy_cnpj, '', email, senha_hash, '', documento, cidade, estado, pais, 1 if aceitar_termos else 0, '', '', '', '', '', '', dias_funcionamento, '', '', '', 'comprador', data_nascimento, sobrenome, '', ''
            ))
            conn.commit()
            session['usuario'] = email
            session['usuario_id'] = usuario_id
            session['nome'] = nome
            session['tipo_usuario'] = 'comprador'
        conn.close()
        flash('Cadastro realizado com sucesso!')
        return redirect(url_for('cadastro_sucesso'))
    return render_template('cadastros.html', cidades_empresa=cidades_empresa)

DB_PATH = r"C:\Users\olive\OneDrive\Desktop\passaporte-do-pinhao\database\banco.db"


# Endpoint AJAX para validação de CPF, CNPJ e e-mail
@app.route('/verifica_existente', methods=['POST'])
def verifica_existente():
    tipo = request.form.get('tipo')
    valor = request.form.get('valor')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    existe = False
    if tipo == 'cpf':
        cursor.execute('SELECT id FROM usuarios WHERE cpf = ?', (valor,))
        existe = cursor.fetchone() is not None
    elif tipo == 'cnpj':
        cursor.execute('SELECT id FROM empresas WHERE cnpj = ?', (valor,))
        existe = cursor.fetchone() is not None
    elif tipo == 'email':
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (valor,))
        existe = cursor.fetchone() is not None
        if not existe:
            cursor.execute('SELECT id FROM empresas WHERE email = ?', (valor,))
            existe = cursor.fetchone() is not None
    conn.close()
    return jsonify({'existe': existe})

# Garante que as tabelas existem antes de cada request
@app.before_request
def garantir_tabelas():
    if not hasattr(g, 'tabelas_criadas'):
        try:
            init_db()
            g.tabelas_criadas = True
        except Exception as e:
            print('Erro ao garantir tabelas:', e)

def criar_tabela_cidades_nao_atendidas():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS cidades_nao_atendidas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                razao_social TEXT,
                nome_fantasia TEXT,
                cnpj TEXT,
                telefone_empresa TEXT,
                cidade_empresa TEXT,
                data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        print('Erro ao criar tabela cidades_nao_atendidas:', e)

def init_db():

    if not os.path.exists('database'):
        os.makedirs('database')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()


    # Tabela de clientes (para cupons e compras)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT,
            senha TEXT,
            telefone TEXT,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de usuários (admin, comprador, vendedor)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            tipo TEXT NOT NULL CHECK(tipo IN ('admin', 'comprador', 'vendedor')),
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabela de cidades
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cidades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            estado TEXT NOT NULL,
            ativo INTEGER DEFAULT 1
        )
    ''')

    # Tabela de empresas (ligada a usuário e cidade)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            nome TEXT NOT NULL,
            nome_fantasia TEXT,
            cnpj TEXT,
            cidade_id INTEGER,
            aprovado INTEGER DEFAULT 0,
            telefone TEXT,
            foto TEXT,
            email TEXT,
            senha_hash TEXT,
            empresa TEXT,
            documento TEXT,
            cidade TEXT,
            estado TEXT,
            pais TEXT,
            aceitar_termos INTEGER,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (cidade_id) REFERENCES cidades(id)
        )
    ''')

    # Tabela de ofertas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ofertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            titulo TEXT NOT NULL,
            descricao TEXT NOT NULL,
            preco REAL NOT NULL,
            imagem TEXT,
            exclusivo INTEGER DEFAULT 0,
            valor_original REAL,
            parcelamento INTEGER DEFAULT 1,
            sem_juros INTEGER DEFAULT 0,
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    ''')

    # Tabela de carrinho
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS carrinho (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            oferta_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 1,
            status TEXT DEFAULT 'aberto',
            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (oferta_id) REFERENCES ofertas(id)
        )
    ''')

    # Tabela de compras
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            data TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'finalizada',
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
    ''')

    # Tabela de itens da compra
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS itens_compra (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            compra_id INTEGER NOT NULL,
            oferta_id INTEGER NOT NULL,
            quantidade INTEGER DEFAULT 1,
            codigo_cupom TEXT,
            validado INTEGER DEFAULT 0,
            FOREIGN KEY (compra_id) REFERENCES compras(id),
            FOREIGN KEY (oferta_id) REFERENCES ofertas(id)
        )
    ''')

    # Tabela de cupons
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oferta_id INTEGER NOT NULL,
            usuario_id INTEGER NOT NULL,
            codigo TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            validado_por_empresa_id INTEGER,
            data_validacao TIMESTAMP,
            FOREIGN KEY (oferta_id) REFERENCES ofertas(id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY (validado_por_empresa_id) REFERENCES empresas(id)
        )
    ''')

    # Tabela cidades não atendidas (mantida)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cidades_nao_atendidas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            razao_social TEXT,
            nome_fantasia TEXT,
            cnpj TEXT,
            telefone_empresa TEXT,
            cidade_empresa TEXT,
            data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    # Usuário padrão (comprador) - CPF: 05920071974, senha: 1234
    try:
        conn2 = sqlite3.connect(DB_PATH)
        cursor2 = conn2.cursor()
        cursor2.execute('SELECT id FROM usuarios WHERE email = ?', ('05920071974',))
        if not cursor2.fetchone():
            senha_hash = bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cursor2.execute('''
                INSERT INTO usuarios (nome, email, senha_hash, tipo)
                VALUES (?, ?, ?, ?)
            ''', ('Usuário Padrão', '05920071974', senha_hash, 'comprador'))
            conn2.commit()
        conn2.close()
    except Exception as e:
        print('Erro ao criar usuário padrão:', e)



# Removido bloco duplicado/confuso de criação de empresas

init_db()

# Criação automática do admin se não existir



def criar_admin_automatico():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    email_admin = 'domjoaolages@gmail.com'
    senha_admin = 'imu4dR13@1987'
    senha_hash = bcrypt.hashpw(senha_admin.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    # Criptografar nome e email
    nome_admin_crypt = fernet.encrypt('Administrador'.encode('utf-8'))
    email_admin_crypt = fernet.encrypt(email_admin.encode('utf-8'))
    cursor.execute("SELECT id FROM usuarios WHERE tipo = 'admin'")
    existe_admin = cursor.fetchone()
    if existe_admin:
        # Atualiza o admin existente para o novo e-mail e senha (criptografados)
        cursor.execute('''UPDATE usuarios SET nome=?, email=?, senha_hash=? WHERE id=?''', (nome_admin_crypt, email_admin_crypt, senha_hash, existe_admin[0]))
        print(f"Admin atualizado (criptografado): {email_admin} | senha: {senha_admin}")
    else:
        cursor.execute('''
            INSERT INTO usuarios (nome, email, senha_hash, tipo)
            VALUES (?, ?, ?, ?)
        ''', (nome_admin_crypt, email_admin_crypt, senha_hash, 'admin'))
        print(f"Admin criado automaticamente (criptografado): {email_admin} | senha: {senha_admin}")
    conn.commit()
    conn.close()

criar_admin_automatico()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ofertas.id, ofertas.titulo, ofertas.descricao, ofertas.preco, ofertas.imagem, empresas.nome,
               ofertas.exclusivo, ofertas.valor_original, ofertas.parcelamento, ofertas.sem_juros
        FROM ofertas
    JOIN empresas ON ofertas.empresa_id = empresas.id
    ''')
    ofertas = cursor.fetchall()
    conn.close()
    return render_template('index.html', ofertas=ofertas)

@app.route('/buscar')
def buscar():
    import unicodedata
    termo = request.args.get('q', '')
    if not termo.strip():
        return redirect(url_for('index'))
    termo_normalizado = unicodedata.normalize('NFKD', termo).encode('ASCII', 'ignore').decode('ASCII').lower()
    # Correções fonéticas simples
    sinonimos = {
        'cafe': ['cafe', 'café', 'caff'],
        'fondue': ['fondue', 'fundi', 'fondi', 'fondue'],
    }
    termos_busca = [termo_normalizado]
    for base, vargs in sinonimos.items():
        if termo_normalizado in vargs:
            termos_busca.extend(v for v in vargs if v != termo_normalizado)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Monta query dinâmica para múltiplos termos
    wheres = []
    params = []
    for t in termos_busca:
        wheres.append('(LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ofertas.titulo, "é", "e"), "ê", "e"), "á", "a"), "í", "i"), "ç", "c")) LIKE ? OR LOWER(REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(ofertas.descricao, "é", "e"), "ê", "e"), "á", "a"), "í", "i"), "ç", "c")) LIKE ?)')
        params.extend([f'%{t}%', f'%{t}%'])
    where_sql = ' OR '.join(wheres)
    cursor.execute(f'''
        SELECT ofertas.id, ofertas.titulo, ofertas.descricao, ofertas.preco, ofertas.imagem, empresas.nome,
               ofertas.exclusivo, ofertas.valor_original, ofertas.parcelamento, ofertas.sem_juros
        FROM ofertas
        JOIN empresas ON ofertas.empresa_id = empresas.id
        WHERE {where_sql}
    ''', params)
    resultados = cursor.fetchall()
    conn.close()
    return render_template('index.html', ofertas=resultados, termo_busca=termo)


# Redireciona qualquer acesso a /cadastro para /cadastros
@app.route('/cadastro', methods=['GET', 'POST'])
def cadastro_redirect():
    return redirect('/cadastros')

@app.route('/cadastro_empresa', methods=['GET', 'POST'])
def cadastro_empresa():
    if request.method == 'POST':
        # Coleta todos os campos do formulário
        nome = request.form.get('nome')
        sobrenome = request.form.get('sobrenome')
        sexo = request.form.get('sexo')
        data_nascimento = request.form.get('data_nascimento')
        telefone = request.form.get('telefone')
        cidade = request.form.get('cidade')
        estado = request.form.get('estado')
        pais = request.form.get('pais')
        tipo_documento = request.form.get('tipo_documento')
        documento = request.form.get('documento')
        email = request.form.get('email')
        senha = request.form.get('senha')
        empresa = request.form.get('empresa')
        aceitar_termos = request.form.get('aceitar_termos')
        tipo_usuario = request.form.get('tipo_usuario')
        foto = request.form.get('foto', '')

        # Salva os dados na session
        session['nome'] = nome
        session['sobrenome'] = sobrenome
        session['sexo'] = sexo
        session['data_nascimento'] = data_nascimento
        session['telefone'] = telefone
        session['cidade'] = cidade
        session['estado'] = estado
        session['pais'] = pais
        session['tipo_documento'] = tipo_documento
        session['documento'] = documento
        session['email'] = email
        session['senha'] = senha
        session['empresa'] = empresa
        session['aceitar_termos'] = aceitar_termos
        session['tipo_usuario'] = tipo_usuario
        session['foto'] = foto
        session.modified = True

        # Validações básicas
        if not nome or not sobrenome or not sexo or not data_nascimento or not telefone or not cidade or not estado or not pais or not documento or not email or not senha or not aceitar_termos:
            return "Erro: Todos os campos são obrigatórios.", 400
        if not tipo_usuario:
            return "Erro: É necessário selecionar se deseja comprar ou vender.", 400

        # Validação de CPF ou CNPJ
        def validar_cpf_cnpj(doc):
            return len(doc) in [11, 14] and doc.isdigit()
        if not validar_cpf_cnpj(documento):
            return "Erro: CPF ou CNPJ inválido.", 400

        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
        if isinstance(senha_hash, bytes):
            senha_hash = senha_hash.decode('utf-8')

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Verifica se o e-mail já está cadastrado em empresas ou usuarios
        cursor.execute('SELECT id FROM empresas WHERE email = ?', (email,))
        existe_empresa = cursor.fetchone()
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        existe_usuario = cursor.fetchone()
        # Verifica se o documento (CPF/CNPJ) já está cadastrado em empresas ou usuarios
        cursor.execute('SELECT id FROM empresas WHERE documento = ?', (documento,))
        existe_doc_empresa = cursor.fetchone()
        cursor.execute('SELECT id FROM usuarios WHERE email = ? OR nome = ?', (documento, documento))
        existe_doc_usuario = cursor.fetchone()
        if existe_empresa or existe_usuario:
            conn.close()
            return render_template('cadastro_empresa.html', erro_email=True, email=email)
        if existe_doc_empresa or existe_doc_usuario:
            conn.close()
            return render_template('cadastro_empresa.html', erro_doc=True, documento=documento)
        # Salva todos os dados na tabela empresas (ajuste conforme colunas do banco)
        cursor.execute('''
            INSERT INTO empresas (nome, email, senha_hash, empresa, documento, telefone, foto, sobrenome, sexo, data_nascimento, cidade, estado, pais, tipo_usuario)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (nome, email, senha_hash, empresa, documento, telefone, foto, sobrenome, sexo, data_nascimento, cidade, estado, pais, tipo_usuario))
        conn.commit()
        empresa_id = cursor.lastrowid
        # Mantém o usuário logado após cadastro
    session['usuario'] = email
    session['empresa_id'] = empresa_id
    session['nome_empresa'] = empresa  # nome da empresa
    session['nome'] = empresa  # para garantir que a tela de sucesso mostre o nome da empresa
    session['tipo_usuario'] = tipo_usuario
    conn.close()
    return redirect(url_for('cadastro_sucesso'))
# Nova rota para mensagem de sucesso
@app.route('/cadastro_sucesso')
def cadastro_sucesso():
    nome = session.get('nome') or session.get('nome_empresa')
    return render_template('cadastro_sucesso.html', nome=nome)
    return render_template('cadastro_empresa.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        identificador = request.form.get('email') or request.form.get('identificador')  # e-mail ou CPF
        senha = request.form['senha']

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Buscar todos admins (criptografados) e outros usuários normalmente
        cursor.execute('SELECT id, nome, email, senha_hash, tipo FROM usuarios')
        usuarios = cursor.fetchall()
        usuario_encontrado = None
        for u in usuarios:
            if u[4] == 'admin':
                # Descriptografa email
                try:
                    email_admin = fernet.decrypt(u[2]).decode('utf-8')
                except Exception:
                    continue
                if identificador == email_admin:
                    usuario_encontrado = (u[0], fernet.decrypt(u[1]).decode('utf-8'), u[3], u[4], email_admin)
                    break
            else:
                if identificador == u[2]:
                    usuario_encontrado = (u[0], u[1], u[3], u[4], u[2])
                    break
        if usuario_encontrado:
            # usuario_encontrado: (id, nome, senha_hash, tipo, email)
            if bcrypt.checkpw(senha.encode('utf-8'), usuario_encontrado[2].encode('utf-8')):
                session['usuario'] = usuario_encontrado[4]
                session['usuario_id'] = usuario_encontrado[0]
                session['nome'] = usuario_encontrado[1]
                session['tipo_usuario'] = usuario_encontrado[3]
                conn.close()
                if usuario_encontrado[3] == 'admin':
                    return redirect('/admin')
                elif usuario_encontrado[3] == 'comprador':
                    return redirect('/minha_pagina')
                elif usuario_encontrado[3] == 'vendedor':
                    return redirect('/empresa')
                else:
                    return redirect('/')
        # Se não encontrar, buscar em empresas (vendedores)
        cursor.execute('SELECT id, nome, senha_hash, documento FROM empresas WHERE email = ? OR documento = ?', (identificador, identificador))
        empresa = cursor.fetchone()
        conn.close()
        if empresa and bcrypt.checkpw(senha.encode('utf-8'), empresa[2].encode('utf-8')):
            session['usuario'] = identificador
            session['empresa_id'] = empresa[0]
            session['nome_empresa'] = empresa[1]
            session['tipo_usuario'] = 'vendedor'
            return redirect('/empresa')
        else:
            return render_template('login.html', error='email_not_found')
    error = request.args.get('error')
    return render_template('login.html', error=error)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.clear()
    return redirect('/')

# Página do usuário logado
@app.route('/minha_pagina')
def minha_pagina():
    if 'usuario' not in session:
        return redirect('/login')
    usuario_id = session.get('usuario_id')
    nome = session.get('nome')
    email = session.get('usuario')
    # Buscar todos os dados do usuário
    usuario = {'nome': nome, 'email': email, 'foto': '/static/uploads/default-user.png', 'telefone': '', 'cidade': '', 'estado': '', 'pais': '', 'data_nascimento': ''}
    if usuario_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT nome, email, foto, telefone, cidade, estado, pais, data_nascimento FROM usuarios WHERE id = ?', (usuario_id,))
        row = cursor.fetchone()
        if row:
            usuario = {
                'nome': row[0],
                'email': row[1],
                'foto': row[2] or '/static/uploads/default-user.png',
                'telefone': row[3] or '',
                'cidade': row[4] or '',
                'estado': row[5] or '',
                'pais': row[6] or '',
                'data_nascimento': row[7] or ''
            }
        # Buscar cupons do usuário
        cursor.execute('''
            SELECT cupons.codigo, ofertas.titulo, ofertas.descricao, ofertas.preco, cupons.ativo
            FROM cupons
            JOIN ofertas ON cupons.oferta_id = ofertas.id
            WHERE cupons.usuario_id = ?
        ''', (usuario_id,))
        cupons = cursor.fetchall()
        # Buscar compras do usuário
        cursor.execute('''
            SELECT compras.id, compras.data, compras.status
            FROM compras
            WHERE compras.usuario_id = ?
            ORDER BY compras.data DESC
        ''', (usuario_id,))
        compras = cursor.fetchall()
        conn.close()
    else:
        cupons = []
        compras = []
    return render_template('minha_conta.html', usuario=usuario, cupons=cupons, compras=compras)

@app.route('/cadastro_oferta', methods=['GET', 'POST'])
def cadastro_oferta():
    if 'empresa_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        titulo = request.form['titulo']
        descricao = request.form['descricao']
        preco = float(request.form['preco'])
        imagem = request.form['imagem']
        empresa_id = session['empresa_id']
    exclusivo = 1 if request.form.get('exclusivo') in ['1', 'on', True] else 0
    valor_original = float(request.form.get('valor_original', preco))
    parcelamento = int(request.form.get('parcelamento', 1))
    sem_juros = 1 if request.form.get('sem_juros') in ['1', 'on', True] else 0

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ofertas (titulo, descricao, preco, imagem, empresa_id, exclusivo, valor_original, parcelamento, sem_juros)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (titulo, descricao, preco, imagem, empresa_id, exclusivo, valor_original, parcelamento, sem_juros))
    conn.commit()
    conn.close()
    return redirect('/')
    
    return render_template('cadastro_oferta.html')

@app.route('/oferta/<int:oferta_id>')
def venda_oferta(oferta_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT ofertas.titulo, ofertas.descricao, ofertas.preco, ofertas.imagem,
               empresas.nome, empresas.telefone,
               ofertas.exclusivo, ofertas.valor_original, ofertas.parcelamento, ofertas.sem_juros
        FROM ofertas
    JOIN empresas ON ofertas.empresa_id = empresas.id
        WHERE ofertas.id = ?
    ''', (oferta_id,))
    oferta = cursor.fetchone()
    conn.close()

    if oferta:
        return render_template('venda_oferta.html', oferta=oferta)
    else:
        return "<h2>Oferta não encontrada.</h2>", 404

@app.route('/empresas')
def listar_empresas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM empresas')
    empresas = cursor.fetchall()
    conn.close()

    html = '<h2>Empresas cadastradas:</h2><ul>'
    for empresa in empresas:
        html += f'<li>{empresa[1]} - {empresa[2]} - {empresa[3]}</li>'
    html += '</ul>'
    return html


@app.route('/empresa')
def empresa():
    if 'empresa_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Buscar dados completos da empresa (incluindo cidade)
    cursor.execute('''
        SELECT e.nome, e.nome_fantasia, e.cnpj, e.telefone, e.email, c.nome as cidade_nome
        FROM empresas e
        LEFT JOIN cidades c ON e.cidade_id = c.id
        WHERE e.id = ?
    ''', (session['empresa_id'],))
    empresa_row = cursor.fetchone()
    empresa = {
        'nome': empresa_row[0] if empresa_row else '',
        'nome_fantasia': empresa_row[1] if empresa_row else '',
        'cnpj': empresa_row[2] if empresa_row else '',
        'telefone': empresa_row[3] if empresa_row else '',
        'email': empresa_row[4] if empresa_row else '',
        'cidade_nome': empresa_row[5] if empresa_row else '',
    }

    # Buscar ofertas cadastradas pela empresa
    cursor.execute('''
        SELECT id, titulo, descricao, preco, imagem, exclusivo, valor_original
        FROM ofertas
    WHERE empresa_id = ?
    ''', (session['empresa_id'],))
    ofertas = cursor.fetchall()

    # Buscar cupons comprados pelos clientes
    cursor.execute('''
        SELECT cupons.id, ofertas.titulo, usuarios.nome
        FROM cupons
        JOIN ofertas ON cupons.oferta_id = ofertas.id
        JOIN usuarios ON cupons.usuario_id = usuarios.id
        WHERE ofertas.empresa_id = ?
    ''', (session['empresa_id'],))
    cupons = cursor.fetchall()

    conn.close()

    return render_template('empresa.html', empresa=empresa, ofertas=ofertas, cupons=cupons)


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Buscar empresas pendentes de aprovação
    cursor.execute('''
        SELECT id, nome, email, aprovado FROM empresas ORDER BY aprovado, nome
    ''')
    empresas = cursor.fetchall()

    # Buscar todas as ofertas cadastradas
    cursor.execute('''
        SELECT id, titulo, descricao, preco FROM ofertas
    ''')
    ofertas = cursor.fetchall()

    # Buscar todos os usuários cadastrados (todos os campos)
    cursor.execute('SELECT id, nome, email, senha_hash, tipo, telefone, cidade, estado, pais, foto, data_nascimento FROM usuarios')
    usuarios = cursor.fetchall()

    # Buscar todas as cidades
    cursor.execute('SELECT id, nome, estado, ativo FROM cidades ORDER BY nome')
    cidades = cursor.fetchall()

    # Buscar todas as empresas detalhado
    cursor.execute('SELECT * FROM empresas')
    empresas_detalhado = cursor.fetchall()

    conn.close()

    return render_template('admin.html', empresas=empresas, ofertas=ofertas, usuarios=usuarios, cidades=cidades, empresas_detalhado=empresas_detalhado)

# Aprovar empresa
@app.route('/admin/empresa/aprovar', methods=['POST'])
def aprovar_empresa():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    empresa_id = request.form.get('empresa_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE empresas SET aprovado = 1 WHERE id = ?', (empresa_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

# Reprovar empresa (opcional: pode ser deletar ou marcar como reprovada)
@app.route('/admin/empresa/reprovar', methods=['POST'])
def reprovar_empresa():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    empresa_id = request.form.get('empresa_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM empresas WHERE id = ?', (empresa_id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

@app.route('/cadastro_admin', methods=['POST'])
def cadastro_admin():
    # Token de proteção via variável de ambiente
    token_requisicao = request.args.get('token')
    token_esperado = os.getenv('ADMIN_SETUP_TOKEN')
    if not token_esperado or token_requisicao != token_esperado:
        return "Acesso negado. Token inválido.", 403

    identificador = '05920071974qh787'
    senha = 'imu4dR13@1987'
    senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO empresas (nome, email, senha_hash, documento, telefone, aprovado)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', ('Admin', 'admin@passaporte.com', senha_hash, identificador, '00000000000', 1))
    conn.commit()
    conn.close()

    return "Admin cadastrado com sucesso!"

@app.route('/esqueci-senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM clientes WHERE email = ?', (email,))
        cliente = cursor.fetchone()
        conn.close()

        if cliente:
            codigo = '123456'  # Gerar código aleatório aqui
            session['codigo_recuperacao'] = codigo
            session['cliente_id'] = cliente[0]

            # Enviar código para o e-mail
            try:
                sender_email = "passaportedopinhao@proton.me"
                sender_password = os.getenv("PROTONMAIL_PASSWORD")

                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = email
                msg['Subject'] = "Código de Recuperação de Senha"
                body = f"Seu código de recuperação é: {codigo}"
                msg.attach(MIMEText(body, 'plain'))

                with smtplib.SMTP("smtp.protonmail.com", 587) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.sendmail(sender_email, email, msg.as_string())

                print(f'Código enviado para {email}: {codigo}')
                return redirect('/recuperar-senha')
            except Exception as e:
                print(f"Erro ao enviar e-mail: {e}")
                return render_template('esqueci_senha.html', error='Erro ao enviar e-mail.')
        else:
            return render_template('esqueci_senha.html', error='E-mail não encontrado.')

    return render_template('esqueci_senha.html')

@app.route('/recuperar-senha', methods=['GET', 'POST'])
def recuperar_senha():
    if request.method == 'POST':
        codigo = request.form.get('codigo')
        nova_senha = request.form.get('nova_senha')

        if codigo == session.get('codigo_recuperacao'):
            senha_hash = bcrypt.hashpw(nova_senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('UPDATE clientes SET senha = ? WHERE id = ?', (senha_hash, session.get('cliente_id')))
            conn.commit()
            conn.close()
            session.pop('codigo_recuperacao', None)
            session.pop('cliente_id', None)
            return redirect('/login')
        else:
            return render_template('recuperar_senha.html', error='Código inválido.')

    return render_template('recuperar_senha.html')

def criar_tabela_cadastro_temp():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cadastro_temp (
            email TEXT PRIMARY KEY,
            nome TEXT,
            sobrenome TEXT,
            cpf TEXT,
            sexo TEXT,
            data_nascimento TEXT,
            cidade TEXT,
            pais TEXT,
            estado TEXT,
            telefone TEXT
        )
    ''')
    conn.commit()
    conn.close()

criar_tabela_cadastro_temp()

@app.route('/cadastro_etapa1', methods=['GET', 'POST'])
def cadastro_etapa1():
    if request.method == 'GET':
        acao = request.args.get('acao')
        if acao:
            session['acao'] = acao
        # Gera um id único para o fluxo de cadastro, se não existir
        if not session.get('cadastro_id'):
            session['cadastro_id'] = str(uuid.uuid4())
    if request.method == 'POST':
        # Salva todos os campos do formulário na sessão
        for campo in ['nome', 'sobrenome', 'cpf', 'sexo', 'data_nascimento', 'cidade', 'pais', 'estado', 'telefone', 'email']:
            session[campo] = request.form.get(campo)
        acao = session.get('acao')
        if acao == 'vender':
            return redirect('/cadastro_etapa2')
        else:
            return redirect('/cadastro_etapa3')
    return render_template('cadastro_etapa1.html')

@app.route('/cadastro_etapa2', methods=['GET', 'POST'])
def cadastro_etapa2():
    acao = session.get('acao')
    if acao != 'vender':
        return redirect('/cadastro_etapa3')
    if request.method == 'POST':
        campos_empresa = [
            'razao_social', 'nome_fantasia', 'cnpj', 'telefone_empresa', 'cidade_empresa',
            'bairro', 'endereco', 'numero', 'ponto_referencia', 'tipo_servico',
            'dias_funcionamento', 'pausa_meio_dia', 'horario_abre', 'horario_fecha'
        ]
        faltando = [campo for campo in campos_empresa[:10] if not request.form.get(campo)]
        if faltando:
            erro = 'Preencha todos os campos obrigatórios antes de avançar.'
            return render_template('cadastro_etapa2.html', erro=erro)
        for campo in campos_empresa:
            session[campo] = request.form.get(campo, '')
        session.modified = True  # Garante persistência da session
        return redirect('/cadastro_etapa3')
    return render_template('cadastro_etapa2.html')

@app.route('/cadastro_etapa3', methods=['GET', 'POST'])
def cadastro_etapa3():
    if request.method == 'POST':
        # Confirmação do e-mail
        email2 = request.form.get('email2')
        email = session.get('email')
        if not email or not email2 or email != email2:
            flash('Confirme corretamente o e-mail digitando igual ao mostrado acima.')
            return render_template('cadastro_etapa3.html', **session)
        session['senha'] = request.form.get('senha')
        return redirect('/finalizar_cadastro')
    # Passa todos os dados da session para o template
    return render_template('cadastro_etapa3.html', **session)

@app.route('/finalizar_cadastro', methods=['POST'])
def finalizar_cadastro():
    acao = session.get('acao')
    if acao == 'vender':
        # Cadastro de empresa/vendedor
        campos_empresa = [
            'razao_social', 'nome_fantasia', 'cnpj', 'telefone_empresa', 'email', 'senha',
            'cidade_empresa', 'bairro', 'endereco', 'numero', 'ponto_referencia', 'tipo_servico',
            'dias_funcionamento', 'pausa_meio_dia', 'horario_abre', 'horario_fecha'
        ]
        faltando = [campo for campo in campos_empresa if not session.get(campo)]
        if faltando:
            flash('Preencha todos os campos obrigatórios do cadastro de empresa.')
            return redirect('/cadastro_etapa2')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Verifica se o e-mail já está cadastrado em empresas ou usuarios
        cursor.execute('SELECT id FROM empresas WHERE email = ?', (session['email'],))
        existe_empresa = cursor.fetchone()
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (session['email'],))
        existe_usuario = cursor.fetchone()
        if existe_empresa or existe_usuario:
            conn.close()
            flash('E-mail já cadastrado. Se for seu, <a href="/esqueci-senha">recupere sua senha</a> ou use outro e-mail.', 'danger')
            return redirect('/cadastro_etapa3')
        senha_hash = bcrypt.hashpw(session['senha'].encode('utf-8'), bcrypt.gensalt())
        if isinstance(senha_hash, bytes):
            senha_hash = senha_hash.decode('utf-8')
        cursor.execute('''INSERT INTO empresas (
            razao_social, nome_fantasia, cnpj, telefone, email, senha_hash,
            cidade, bairro, endereco, numero, ponto_referencia, tipo_servico,
            dias_funcionamento, pausa_meio_dia, horario_abre, horario_fecha
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                session['razao_social'], session['nome_fantasia'], session['cnpj'], session['telefone_empresa'], session['email'], senha_hash,
                session['cidade_empresa'], session['bairro'], session['endereco'], session['numero'], session['ponto_referencia'], session['tipo_servico'],
                session.get('dias_funcionamento',''), session.get('pausa_meio_dia',''), session.get('horario_abre',''), session.get('horario_fecha','')
            )
        )
        conn.commit()
        empresa_id = cursor.lastrowid
        conn.close()
        session['usuario'] = session['email']
        session['empresa_id'] = empresa_id
        session['nome_empresa'] = session['razao_social']
        session['tipo_usuario'] = 'vendedor'
        # Limpa variáveis de sessão do fluxo de cadastro
        for campo in campos_empresa + ['acao','cadastro_id']:
            session.pop(campo, None)
        flash('Cadastro de empresa realizado com sucesso!')
        return redirect(url_for('cadastro_sucesso'))
    else:
        # Cadastro de pessoa física/comprador
        campos_obrigatorios = ['nome','sobrenome','cpf','sexo','cidade','pais','estado','telefone','email','senha','data_nascimento']
        faltando = [campo for campo in campos_obrigatorios if not session.get(campo)]
        if faltando:
            flash('Preencha todos os campos obrigatórios do cadastro.')
            return render_template('cadastro_etapa3.html')
        email = session.get('email')
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Verifica se o e-mail já está cadastrado em usuarios ou empresas
        cursor.execute('SELECT id FROM usuarios WHERE email = ?', (email,))
        existe_usuario = cursor.fetchone()
        cursor.execute('SELECT id FROM empresas WHERE email = ?', (email,))
        existe_empresa = cursor.fetchone()
        if existe_usuario or existe_empresa:
            conn.close()
            flash('E-mail já cadastrado. Se for seu, <a href="/esqueci-senha">recupere sua senha</a> ou use outro e-mail.', 'danger')
            return render_template('cadastro_etapa3.html')
        nome = session.get('nome')
        sobrenome = session.get('sobrenome')
        cpf = session.get('cpf')
        sexo = session.get('sexo')
        data_nascimento = session.get('data_nascimento')
        cidade = session.get('cidade')
        pais = session.get('pais')
        estado = session.get('estado')
        telefone = session.get('telefone')
        senha = session.get('senha')
        senha_hash = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt())
        if isinstance(senha_hash, bytes):
            senha_hash = senha_hash.decode('utf-8')
        cursor.execute('INSERT INTO usuarios (nome, email, senha_hash, tipo, telefone, cidade, estado, pais, sobrenome, cpf, sexo, data_nascimento) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', (nome, email, senha_hash, 'comprador', telefone, cidade, estado, pais, sobrenome, cpf, sexo, data_nascimento))
        conn.commit()
        usuario_id = cursor.lastrowid
        conn.close()
        session['usuario'] = email
        session['usuario_id'] = usuario_id
        session['nome'] = nome
        session['tipo_usuario'] = 'comprador'
        # Limpa variáveis de sessão do fluxo de cadastro
        for campo in campos_obrigatorios + ['acao','cadastro_id']:
            session.pop(campo, None)
        flash('Cadastro realizado com sucesso! Bem-vindo, {}!'.format(nome.split(' ')[0]))
        return redirect(url_for('cadastro_sucesso'))

# Rota para upload de foto
@app.route('/upload_foto', methods=['POST'])
def upload_foto():
    if 'foto' not in request.files:
        flash('Nenhuma foto enviada.')
        return redirect(request.referrer or url_for('cadastro_etapa3'))
    file = request.files['foto']
    if file.filename == '':
        flash('Nenhuma foto selecionada.')
        return redirect(request.referrer or url_for('cadastro_etapa3'))
    if file:
        filename = f"foto_{uuid.uuid4().hex}.jpg"
        upload_path = os.path.join('static', 'uploads', filename)
        file.save(upload_path)
        session['foto'] = filename
        flash('Foto atualizada com sucesso!')
    return redirect(request.referrer or url_for('cadastro_etapa3'))

# Rota de depuração para listar todos os usuários cadastrados
@app.route('/debug_usuarios')
def debug_usuarios():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT id, nome, email, senha_hash, tipo FROM usuarios')
    usuarios = cursor.fetchall()
    conn.close()
    html = '<h2>Usuários cadastrados</h2><table border="1"><tr><th>ID</th><th>Nome</th><th>Email</th><th>Senha Hash</th><th>Tipo</th></tr>'
    for u in usuarios:
        if u[4] == 'admin':
            try:
                nome = fernet.decrypt(u[1]).decode('utf-8')
                email = fernet.decrypt(u[2]).decode('utf-8')
            except Exception:
                nome = '[ERRO]'
                email = '[ERRO]'
        else:
            nome = u[1]
            email = u[2]
        html += f'<tr><td>{u[0]}</td><td>{nome}</td><td>{email}</td><td>{u[3]}</td><td>{u[4]}</td></tr>'
    html += '</table>'
    return html

@app.route('/cidade_nao_atendida')
def cidade_nao_atendida():
    return render_template('cidade_nao_atendida.html')


@app.route('/continuar_comprador')
def continuar_comprador():
    session['acao'] = 'comprar'
    return render_template('cadastro_etapa3.html')


# --- Rotas e funções administrativas e de edição de empresa ---
from flask import flash

# Rotas de administração de cidades (após definição do app)
@app.route('/admin/cidades', methods=['GET', 'POST'])
def admin_cidades():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form.get('nome')
        estado = request.form.get('estado')
        if nome and estado:
            cursor.execute('INSERT INTO cidades (nome, estado, ativo) VALUES (?, ?, 1)', (nome, estado.upper()))
            conn.commit()
            flash('Cidade adicionada com sucesso!')
    cursor.execute('SELECT id, nome, estado, ativo FROM cidades ORDER BY nome')
    cidades = cursor.fetchall()
    # Adiciona consulta de todos os usuários e empresas
    cursor.execute('SELECT id, nome, email, senha_hash, tipo FROM usuarios')
    usuarios = cursor.fetchall()
    cursor.execute('SELECT * FROM empresas')
    empresas = cursor.fetchall()
    conn.close()
    return render_template('admin_cidades.html', cidades=cidades, usuarios=usuarios, empresas=empresas)

@app.route('/admin/cidades/ativar', methods=['POST'])
def ativar_cidade():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    cidade_id = request.form.get('cidade_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cidades SET ativo = 1 WHERE id = ?', (cidade_id,))
    conn.commit()
    conn.close()
    return redirect('/admin/cidades')

@app.route('/admin/cidades/desativar', methods=['POST'])
def desativar_cidade():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    cidade_id = request.form.get('cidade_id')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE cidades SET ativo = 0 WHERE id = ?', (cidade_id,))
    conn.commit()
    conn.close()
    return redirect('/admin/cidades')

# Tabela de histórico de alterações de empresas
def criar_tabela_historico_empresa():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER,
            campo TEXT,
            valor_antigo TEXT,
            valor_novo TEXT,
            alterado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    ''')
    conn.commit()
    conn.close()
criar_tabela_historico_empresa()

# Rota para editar dados da empresa
@app.route('/empresa/editar', methods=['GET', 'POST'])
def editar_empresa():
    if 'empresa_id' not in session:
        return redirect('/login')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    empresa_id = session['empresa_id']
    # Buscar dados atuais
    cursor.execute('''
        SELECT nome, nome_fantasia, cnpj, telefone, email, cidade_id FROM empresas WHERE id = ?
    ''', (empresa_id,))
    row = cursor.fetchone()
    empresa = {
        'nome': row[0] if row else '',
        'nome_fantasia': row[1] if row else '',
        'cnpj': row[2] if row else '',
        'telefone': row[3] if row else '',
        'email': row[4] if row else '',
        'cidade_id': row[5] if row else '',
        'cidade_nome': ''
    }
    # Buscar nome da cidade
    if empresa['cidade_id']:
        cursor.execute('SELECT nome FROM cidades WHERE id = ?', (empresa['cidade_id'],))
        cidade_row = cursor.fetchone()
        empresa['cidade_nome'] = cidade_row[0] if cidade_row else ''

    if request.method == 'POST':
        # Coletar dados do formulário
        novo_nome = request.form.get('nome')
        novo_nome_fantasia = request.form.get('nome_fantasia')
        novo_cnpj = request.form.get('cnpj')
        novo_telefone = request.form.get('telefone')
        novo_email = request.form.get('email')
        novo_cidade_nome = request.form.get('cidade_nome')
        # Buscar id da cidade (cria se não existir)
        cursor.execute('SELECT id FROM cidades WHERE nome = ?', (novo_cidade_nome,))
        cidade_row = cursor.fetchone()
        if cidade_row:
            novo_cidade_id = cidade_row[0]
        else:
            cursor.execute('INSERT INTO cidades (nome, estado, ativo) VALUES (?, ?, 1)', (novo_cidade_nome, 'XX'))
            novo_cidade_id = cursor.lastrowid
        # Salvar histórico de alterações
        campos = [
            ('nome', empresa['nome'], novo_nome),
            ('nome_fantasia', empresa['nome_fantasia'], novo_nome_fantasia),
            ('cnpj', empresa['cnpj'], novo_cnpj),
            ('telefone', empresa['telefone'], novo_telefone),
            ('email', empresa['email'], novo_email),
            ('cidade_id', str(empresa['cidade_id']), str(novo_cidade_id))
        ]
        for campo, antigo, novo in campos:
            if antigo != novo:
                cursor.execute('''
                    INSERT INTO historico_empresa (empresa_id, campo, valor_antigo, valor_novo)
                    VALUES (?, ?, ?, ?)
                ''', (empresa_id, campo, antigo, novo))
        # Atualizar empresa
        cursor.execute('''
            UPDATE empresas SET nome=?, nome_fantasia=?, cnpj=?, telefone=?, email=?, cidade_id=? WHERE id=?
        ''', (novo_nome, novo_nome_fantasia, novo_cnpj, novo_telefone, novo_email, novo_cidade_id, empresa_id))
        conn.commit()
        conn.close()
        return redirect('/empresa')

    conn.close()
    return redirect('/empresa')

# --- Rotas administrativas para usuários ---
@app.route('/admin/usuario/excluir', methods=['POST'])
def admin_excluir_usuario():
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    usuario_id = request.form.get('usuario_id')
    if not usuario_id:
        flash('ID de usuário não informado.')
        return redirect('/admin')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM usuarios WHERE id = ?', (usuario_id,))
    conn.commit()
    conn.close()
    flash('Usuário excluído com sucesso!')
    return redirect('/admin')

# Página de visualização de usuário para admin
@app.route('/admin/usuario/<int:usuario_id>')
def admin_ver_usuario(usuario_id):
    if 'usuario' not in session or session.get('tipo_usuario') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Buscar dados completos do usuário
    cursor.execute('SELECT id, nome, email, telefone, cidade, estado, pais, data_nascimento, foto, tipo, sobrenome, cpf, sexo FROM usuarios WHERE id = ?', (usuario_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return '<h2>Usuário não encontrado</h2>', 404
    usuario = {
        'id': row[0],
        'nome': row[1],
        'email': row[2],
        'telefone': row[3],
        'cidade': row[4],
        'estado': row[5],
        'pais': row[6],
        'data_nascimento': row[7],
        'foto': row[8],
        'tipo': row[9],
        'sobrenome': row[10],
        'cpf': row[11],
        'sexo': row[12]
    }
    # Buscar compras do usuário
    cursor.execute('''
        SELECT compras.id, compras.data, compras.status
        FROM compras
        WHERE compras.usuario_id = ?
        ORDER BY compras.data DESC
    ''', (usuario_id,))
    compras = cursor.fetchall()
    # Buscar cupons do usuário
    cursor.execute('''
        SELECT cupons.codigo, ofertas.titulo, ofertas.descricao, ofertas.preco, cupons.ativo
        FROM cupons
        JOIN ofertas ON cupons.oferta_id = ofertas.id
        WHERE cupons.usuario_id = ?
    ''', (usuario_id,))
    cupons = cursor.fetchall()
    conn.close()
    return render_template('admin_ver_usuario.html', usuario=usuario, compras=compras, cupons=cupons)
    return render_template('empresa_editar.html', empresa=empresa)

@app.route('/usuario/editar', methods=['GET', 'POST'])
def editar_usuario():
    if 'usuario_id' not in session:
        return redirect('/login')
    usuario_id = session['usuario_id']
    campo = request.args.get('campo')
    if campo not in ['nome', 'telefone', 'cidade', 'estado', 'pais', 'data_nascimento', 'foto']:
        return 'Campo inválido.', 400
    is_foto = campo == 'foto'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if request.method == 'POST':
        if is_foto:
            file = request.files.get('valor')
            if not file or file.filename == '':
                conn.close()
                return 'Selecione uma imagem.', 400
            caminho = f'static/uploads/{usuario_id}_foto.png'
            file.save(caminho)
            cursor.execute('UPDATE usuarios SET foto = ? WHERE id = ?', (f'/{caminho}', usuario_id))
            conn.commit()
            conn.close()
            return redirect('/minha_pagina')
        else:
            novo_valor = request.form.get('valor')
            if not novo_valor:
                conn.close()
                return 'Valor não pode ser vazio.', 400
            if campo == 'data_nascimento':
                # Validação simples de data (YYYY-MM-DD)
                import re
                if not re.match(r'^\d{4}-\d{2}-\d{2}$', novo_valor):
                    conn.close()
                    return 'Data deve estar no formato AAAA-MM-DD.', 400
            cursor.execute(f'UPDATE usuarios SET {campo} = ? WHERE id = ?', (novo_valor, usuario_id))
            conn.commit()
            conn.close()
            return redirect('/minha_pagina')
    # GET: mostrar formulário de edição
    cursor.execute(f'SELECT {campo} FROM usuarios WHERE id = ?', (usuario_id,))
    row = cursor.fetchone()
    valor_atual = row[0] if row else ''
    conn.close()
    if is_foto:
        return '''
            <h2>Editar Foto</h2>
            <form method="post" enctype="multipart/form-data">
                <input type="file" name="valor" accept="image/*" required>
                <button type="submit">Salvar</button>
                <a href="/minha_pagina">Cancelar</a>
            </form>
        '''
    else:
        tipo_input = 'date' if campo == 'data_nascimento' else 'text'
        return f'''
            <h2>Editar {campo.replace('_',' ').capitalize()}</h2>
            <form method="post">
                <input type="{tipo_input}" name="valor" value="{valor_atual or ''}" autofocus required>
                <button type="submit">Salvar</button>
                <a href="/minha_pagina">Cancelar</a>
            </form>
        '''

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)