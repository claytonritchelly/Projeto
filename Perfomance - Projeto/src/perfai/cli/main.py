import json
import typer
from rich import print

from perfai.core.parser import SQLParser
from perfai.llm.ollama_client import OllamaClient

app = typer.Typer(add_completion=False)


@app.command()
def analyze(
	sql: str,
	db: str = typer.Option("postgres", help="postgres|mysql|tsql"),
	use_llm: bool = typer.Option(False, help="Ativa reescrita/explicação por LLM (opcional)"),
	model: str = typer.Option("qwen2.5:7b-instruct"),
):
	parser = SQLParser(dialect=db)
	normalized = parser.normalize(sql)

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

	out = {"normalized": normalized, "hints": baseline_hints(normalized)}

	if not use_llm:
		out["suggestion"] = "LLM desabilitado (use_llm=false)."
		print(out)
		return

	try:
		client = OllamaClient(model=model)
		prompt = (
			"Reescreva a query SQL mantendo equivalência semântica e explique potenciais ganhos.\n"
			f"Dialeto: {db}\nSQL:\n{normalized}\n"
		)
		resp = client.complete(prompt)
		out["suggestion"] = resp
		print(out)
	except Exception as exc:  # noqa: BLE001
		out["suggestion"] = f"LLM indisponível: {type(exc).__name__}"
		print(out)


if __name__ == "__main__":
	app()
