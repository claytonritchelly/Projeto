from __future__ import annotations

from typing import Any, Dict, List, Optional

import json
import psycopg


def build_explain_query(sql: str, analyze: bool = False, buffers: bool = False, format_json: bool = True) -> str:
	parts: List[str] = ["EXPLAIN"]
	options: List[str] = []
	if analyze:
		options.append("ANALYZE")
	if buffers:
		options.append("BUFFERS")
	if format_json:
		options.append("FORMAT JSON")
	if options:
		parts.append(f"({', '.join(options)})")
	parts.append(sql)
	return " ".join(parts)


def explain(
	dsn: str,
	sql: str,
	analyze: bool = False,
	buffers: bool = False,
	statement_timeout_ms: Optional[int] = 10000,
) -> Dict[str, Any]:
	"""Executa EXPLAIN no PostgreSQL. Retorna JSON quando possível, caso contrário texto bruto.

	- Usa AUTOCOMMIT e ativa statement_timeout opcional.
	- Não executa DML; se analyze=True, a query é executada para coletar tempos (cuidado).
	"""
	query = build_explain_query(sql, analyze=analyze, buffers=buffers, format_json=True)
	fallback_query = build_explain_query(sql, analyze=analyze, buffers=buffers, format_json=False)

	with psycopg.connect(dsn, autocommit=True) as conn:
		if statement_timeout_ms is not None:
			with conn.cursor() as cur:
				cur.execute(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}")
		try:
			with conn.cursor() as cur:
				cur.execute(query)
				rows = cur.fetchall()
				plan_doc = rows[0][0]
				if isinstance(plan_doc, str):
					parsed = json.loads(plan_doc)
				else:
					parsed = plan_doc
				return {"format": "json", "plan": parsed}
		except Exception:
			with psycopg.connect(dsn, autocommit=True) as conn2:
				if statement_timeout_ms is not None:
					with conn2.cursor() as cur2:
						cur2.execute(f"SET LOCAL statement_timeout = {int(statement_timeout_ms)}")
				with conn2.cursor() as cur2:
					cur2.execute(fallback_query)
					text_lines = [r[0] for r in cur2.fetchall()]
					return {"format": "text", "plan": text_lines}
