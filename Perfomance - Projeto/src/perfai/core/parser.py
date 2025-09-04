from typing import Any, Dict, Optional

import sqlglot
from sqlglot import exp


class SQLParser:
	"""Parser e normalizador SQL multi-dialeto usando sqlglot."""

	def __init__(self, dialect: str) -> None:
		self.dialect = dialect

	def parse(self, sql: str) -> exp.Expression:
		return sqlglot.parse_one(sql, read=self.dialect)

	def normalize(self, sql: str) -> str:
		"""Normaliza SQL (formatação e padronização) para facilitar regras e diffs."""
		expr = self.parse(sql)
		return expr.sql(dialect=self.dialect, pretty=True)

	def to_ast(self, sql: str) -> Dict[str, Any]:
		expr = self.parse(sql)
		return expr.to_dict()

	@staticmethod
	def detect_dialect(preferred: Optional[str] = None) -> str:
		return preferred or "postgres"
