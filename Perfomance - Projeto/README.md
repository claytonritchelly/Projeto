# PerfAI - Otimizador de Queries SQL

Ferramenta de performance com IA para analisar e otimizar queries SQL de PostgreSQL, MySQL e SQL Server. Combina motor de regras determinístico com LLM local (Ollama) para reescrita e explicações.

## Requisitos
- macOS
- Python 3.11+
- Ollama instalado localmente e modelos baixados

## Instalação
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Preparar Ollama (local)
```bash
brew install --cask ollama
ollama serve &
ollama pull llama3.1:8b-instruct
ollama pull qwen2.5:7b-instruct
```

## Executar API
```bash
uvicorn perfai.api.main:app --reload --port 8000
```

## Executar CLI
```bash
python -m perfai.cli.main analyze --db postgres --sql "SELECT 1"
```

## Aviso
- A ferramenta não executa DML/DDL perigosos; apenas leitura/EXPLAIN.
- Valide recomendações em staging antes de produção.
