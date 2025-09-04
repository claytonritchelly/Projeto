import json
import streamlit as st

from perfai.core.parser import SQLParser
from perfai.rules.engine import analyze_sql

import pathlib
import os
project_root = pathlib.Path(__file__).resolve().parents[3]
logo_path = str(project_root / "assets" / "goldencloud.png")

# Configuração inicial da página (título e favicon)
st.set_page_config(page_title="Golden", page_icon=logo_path if os.path.exists(logo_path) else None, layout="wide")

css_path = project_root / "assets" / "custom.css"
try:
	with open(css_path, "r", encoding="utf-8") as f:
		st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception:
	pass


# Header com logo (se existir)
cols = st.columns([1,6])
with cols[0]:
    if os.path.exists(logo_path):
        st.image(logo_path, use_column_width=True)
with cols[1]:
    st.title("Ajuste de Performance de Querys")

# Sidebar mínima
st.sidebar.caption("Ferramenta de Perfomance Golden Cloud")
_labels = ["POSTGRE", "MYSQL", "SQL SERVER"]
_choice = st.sidebar.selectbox("Dialeto", _labels, index=0)
_label_to_dialect = {"POSTGRE": "postgres", "MYSQL": "mysql", "SQL SERVER": "tsql"}
dialect = _label_to_dialect[_choice]

# Área principal: duas caixas
st.subheader("Cole sua query original")
input_sql = st.text_area(
	"Query de entrada",
	value="SELECT * FROM users WHERE LOWER(email)=LOWER($1)",
	height=220,
)

col_btn, _ = st.columns([1, 4])
with col_btn:
	ajustar = st.button("Ajustar performance", type="primary")

output_sql = ""
if ajustar and input_sql.strip():
	# Normalização e sugestões
	parser = SQLParser(dialect=dialect)
	normalized = parser.normalize(input_sql)
	rules = analyze_sql(input_sql, dialect=dialect)

	# Monta saída com cabeçalho de sugestões em comentários SQL
	lines: list[str] = []
	lines.append("-- PerfAI: sugestões de otimização (estático, sem banco)")
	if not rules:
		lines.append("-- Nenhuma sugestão crítica encontrada para esta query.")
	else:
		for s in rules:
			severity = s.get("severity", "info")
			message = s.get("message", "Sugestão")
			lines.append(f"-- [{severity}] {message}")
	lines.append("")
	lines.append(normalized)
	output_sql = "\n".join(lines)

st.subheader("Query ajustada")
st.text_area("Saída", value=output_sql, height=280, disabled=False)

# Exportação simples opcional (JSON do relatório), mantendo uma página
if output_sql:
	report = {
		"dialect": dialect,
		"input": input_sql,
		"normalized": output_sql.split("\n\n", 1)[-1] if "\n\n" in output_sql else output_sql,
		"full_output": output_sql,
	}
	st.download_button(
		"Baixar JSON do relatório",
		data=json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8"),
		file_name="perfai_report.json",
		mime="application/json",
	)
