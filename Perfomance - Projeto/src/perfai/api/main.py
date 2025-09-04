resafrom fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from perfai.core.parser import SQLParser
from perfai.llm.ollama_client import OllamaClient
from perfai.connectors.postgres import explain as pg_explain
from perfai.rules.engine import analyze_sql


class AnalyzeRequest(BaseModel):
	sql: str
	db: str
	model: str | None = None
	use_llm: bool = False


app = FastAPI(title="PerfAI", version="0.1.0")


@app.post("/analyze")
async def analyze(req: AnalyzeRequest, format: str = "json"):
	parser = SQLParser(dialect=req.db)
	normalized = parser.normalize(req.sql)

	def baseline_hints(sql_text: str) -> list[str]:
		hints: list[str] = []
		if "SELECT *" in sql_text.upper():
			hints.append("Evite SELECT *: projete apenas as colunas necessárias.")
		if "LOWER(" in sql_text.upper() or "UPPER(" in sql_text.upper():
			hints.append("Evite funções em colunas filtradas; use índices funcionais ou normalize dados.")
		if "IN (" in sql_text.upper() and "," in sql_text:
			hints.append("Avalie trocar IN por JOIN/EXISTS para listas grandes.")
		if "DISTINCT" in sql_text.upper():
			hints.append("Verifique se DISTINCT é necessário; pode mascarar JOINs duplicados.")
		return hints

	result: dict = {"normalized": normalized, "hints": baseline_hints(normalized)}
	result["rules"] = analyze_sql(req.sql, dialect=req.db)

	if format.lower() == "markdown":
		lines: list[str] = []
		lines.append("# PerfAI - Relatório de Otimização SQL")
		lines.append("")
		lines.append("## SQL Normalizada")
		lines.append("````sql")
		lines.append(result.get("normalized", ""))
		lines.append("````")
		if result.get("hints"):
			lines.append("")
			lines.append("## Dicas")
			for h in result["hints"]:
				lines.append(f"- {h}")
		if result.get("rules"):
			lines.append("")
			lines.append("## Recomendações (Regras)")
			for r in result["rules"]:
				lines.append(f"- [{r.get('severity','')}] {r.get('message','')}")
		return PlainTextResponse("\n".join(lines), media_type="text/markdown; charset=utf-8")

	if not req.use_llm:
		result["suggestion"] = "LLM desabilitado (use_llm=false)."
		return result

	try:
		client = OllamaClient(model=req.model or "qwen2.5:7b-instruct")
		prompt = (
			"Reescreva a query SQL mantendo equivalência semântica e explique potenciais ganhos.\n"
			f"Dialeto: {req.db}\nSQL:\n{normalized}\n"
		)
		suggestion = client.complete(prompt)
		result["suggestion"] = suggestion
		return result
	except Exception as exc:  # noqa: BLE001
		result["suggestion"] = f"LLM indisponível: {type(exc).__name__}"
		return result


class ExplainRequest(BaseModel):
	dsn: str
	sql: str
	analyze: bool = False
	buffers: bool = False
	timeout_ms: int | None = 10000


@app.post("/explain/postgres")
async def explain_postgres(req: ExplainRequest):
	plan = pg_explain(
		dsn=req.dsn,
		sql=req.sql,
		analyze=req.analyze,
		buffers=req.buffers,
		statement_timeout_ms=req.timeout_ms,
	)
	return plan
