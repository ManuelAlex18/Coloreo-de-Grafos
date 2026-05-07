import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import pandas as pd
import io
from algoritmos_coloreo import (
    construir_grafo_conflictos,
    coloreo_voraz_greedy,
    coloreo_dsatur,
    coloreo_voraz_greedy_disponibilidad,
    coloreo_dsatur_disponibilidad,
)


COLORES_BLOQUES = [
    "#E63946", "#457B9D", "#2A9D8F", "#E9C46A",
    "#F4A261", "#A8DADC", "#6A4C93", "#F77F00",
    "#80B918", "#FF6B6B",
]


def color_bloque(n):
    return COLORES_BLOQUES[(n - 1) % len(COLORES_BLOQUES)]


def horario_resultado(res, clases):
    grupos = sorted({c["grupo"] for c in clases})
    max_bloque = max(res.values())
    bloques = [f"B{i}" for i in range(1, max_bloque + 1)]

    # Construir matriz: bloque -> grupo -> lista de clases
    matriz = {b: {g: [] for g in grupos} for b in bloques}
    for c in clases:
        bloque = f"B{res[c['id']]}"
        grupo = c["grupo"]
        materia = c.get("materia", "").strip()
        docente = c["docente"]
        celda = f"{c['id']}"
        if materia:
            celda += f" · {materia}"
        celda += f" ({docente})"
        matriz[bloque][grupo].append(celda)

    filas = []
    for b in bloques:
        fila = {"Bloque": b}
        for g in grupos:
            fila[g] = "  /  ".join(matriz[b][g]) if matriz[b][g] else ""
        filas.append(fila)
    return pd.DataFrame(filas).set_index("Bloque")


def construir_figura(grafo, coloracion, titulo):
    G = nx.Graph()
    for nodo, vecinos in grafo.items():
        G.add_node(nodo)
        for v in vecinos:
            G.add_edge(nodo, v)

    pos = nx.spring_layout(G, seed=42)

    # Aristas
    edge_x, edge_y = [], []
    for u, v in G.edges():
        x0, y0 = pos[u]
        x1, y1 = pos[v]
        edge_x += [x0, x1, None]
        edge_y += [y0, y1, None]

    trace_aristas = go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(width=1.5, color="#888"),
        hoverinfo="none",
    )

    # Nodos
    node_x = [pos[n][0] for n in G.nodes()]
    node_y = [pos[n][1] for n in G.nodes()]
    node_colors = [color_bloque(coloracion[n]) for n in G.nodes()]
    node_text = [
        f"Clase: {n}<br>Bloque: B{coloracion[n]}"
        for n in G.nodes()
    ]
    node_labels = list(G.nodes())

    trace_nodos = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=node_labels,
        textposition="top center",
        hovertext=node_text,
        marker=dict(size=30, color=node_colors, line=dict(width=2, color="white")),
    )

    fig = go.Figure(
        data=[trace_aristas, trace_nodos],
        layout=go.Layout(
            title=dict(text=titulo, font=dict(size=16)),
            showlegend=False,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            height=420,
        ),
    )
    return fig


# ── Interfaz ─────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Coloreo de Grafos", layout="wide")
st.title("Asignacion de Horarios — Coloreo de Grafos")
st.caption("Maestria en Ciencias de la Computacion · 2026")

st.markdown("### Tabla de clases")

# ── Importar / Descargar plantilla ──────────────────────────────────────────────
col_up, col_dl = st.columns(2)

_buf_tmpl = io.BytesIO()
pd.DataFrame(columns=["id", "materia", "grupo", "docente"]).to_excel(
    _buf_tmpl, index=False, engine="openpyxl"
)
_buf_tmpl.seek(0)

with col_up:
    archivo_subido = st.file_uploader(
        "Cargar Plantilla",
        type=["xlsx", "csv"],
        label_visibility="visible",
    )
with col_up:
    st.write("")
    st.write("")
    st.download_button(
        "Descargar plantilla",
        data=_buf_tmpl,
        file_name="plantilla_clases.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        
    )

# ── Cargar datos ─────────────────────────────────────────────────────────────
if archivo_subido is not None:
    if archivo_subido.name.endswith(".csv"):
        _df_cargado = pd.read_csv(archivo_subido)
    else:
        _df_cargado = pd.read_excel(archivo_subido, engine="openpyxl")
    _df_cargado.columns = [str(c).strip().lower() for c in _df_cargado.columns]
    for col in ["id", "materia", "grupo", "docente"]:
        if col not in _df_cargado.columns:
            _df_cargado[col] = ""
    _df_cargado = _df_cargado[["id", "materia", "grupo", "docente"]].astype(str)
    _df_cargado.replace("nan", "", inplace=True)
else:
    _df_cargado = pd.DataFrame(columns=["id", "materia", "grupo", "docente"])

st.info("Agrega clases manualmente o importa un archivo Excel/CSV. Luego presiona **Ejecutar algoritmos**."
)
df_editado = st.data_editor(
    _df_cargado,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "id":      st.column_config.TextColumn("ID Clase", width="small"),
        "materia": st.column_config.TextColumn("Materia"),
        "grupo":   st.column_config.TextColumn("Grupo", width="small"),
        "docente": st.column_config.TextColumn("Docente", width="small"),
    },
)

st.markdown("### Orden para Greedy")
orden_input = st.text_input(
    "Ingresa el orden de procesamiento (separado por comas)",
    value="",
    placeholder="Ejemplo: B,A,H,F,I,E,D,C,G",
    help="Si se deja vacio, se usa el orden en que estan en la tabla.",
)

# ════════════════════════════════════════════════════════════════════
# SECCION: Disponibilidad de docentes por bloque
# ════════════════════════════════════════════════════════════════════
st.markdown("---")
usar_disponibilidad = st.toggle("Restricciones de disponibilidad por docente")

_inputs_prohibidos = {}
if usar_disponibilidad:
    _docentes_cargados = sorted({
        str(r["docente"]).strip()
        for _, r in df_editado.iterrows()
        if pd.notna(r.get("docente")) and str(r.get("docente", "")).strip()
    })

    if not _docentes_cargados:
        st.info("Carga clases en la tabla superior para configurar la disponibilidad de docentes.")
    else:
        st.info(
            "Ingresa los bloques **no disponibles** de cada docente separados por comas. "
            "Si el campo queda vacío, el docente no tiene restricción. "
            "Los bloques son números enteros (1, 2, 3, …)."
        )
        _cols_doc = st.columns(min(len(_docentes_cargados), 4))
        for idx, doc in enumerate(_docentes_cargados):
            with _cols_doc[idx % len(_cols_doc)]:
                _inputs_prohibidos[doc] = st.text_input(
                    f"Docente {doc} — bloques prohibidos",
                    value="",
                    placeholder="Ej: 1, 4",
                    key=f"disp_{doc}",
                )

# ── Botón único de ejecución ──────────────────────────────────────────────────
st.markdown("---")
ejecutar = st.button("Ejecutar algoritmos", type="primary")

if ejecutar:
    clases = df_editado.dropna(subset=["id", "grupo", "docente"]).to_dict("records")
    clases = [c for c in clases if str(c.get("id", "")).strip()]
    if len(clases) < 2:
        st.error("Ingresa al menos 2 clases para construir el grafo.")
        st.stop()

    orden = [x.strip() for x in orden_input.split(",") if x.strip()]
    ids_validos = {c["id"] for c in clases}
    orden_filtrado = [n for n in orden if n in ids_validos]
    for c in clases:
        if c["id"] not in orden_filtrado:
            orden_filtrado.append(c["id"])

    grafo = construir_grafo_conflictos(clases)

    if usar_disponibilidad:
        # Construir bloques_prohibidos desde los inputs
        bloques_prohibidos = {}
        for doc, texto in _inputs_prohibidos.items():
            nums = {int(t.strip()) for t in texto.split(",") if t.strip().isdigit()}
            if nums:
                bloques_prohibidos[doc] = nums
        docente_clase = {c["id"]: c["docente"] for c in clases}
        res_greedy = coloreo_voraz_greedy_disponibilidad(
            grafo, orden_filtrado, docente_clase, bloques_prohibidos
        )
        res_dsatur = coloreo_dsatur_disponibilidad(grafo, docente_clase, bloques_prohibidos)
    else:
        res_greedy = coloreo_voraz_greedy(grafo, orden_filtrado)
        res_dsatur = coloreo_dsatur(grafo)

    bloques_greedy = max(res_greedy.values())
    bloques_dsatur = max(res_dsatur.values())

    # ── Métricas resumen ───────────────────────────────────────────────────
    st.markdown("---")
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Clases", len(clases))
    col_m2.metric("Bloques — Greedy", f"B{bloques_greedy}")
    col_m3.metric("Bloques — DSatur", f"B{bloques_dsatur}")

    # ── Grafos lado a lado ─────────────────────────────────────────────────
    st.markdown("### Grafos coloreados")
    col_g, col_sep, col_d = st.columns([20, 1, 20])
    with col_g:
        st.plotly_chart(
            construir_figura(grafo, res_greedy, f"Greedy  ({bloques_greedy} bloques)"),
            width="stretch",
        )
    with col_sep:
        st.markdown(
            "<style>@media (max-width:768px){.divider-vertical{display:none!important}}</style>"
            "<div class='divider-vertical' style='border-left:2px solid #dee2e6;height:460px;margin:0 auto'></div>",
            unsafe_allow_html=True,
        )
    with col_d:
        st.plotly_chart(
            construir_figura(grafo, res_dsatur, f"DSatur  ({bloques_dsatur} bloques)"),
            width="stretch",
        )

    # ── Leyenda de colores ─────────────────────────────────────────────────
    max_bloques = max(bloques_greedy, bloques_dsatur)
    st.markdown("**Leyenda de bloques:**")
    cols_ley = st.columns(max_bloques)
    for i in range(1, max_bloques + 1):
        cols_ley[i - 1].markdown(
            f"<div style='background:{color_bloque(i)};padding:6px 10px;"
            f"border-radius:6px;color:white;text-align:center'><b>B{i}</b></div>",
            unsafe_allow_html=True,
        )

    # ── Horarios resultantes ───────────────────────────────────────────────
    st.markdown("### Horario resultante")
    st.markdown("**Greedy**")
    st.dataframe(horario_resultado(res_greedy, clases), width="stretch")
    st.markdown("**DSatur**")
    st.dataframe(horario_resultado(res_dsatur, clases), width="stretch")
