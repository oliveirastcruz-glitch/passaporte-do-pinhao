# Passaporte do Pinhão

Aplicação web em Flask para gerenciamento de empresas, ofertas, usuários e uma agenda modelo (protótipo de barbearia).

## Funcionalidades Atuais
- Cadastro de usuários e empresas com validações básicas
- Upload de fotos (armazenadas em `static/uploads` – ignorado no Git após `.gitignore`)
- Estrutura de ofertas, carrinho, compras e cupons (CRUD inicial preparado)
- Agenda modelo acessível em `/agenda-modelo` com interface interativa (HTML/CSS/JS puros)
- Criação automática das tabelas SQLite se não existirem
- Criptografia de dados sensíveis com Fernet (chave gerada se não definida)

## Requisitos
- Python 3.10+
- Pip

## Instalação
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Executar a Aplicação
```powershell
python main.py
```
Acesse: http://127.0.0.1:5000

## Deploy no Render

### Preparação das Dependências
O arquivo `requirements.txt` já inclui todas as dependências necessárias para produção:
- **flask**: Framework web principal
- **gunicorn**: Servidor WSGI para produção
- **bcrypt**: Para hash de senhas (usado pela aplicação)
- **cryptography**: Para criptografia de dados sensíveis (Fernet)

### Configuração no Render
1. **Comando de Start**: Configure o comando de inicialização no Render como:
   ```
   gunicorn main:app
   ```

2. **Variáveis de Ambiente**:
   - O Render automaticamente define a variável `PORT` - a aplicação deve usar `os.environ.get('PORT', 5000)`
   - Defina `FERNET_KEY` como variável de ambiente para a chave de criptografia em produção
   - Configure outras variáveis sensíveis conforme necessário

3. **Configurações Recomendadas**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn main:app`
   - **Environment**: Python 3

### Observações para Produção
- A aplicação criará automaticamente o banco SQLite se não existir
- Uploads são armazenados em `static/uploads` (considere usar armazenamento persistente)
- Defina `FERNET_KEY` como variável de ambiente para segurança dos dados criptografados

## Estrutura Simplificada
```
main.py                # Aplicação Flask principal
database/              # Bancos locais (ignorado após .gitignore)
static/
	style.css
	uploads/             # Uploads de usuários (.gitkeep mantém pasta)
templates/             # Templates Jinja2 (HTML)
```

## Próximos Passos Sugeridos
- Integrar agenda com dados reais do banco
- Adicionar autenticação/autorização mais robusta (login separado, roles)
- Implementar Alembic para migrações de banco ao invés de CREATE direto
- Criar testes automatizados (pytest) para rotas críticas
- Refatorar lógica em camadas (services / repositories)
- Otimizar tratamento de uploads e validações de imagem

## Segurança / Observações
- A chave Fernet deveria ser definida via variável de ambiente `FERNET_KEY` em produção.
- Evitar subir dados reais ou sensíveis no repositório (já mitigado por `.gitignore`).
- Considerar migração futura para Postgres/MySQL em produção.

## Licença
Projeto interno / experimental (definir licença futuramente).

---
Autor: Marcos Oliveira
