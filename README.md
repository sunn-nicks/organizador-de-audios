# organizador-de-audios
organize seus áudios de forma rápida e prática

🌀 Audio Organizer Web App

Organize seus áudios de forma rápida, automática e inteligente.

Este aplicativo web permite:

Detectar e remover duplicatas

Normalizar nomes de arquivos

Extrair as primeiras palavras dos áudios (Google STT)

Renomear automaticamente

Gerar um ZIP final organizado

Funcionar no PC e no celular

Frontend com tema Aurora (Ciano + Violeta), moderno e confortável.

📁 Estrutura do Projeto
audio-organizer-app/
│
├── backend/
│   ├── main.py
│   ├── organizer.py
│   └── processed/
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   ├── script.js
│
└── requirements.txt

🚀 Rodando Localmente
1. Criar ambiente virtual
python -m venv venv

2. Ativar

Windows:

venv\Scripts\activate


Linux/macOS:

source venv/bin/activate

3. Instalar dependências
pip install -r requirements.txt

4. Iniciar o servidor
uvicorn backend.main:app --host 0.0.0.0 --port 8000

5. Abrir no navegador
http://localhost:8000

☁️ Deploy no Render.com (gratuito)
1. Suba este repositório para o GitHub

Visibility: Public

Add README: ON

.gitignore: Python

License: MIT

2. No Render

New → Web Service

Conectar seu repositório

3. Configurações

Build Command:

pip install -r requirements.txt


Start Command:

uvicorn backend.main:app --host 0.0.0.0 --port $PORT


Runtime: Python 3.10+
Instance: Free
Branch: main

Clique Create Web Service.

🎤 Speech-to-Text (Google)

STT é usado apenas quando o nome do arquivo não é considerado “decente”
Não precisa chave API — usa o modo gratuito do SpeechRecognition.

🧠 Como funciona

Identifica duplicatas por hash

Corrige nomes automaticamente

Extrai 1–5 palavras do áudio (configurável)

Renomeia mantendo prefixos

Gera uma pasta final compactada

Fornece link para download

📱 Interface

Upload múltiplo

Escolha de número de palavras (1–5)

Botão Processar

Barra de progresso

Download do ZIP

Tema Aurora (ciano + violeta)

❓ FAQ

O app apaga os originais?
Não. Tudo é feito em cópias internas.

Funciona no celular?
Sim, totalmente responsivo.

O Render precisa ficar ligado?
Não — ele acorda quando acessado.

O app pode ser acessado de qualquer lugar?
Sim, você recebe uma URL pública.

📜 Licença

MIT.
