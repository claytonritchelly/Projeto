from __future__ import annotations

from typing import Dict, List

from sqlglot import exp
import sqlglot


Suggestion = Dict[str, str]


def analyze_sql(sql: str, dialect: str = "postgres") -> List[Suggestion]:
	exprs = sqlglot.parse(sql, read=dialect)
	suggestions: List[Suggestion] = []

	for root in exprs:
		# Regra: evitar SELECT *
		selects = list(root.find_all(exp.Select))
		for s in selects:
			if any(isinstance(p, exp.Star) for p in s.expressions):
				suggestions.append({
					"rule": "select_star",
					"severity": "medium",
					"message": "Evite SELECT *; projete apenas as colunas necessárias.",
				})

		# Regra: função em coluna do predicado (sargabilidade)
		for where in root.find_all(exp.Where):
			for func in where.find_all(exp.Func):
				# LOWER(col), UPPER(col), CAST(col AS ...), COALESCE(col, ...), SUBSTRING(col,...)
				try:
					args = list(func.find_all(exp.Column))
				except Exception:
					args = []
				if args:
					suggestions.append({
						"rule": "predicate_function",
						"severity": "high",
						"message": "Evite funções em colunas filtradas (use índice funcional ou normalize os dados).",
					})

		# Regra: LIKE com wildcard à esquerda ('%abc')
		for like in root.find_all(exp.Like):
			lit = None
			if isinstance(like.expression, exp.Literal):
				lit = like.expression
			elif isinstance(like.this, exp.Literal):
				lit = like.this
			if lit is not None and isinstance(lit.this, str) and lit.this.startswith("%"):
				suggestions.append({
					"rule": "leading_wildcard",
					"severity": "medium",
					"message": "LIKE com wildcard à esquerda desabilita índice. Considere trigram/GIN (Postgres) ou buscar por sufixo.",
				})

		# Regra: IN com lista grande de literais
		for isin in root.find_all(exp.In):
			values = getattr(isin, "expressions", []) or []
			if isinstance(values, list) and len(values) >= 10 and all(isinstance(e, exp.Literal) for e in values):
				suggestions.append({
					"rule": "large_in_list",
					"severity": "low",
					"message": "Lista grande no IN; avalie JOIN em tabela temporária/CTE ou EXISTS.",
				})

		# Regra: DISTINCT possivelmente desnecessário
		for _ in root.find_all(exp.Distinct):
			suggestions.append({
				"rule": "distinct_check",
				"severity": "low",
				"message": "Verifique se DISTINCT é necessário; pode mascarar duplicidade causada por JOIN.",
			})

		# Regra: OR múltiplos em mesmo identificador -> IN
		for where in root.find_all(exp.Where):
			or_nodes = list(where.find_all(exp.Or))
			if or_nodes:
				suggestions.append({
					"rule": "or_to_in",
					"severity": "low",
					"message": "Vários ORs podem ser reescritos como IN para simplificar e potencialmente otimizar.",
				})

		# Regra: NOT IN -> avaliar NOT EXISTS (especialmente com NULLs)
		for not_in in root.find_all(exp.Not):
			if isinstance(not_in.this, exp.In):
				suggestions.append({
					"rule": "not_in_exists",
					"severity": "low",
					"message": "NOT IN pode ter semântica indesejada com NULLs; avalie NOT EXISTS.",
				})

	return suggestions
