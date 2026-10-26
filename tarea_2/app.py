"""Dashboard · Voces y documentos peruanos: del archivo escaneado al texto buscable (Tarea 2, Parte 3).

Solo lee resultados ya calculados y publicables: los CSV seudonimizados de datos/ y datos/reportes/.
No carga PaddleOCR, Tesseract, Whisper, Parakeet ni el LLM, y no contiene audio ni imágenes originales.
Ejecutar desde la raíz del repositorio:  streamlit run tarea_2/app.py
"""
from __future__ import annotations

import html
import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RAIZ = Path(__file__).resolve().parent
DATOS = RAIZ / "datos"
REPORTES = DATOS / "reportes"
PENDIENTE = "PENDIENTE_REVISION_HUMANA"
PENDIENTE_TXT = "Pendiente de revisión"
ORDEN_TIPO = ["impreso", "foto", "manuscrito"]
OCR = ["PaddleOCR", "Tesseract"]                          # principal, alternativo
ASR = ["faster-whisper small", "Parakeet TDT 0.6B v3"]    # principal, alternativo

# Columnas que se publican (todo lo demás se descarta al cargar): textos seudonimizados y metadatos
# sin nombres de archivo de origen ni autores, que podrían reidentificar a personas contemporáneas.
COLS_DOCS = ["id", "tipo", "es_mixto", "observacion_tipo", "epoca", "politica_privacidad", "licencia", "fuente_url",
             "ancho_px", "alto_px", "n_lineas", "n_caracteres", "confianza_media", "tiempo_ocr_seg", "modelo_ocr",
             "n_reemplazos", "revision_privacidad", "texto_ocr"]
COLS_AUDIO = ["id", "fuente_id", "fuente_etiqueta", "licencia", "inicio_s", "duracion_seg", "idioma",
              "idioma_detectado_libre", "idioma_detectado_prob", "n_hablantes", "n_hablantes_estimado",
              "hablantes_en_clip", "pct_voz_vad", "n_palabras", "tiempo_proc_s", "latencia_primer_segmento_s", "rtf",
              "modelo_asr", "n_reemplazos", "revision_privacidad", "texto_asr_diarizado"]
COLS_FUENTES = ["id", "modalidad", "licencia", "licencia_url", "fuente_url", "acceso", "fecha_consulta"]

st.set_page_config(page_title="Voces y documentos peruanos", page_icon="📜", layout="wide",
                   menu_items={"About": "Tarea 2 · Diplomado Python · Mirian de la Cruz Condori"})

# Paleta categórica validada (claro / oscuro): posición 1 = modelo principal, posición 2 = alternativo
_tema = getattr(getattr(st.context, "theme", None), "type", None)
OSCURO = _tema == "dark"
CAT = (["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#9085e9"] if OSCURO
       else ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#6250d6"])
NEUTRO = "#898781"
ANILLO = "rgba(14, 17, 23, 0.9)" if OSCURO else "rgba(255, 255, 255, 0.9)"   # separa marcadores superpuestos
COLOR_MODELO = {OCR[0]: CAT[0], OCR[1]: CAT[1], ASR[0]: CAT[0], ASR[1]: CAT[1]}

st.markdown("""
<style>
.block-container {padding-top: 2.2rem; max-width: 1500px;}
.cabecera h1 {margin-bottom: 0.1rem;}
.cabecera p {opacity: 0.75; margin-top: 0;}
.texto-fuente {font-size: 0.93rem; line-height: 1.6; white-space: pre-wrap;}
.seud {font-family: ui-monospace, Consolas, monospace; font-size: 0.82em; padding: 0 4px; border-radius: 4px;
       background: rgba(137, 135, 129, 0.22);}
mark {background: rgba(237, 161, 0, 0.35); color: inherit; padding: 0 2px; border-radius: 3px;}
.turno {display: grid; grid-template-columns: 7.5rem 1fr; gap: 0.6rem; padding: 0.35rem 0;
        border-bottom: 1px solid rgba(137, 135, 129, 0.18);}
.turno .hab {font-size: 0.8rem; font-weight: 600; opacity: 0.85; white-space: nowrap;}
.turno .hab .punto {display: inline-block; width: 0.6rem; height: 0.6rem; border-radius: 50%; margin-right: 0.35rem;}
.turno .txt {font-size: 0.93rem; line-height: 1.55;}
.fragmento {font-size: 0.9rem; line-height: 1.55; margin: 0.15rem 0 0.35rem 0; opacity: 0.92;}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------------------------
# Datos (solo CSV precalculados)
# ---------------------------------------------------------------------------------------------
@st.cache_data
def cargar() -> dict[str, pd.DataFrame | None]:
    docs = pd.read_csv(DATOS / "documentos.csv")[COLS_DOCS]
    audio = pd.read_csv(DATOS / "transcripciones.csv")[COLS_AUDIO]
    fuentes = pd.read_csv(DATOS / "fuentes.csv")[COLS_FUENTES]
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    m_ocr = pd.read_csv(REPORTES / "metricas_ocr.csv")
    m_asr = pd.read_csv(REPORTES / "metricas_asr.csv")
    ruta_acuerdo = REPORTES / "acuerdo_llm_humano.csv"

    en_muestra = set(muestra["id"])
    docs["en_muestra"] = docs["id"].isin(en_muestra)
    audio["en_muestra"] = audio["id"].isin(en_muestra)
    cer = m_ocr.pivot(index="id", columns="modelo", values="cer")
    docs = docs.merge(cer.rename(columns={OCR[0]: "cer_paddle", OCR[1]: "cer_tesseract"}), left_on="id",
                      right_index=True, how="left")
    wer = m_asr.pivot(index="id", columns="modelo", values="wer")
    audio = audio.merge(wer.rename(columns={ASR[0]: "wer_whisper", ASR[1]: "wer_parakeet"}), left_on="id",
                        right_index=True, how="left")
    url_fuente = fuentes.set_index("id")["fuente_url"]
    audio["fuente_url"] = audio["fuente_id"].map(url_fuente)
    # Cómo se verificó la fuente de cada documento: por SHA-1 (archivo idéntico) o por contenido
    acceso = fuentes.set_index("id")["acceso"].astype(str)
    docs["verificacion_fuente"] = docs["id"].map(acceso).map(
        lambda a: "Commons · verificada por contenido" if "contenido" in a else
        ("Commons · verificada por SHA-1" if "SHA-1" in a else PENDIENTE_TXT))
    audio["texto_plano"] = audio["texto_asr_diarizado"].fillna("").map(quitar_hablantes)
    for df in (docs, audio):
        df["fuente_url"] = df["fuente_url"].where(df["fuente_url"].astype(str).str.startswith("http"))
    return {
        "docs": docs, "audio": audio, "fuentes": fuentes, "muestra": muestra, "m_ocr": m_ocr, "m_asr": m_asr,
        "resumen": pd.read_csv(REPORTES / "resumen_metricas.csv"),
        "comparacion": pd.read_csv(REPORTES / "comparacion_modelos_bootstrap.csv"),
        "bench": pd.read_csv(REPORTES / "benchmark_tiempos.csv"),
        "referencias": pd.read_csv(REPORTES / "control_referencias.csv"),
        "ext": pd.read_csv(DATOS / "extraccion_llm.csv"),
        "auditoria": pd.read_csv(DATOS / "auditoria_llm.csv"),
        "acuerdo": pd.read_csv(ruta_acuerdo) if ruta_acuerdo.exists() else None,
    }


def quitar_hablantes(texto: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\[HABLANTE_[\d?]+\]", " ", texto)).strip()


# ---------------------------------------------------------------------------------------------
# Utilidades de presentación
# ---------------------------------------------------------------------------------------------
def num(x: float, d: int = 3) -> str:
    """Número con coma decimal (formato del informe)."""
    return f"{x:.{d}f}".replace(".", ",")


def metrica_txt(x: float) -> str:
    """CER/WER para tablas: solo existe en la muestra de evaluación."""
    return "—" if pd.isna(x) else num(x)


def pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def mostrar(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)) or str(v) == PENDIENTE:
        return PENDIENTE_TXT
    if str(v) == "REVISADO_HUMANAMENTE":
        return "Revisada por la autora"
    return str(v)


def resaltar_seudonimos(texto_html: str) -> str:
    return re.sub(r"\[((?:NOMBRE|EMAIL|TELEFONO|DNI|DIRECCION)(?:_\d+)?)\]", r'<span class="seud">[\1]</span>',
                  texto_html)


def texto_html(texto: str) -> str:
    return resaltar_seudonimos(html.escape(str(texto)))


def normalizar(s: str) -> str:
    """Minúsculas y sin tildes, conservando la longitud (para ubicar coincidencias en el texto original)."""
    return "".join((unicodedata.normalize("NFD", c)[:1] or c).lower()[:1] or c for c in s)


def coincidencias(texto: str, consulta: str) -> list[tuple[int, int]]:
    q = normalizar(consulta.strip())
    if not q:
        return []
    return [(m.start(), m.end()) for m in re.finditer(re.escape(q), normalizar(texto))]


def fragmentos(texto: str, pos: list[tuple[int, int]], ventana: int = 90, maximo: int = 3) -> list[str]:
    salida, ultimo_fin = [], -1
    for ini, fin in pos:
        if ini < ultimo_fin or len(salida) == maximo:
            continue
        a, b = max(0, ini - ventana), min(len(texto), fin + ventana)
        salida.append(("… " if a > 0 else "") + texto_html(texto[a:ini]) + "<mark>" + html.escape(texto[ini:fin])
                      + "</mark>" + texto_html(texto[fin:b]) + (" …" if b < len(texto) else ""))
        ultimo_fin = b
    return salida


def grafico(fig: go.Figure, alto: int = 380, leyenda: bool = True, rejilla_x: bool = False) -> None:
    fig.update_layout(height=alto, margin=dict(l=8, r=8, t=36 if leyenda else 12, b=8), showlegend=leyenda,
                      legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title=None),
                      bargap=0.3, bargroupgap=0.08, hoverlabel=dict(font_size=12))
    fig.update_xaxes(showgrid=rejilla_x)
    st.plotly_chart(fig, theme="streamlit", config={"displayModeBar": False})


def titulo_grafico(titulo: str, subtitulo: str) -> None:
    st.markdown(f"**{titulo}**")
    st.caption(subtitulo)


def tabla_campos(campos: dict) -> None:
    """Tabla Campo/Valor en markdown: a diferencia de st.dataframe, ajusta los textos largos."""
    filas = []
    for k, v in campos.items():
        valor = texto_html(str(v).replace("\n", " ")).replace("|", "&#124;")
        filas.append(f"| {k} | {valor} |")
    st.markdown("| Campo | Valor |\n|---|---|\n" + "\n".join(filas), unsafe_allow_html=True)


def descarga(df: pd.DataFrame, archivo: str, etiqueta: str, key: str) -> None:
    st.download_button(etiqueta, df.to_csv(index=False).encode("utf-8-sig"), file_name=archivo, mime="text/csv",
                       icon=":material/download:", key=key, on_click="ignore")


def decision_auditoria(D, id_: str) -> None:
    aud = D["auditoria"].set_index("id")
    if id_ not in aud.index:
        st.caption("Este elemento no forma parte de los 20 casos de la auditoría humana.")
        return
    dec, obs = aud.loc[id_, "correcto"], aud.loc[id_, "observacion"]
    if dec == "SI":
        st.badge("Auditoría humana: extracción correcta", icon=":material/check_circle:", color="green")
    elif dec == "NO":
        st.badge("Auditoría humana: extracción incorrecta", icon=":material/cancel:", color="red")
    else:
        st.badge(f"Auditoría humana: {PENDIENTE_TXT}", icon=":material/schedule:", color="gray")
    if isinstance(obs, str) and obs.strip():
        st.caption(f"Observación de la autora: {obs}")


def extraccion_llm(D, id_: str) -> None:
    fila = D["ext"].set_index("id").loc[id_]
    campos = json.loads(fila["campos_json"])
    claves = ["tema", "resumen", "emisor", "fecha", "monto"] if campos.get("modalidad") == "documento" else \
        ["tema", "resumen", "numero_hablantes"]
    tabla_campos({k: ("— (no aparece: null)" if campos.get(k) is None else campos[k]) for k in claves})
    if campos.get("citas_clave"):
        st.markdown("**Citas clave**")
        for c in campos["citas_clave"]:
            st.markdown(f"> {texto_html(c)}", unsafe_allow_html=True)
    verif = {"Citas literales en el texto": fila["verif_citas"], "Cifras de fecha/monto en el texto": fila["verif_fecha_monto"],
             "Hablantes = etiquetas": fila["verif_hablantes"]}
    st.caption(" · ".join(f"{k}: {v}" for k, v in verif.items() if v != "no_aplica"))
    decision_auditoria(D, id_)


# ---------------------------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------------------------
def tab_resumen(D) -> None:
    docs, audio, res, comp = D["docs"], D["audio"], D["resumen"].set_index("modelo"), D["comparacion"].set_index("metrica")
    st.info("**Pregunta guía:** ¿Podemos convertir documentos escaneados y entrevistas en audio en un archivo de texto "
            "estructurado y buscable?", icon=":material/help:")

    tipos = docs["tipo"].value_counts()
    verificadas = docs["fuente_url"].notna().sum()
    c = st.columns(4)
    with c[0]:
        st.metric("Documentos", len(docs), border=True)
        st.caption(" · ".join(f"{tipos.get(t, 0)} {t}s" for t in ORDEN_TIPO))
    with c[1]:
        st.metric("Audio en español peruano", f"{num(audio['duracion_seg'].sum() / 60, 1)} min", border=True)
        st.caption(f"{len(audio)} clips de {audio['fuente_id'].nunique()} fuentes")
    with c[2]:
        st.metric("Texto extraído", f"{audio['n_palabras'].sum():,} palabras".replace(",", " "), border=True)
        st.caption(f"en audio, y {docs['n_caracteres'].sum():,} caracteres de OCR".replace(",", " "))
    with c[3]:
        st.metric("Fuentes verificadas", f"{verificadas + audio['fuente_id'].nunique()}/{len(docs) + audio['fuente_id'].nunique()}",
                  border=True)
        por_contenido = (docs["verificacion_fuente"] == "Commons · verificada por contenido").sum()
        pendientes = len(docs) - verificadas
        st.caption(f"{pendientes} documentos: {PENDIENTE_TXT.lower()}" if pendientes else
                   f"Por SHA-1, salvo {por_contenido} documentos verificados por contenido")

    mejor_asr = res.loc[ASR, "promedio"].idxmin()
    otro_asr = [m for m in ASR if m != mejor_asr][0]
    c = st.columns(4)
    with c[0]:
        st.metric("CER PaddleOCR (menor = mejor)", num(res.loc[OCR[0], "promedio"]), border=True,
                  delta=f"{res.loc[OCR[0], 'promedio'] - res.loc[OCR[1], 'promedio']:+.3f} vs Tesseract".replace(".", ","),
                  delta_color="inverse")
        st.caption("Diferencia significativa (IC 95 % bootstrap)" if comp.loc["CER", "significativa"] else "Diferencia no significativa")
    with c[1]:
        st.metric(f"WER {mejor_asr.split()[0]} (menor = mejor)", num(res.loc[mejor_asr, "promedio"]), border=True,
                  delta=f"{res.loc[mejor_asr, 'promedio'] - res.loc[otro_asr, 'promedio']:+.3f} vs {otro_asr.split()[0]}".replace(".", ","),
                  delta_color="inverse")
        st.caption("Diferencia significativa (IC 95 % bootstrap)" if comp.loc["WER", "significativa"] else
                   "Diferencia no significativa: el IC 95 % incluye 0")
    with c[2]:
        if D["acuerdo"] is not None:
            a = D["acuerdo"].set_index("modalidad")
            st.metric("Acuerdo LLM-humano", pct(a.loc["total", "acuerdo"]), border=True)
            st.caption(f"Documentos {pct(a.loc['documento', 'acuerdo'])} · audios {pct(a.loc['audio', 'acuerdo'])} · n = {a.loc['total', 'n']}")
        else:
            st.metric("Acuerdo LLM-humano", PENDIENTE_TXT, border=True)
    with c[3]:
        ref = D["referencias"]["estado"].value_counts()
        revisadas = ref[ref.index.str.startswith("REVISADO_")].sum()
        st.metric("Referencias revisadas", f"{revisadas}/{len(D['referencias'])}", border=True)
        st.caption(f"{ref.get('REVISADO_CON_CAMBIOS', 0)} corregidas · {ref.get('REVISADO_SIN_CAMBIOS', 0)} aceptadas sin cambios")

    st.space("small")
    g1, g2 = st.columns(2)
    with g1:
        titulo_grafico("El error de OCR crece de impresos a fotos y manuscritos",
                       "CER promedio por tipo de documento en la muestra de evaluación (menor = mejor)")
        fig = go.Figure()
        for modelo in OCR:
            v = [res.loc[modelo, f"promedio_{t}"] for t in ORDEN_TIPO]
            fig.add_bar(x=ORDEN_TIPO, y=v, name=modelo, marker=dict(color=COLOR_MODELO[modelo], cornerradius=4),
                        text=[num(x, 2) for x in v], textposition="outside",
                        hovertemplate="%{x} · " + modelo + ": CER %{y:.3f}<extra></extra>")
        fig.update_layout(barmode="group", yaxis=dict(title="CER promedio", range=[0, 1.15]))
        grafico(fig)
    with g2:
        titulo_grafico("Los dos ASR tienen un WER parecido en casi todos los clips",
                       "WER por clip (menor = mejor); cada línea une los dos modelos sobre el mismo clip; "
                       "un solo punto indica que ambos empatan")
        grafico(figura_wer(D), rejilla_x=True)

    st.markdown("#### Respuesta a la pregunta guía")
    a_txt = (f"La autora juzgó correctas {D['acuerdo'].set_index('modalidad').loc['total', 'correctos']} de "
             f"{D['acuerdo'].set_index('modalidad').loc['total', 'n']} extracciones") if D["acuerdo"] is not None else PENDIENTE_TXT
    st.markdown(f"""
- **Sí, para impresos y habla clara.** El CER en impresos es {num(res.loc[OCR[0], 'promedio_impreso'])} con PaddleOCR y {num(res.loc[OCR[1], 'promedio_impreso'])} con Tesseract, y el WER promedio ronda {num(res.loc[mejor_asr, 'promedio'], 2)}. El texto queda buscable, como muestra la pestaña **🔎 Buscar**.
- **Parcialmente, para fotos y manuscritos.** PaddleOCR obtiene un CER de {num(res.loc[OCR[0], 'promedio_foto'])} en fotos y {num(res.loc[OCR[0], 'promedio_manuscrito'])} en manuscritos, y omite parte del texto. Tesseract casi no reconoce nada fuera de los impresos. Para que estos documentos sean realmente buscables hace falta revisión humana.
- **La estructura con un LLM local** funciona en formato (JSON válido en {D['ext']['json_valido'].sum()} de {len(D['ext'])} casos), pero no siempre en fidelidad. {a_txt}, así que los campos sirven para orientar, no como dato verificado.
""")
    with st.expander("Limitaciones que conviene tener en cuenta", icon=":material/warning:"):
        st.markdown("""
- **Referencias asistidas:** las referencias de la evaluación partieron de borradores asistidos (un LLM para documentos y wav2vec2 para audio). La autora las revisó, pero 17 de las 20 se aceptaron sin cambios. Los valores absolutos de CER y WER deben leerse con cautela; la comparación **entre modelos** es más robusta.
- **Muestras pequeñas:** solo 10 elementos por modalidad, por eso los resultados se acompañan de intervalos de confianza.
- **Hablantes:** la diarización automática **estima** cuántos hablantes hay. El número real sigue *pendiente de revisión* humana.
- **Seudonimización, no anonimización:** los nombres de personas contemporáneas se reemplazaron por marcadores como <span class="seud">[NOMBRE_3]</span>. Aun así, las fuentes públicas enlazadas, que hay que citar por su licencia, pueden permitir reidentificar a las personas.
""", unsafe_allow_html=True)
    with st.expander("Fuentes y licencias", icon=":material/license:"):
        filas = []
        for _, r in D["fuentes"].iterrows():
            url = r["fuente_url"] if str(r["fuente_url"]).startswith("http") else None
            enlace = f"[Ver en Wikimedia Commons]({url})" if url else PENDIENTE_TXT
            fecha = r["fecha_consulta"] if isinstance(r["fecha_consulta"], str) else "—"
            filas.append(f"| {r['id']} | {r['modalidad']} | {mostrar(r['licencia'])} | {enlace} | {mostrar(r['acceso'])} | {fecha} |")
        st.markdown("| id | Modalidad | Licencia | Fuente | Acceso | Consulta |\n|---|---|---|---|---|---|\n" + "\n".join(filas))
        st.caption("La atribución completa de cada obra (autor, título y licencia) está en datos/fuentes.csv y en la página "
                   "de origen enlazada, como permite la licencia CC BY 4.0, §3(a)(2). En entrevistas y documentos "
                   "contemporáneos, los nombres de las personas se retiraron de títulos y enlaces.")


def figura_wer(D) -> go.Figure:
    m = D["m_asr"]
    piv = m.pivot(index="id", columns="modelo", values="wer")
    orden = piv.sort_values(ASR[0]).index.tolist()
    fig = go.Figure()
    for id_, r in piv.iterrows():
        fig.add_scatter(x=[r[ASR[0]], r[ASR[1]]], y=[id_, id_], mode="lines", line=dict(color=NEUTRO, width=2),
                        hoverinfo="skip", showlegend=False)
    for modelo in ASR:
        d = m[m["modelo"] == modelo]
        fig.add_scatter(x=d["wer"], y=d["id"], mode="markers", name=modelo,
                        marker=dict(size=11, color=COLOR_MODELO[modelo], line=dict(width=2, color=ANILLO)),
                        customdata=np.c_[d["fuente"], d["S"], d["D"], d["I"], d["N"]],
                        hovertemplate="<b>%{y}</b> (%{customdata[0]})<br>" + modelo + ": WER %{x:.3f}<br>"
                                      "S %{customdata[1]} · D %{customdata[2]} · I %{customdata[3]} · N %{customdata[4]}<extra></extra>")
    fig.update_layout(xaxis=dict(title="WER", rangemode="tozero"),
                      yaxis=dict(categoryorder="array", categoryarray=orden, title=None))
    return fig


def tab_buscar(D) -> None:
    st.markdown("#### Buscar en todo el archivo")
    st.caption("Busca en el texto OCR de los 25 documentos y en las transcripciones de los 30 clips, todos "
               "seudonimizados. No distingue mayúsculas ni tildes: «peru» encuentra «Perú».")
    c1, c2, c3 = st.columns([3, 3, 2], vertical_alignment="bottom")
    consulta = c1.text_input("Término o frase", placeholder="p. ej.: patria, Lima, cultura, mujer…", key="consulta")
    ejemplo = c2.pills("Ejemplos", ["patria", "Lima", "cultura", "mujer", "Tarata"], key="ejemplo")
    alcance = c3.segmented_control("Buscar en", ["Todo", "Documentos", "Audios"], default="Todo", key="alcance")
    q = (consulta or "").strip() or (ejemplo or "")
    if len(q) < 2:
        st.caption("Escribe al menos 2 caracteres o elige un ejemplo.")
        return

    filas = []
    if alcance in ("Todo", "Documentos", None):
        for _, r in D["docs"].iterrows():
            pos = coincidencias(str(r["texto_ocr"]), q)
            if pos:
                filas.append(("documento", r["id"], f"{r['tipo']} · {r['epoca']}", str(r["texto_ocr"]), pos))
    if alcance in ("Todo", "Audios", None):
        for _, r in D["audio"].iterrows():
            pos = coincidencias(r["texto_plano"], q)
            if pos:
                filas.append(("audio", r["id"], r["fuente_etiqueta"], r["texto_plano"], pos))
    filas.sort(key=lambda f: -len(f[4]))
    n_doc = sum(f[0] == "documento" for f in filas)
    k = st.columns(3)
    k[0].metric("Elementos encontrados", len(filas))
    k[1].metric("Documentos", n_doc)
    k[2].metric("Clips de audio", len(filas) - n_doc)
    if not filas:
        st.warning(f"No hay coincidencias para «{q}».", icon=":material/search_off:")
        return

    tabla = pd.DataFrame([{"id": f[1], "modalidad": f[0], "detalle": f[2], "coincidencias": len(f[4]),
                           "fragmento": html.unescape(re.sub(r"<[^>]+>", "", fragmentos(f[3], f[4], maximo=1)[0]))}
                          for f in filas])
    descarga(tabla, f"busqueda_{normalizar(q).replace(' ', '_')}.csv", "Descargar resultados (CSV)", "dl_busqueda")
    for modalidad, id_, detalle, texto, pos in filas[:30]:
        with st.container(border=True):
            icono = "📄" if modalidad == "documento" else "🎙️"
            st.markdown(f"{icono} **{id_}** · {html.escape(detalle)} · {len(pos)} coincidencia{'s' if len(pos) > 1 else ''}")
            for frag in fragmentos(texto, pos):
                st.markdown(f'<div class="fragmento">{frag}</div>', unsafe_allow_html=True)
    if len(filas) > 30:
        st.caption(f"Se muestran 30 de {len(filas)} elementos; el CSV contiene todos.")


def tab_documentos(D) -> None:
    docs = D["docs"]
    st.markdown("#### Explorador de documentos")
    f1, f2, f3, f4 = st.columns([3, 2, 2, 2], vertical_alignment="bottom")
    tipos = f1.pills("Tipo", ORDEN_TIPO, selection_mode="multi", default=ORDEN_TIPO, key="doc_tipo")
    epocas = f2.pills("Época", sorted(docs["epoca"].unique()), selection_mode="multi",
                      default=sorted(docs["epoca"].unique()), key="doc_epoca")
    conf_min = f3.slider("Confianza OCR mínima", 0.0, 1.0, 0.0, 0.05, key="doc_conf")
    solo_muestra = f4.toggle("Solo muestra de evaluación", key="doc_muestra")
    sel = docs[docs["tipo"].isin(tipos or []) & docs["epoca"].isin(epocas or []) & (docs["confianza_media"] >= conf_min)]
    if solo_muestra:
        sel = sel[sel["en_muestra"]]
    st.caption(f"{len(sel)} de {len(docs)} documentos")
    if sel.empty:
        st.warning("Ningún documento cumple los filtros.", icon=":material/filter_alt_off:")
        return

    t1, t2 = st.columns([3, 2])
    with t1:
        vista = sel.assign(licencia=sel["licencia"].map(mostrar), cer_paddle=sel["cer_paddle"].map(metrica_txt),
                           cer_tesseract=sel["cer_tesseract"].map(metrica_txt),
                           fuente=sel["verificacion_fuente"])
        st.dataframe(vista[["id", "tipo", "epoca", "confianza_media", "n_caracteres", "tiempo_ocr_seg",
                            "cer_paddle", "cer_tesseract", "licencia", "fuente"]], hide_index=True, height=390,
                     column_config={
                         "epoca": "Época",
                         "confianza_media": st.column_config.ProgressColumn("Confianza OCR", min_value=0, max_value=1, format="%.2f"),
                         "n_caracteres": st.column_config.NumberColumn("Caracteres"),
                         "tiempo_ocr_seg": st.column_config.NumberColumn("Tiempo OCR (s)", format="%.1f"),
                         "cer_paddle": st.column_config.TextColumn("CER PaddleOCR", help="Solo muestra de evaluación (— = fuera de la muestra)"),
                         "cer_tesseract": st.column_config.TextColumn("CER Tesseract", help="Solo muestra de evaluación (— = fuera de la muestra)"),
                         "fuente": st.column_config.TextColumn("Fuente", help="El enlace está en la ficha del documento, más abajo"),
                     })
        descarga(sel.drop(columns=["en_muestra"]), "documentos_filtrados.csv", "Descargar documentos filtrados (CSV)", "dl_docs")
    with t2:
        titulo_grafico("Confianza del OCR por tipo de documento",
                       "Confianza media de PaddleOCR por documento; cada punto es un documento")
        fig = go.Figure()
        x = sel["tipo"].map({t: i for i, t in enumerate(ORDEN_TIPO)}).to_numpy(dtype=float)
        jitter = np.random.default_rng(7).uniform(-0.18, 0.18, len(sel))
        fig.add_scatter(x=x + jitter, y=sel["confianza_media"], mode="markers", showlegend=False,
                        marker=dict(size=11, color=CAT[0], line=dict(width=2, color=ANILLO)),
                        customdata=np.c_[sel["id"], sel["tipo"], sel["n_caracteres"]],
                        hovertemplate="<b>%{customdata[0]}</b> · %{customdata[1]}<br>Confianza %{y:.2f}<br>"
                                      "%{customdata[2]} caracteres<extra></extra>")
        fig.update_layout(xaxis=dict(tickmode="array", tickvals=[0, 1, 2], ticktext=ORDEN_TIPO, range=[-0.5, 2.5]),
                          yaxis=dict(title="Confianza media", range=[0.5, 1.02]))
        grafico(fig, alto=360, leyenda=False)

    st.divider()
    id_ = st.selectbox("Documento", sel["id"].tolist(), key="doc_sel",
                       format_func=lambda i: f"{i} · {sel.set_index('id').loc[i, 'tipo']} · confianza "
                                             f"{num(sel.set_index('id').loc[i, 'confianza_media'], 2)}")
    r = docs.set_index("id").loc[id_]
    izq, der = st.columns([3, 2])
    with izq:
        st.markdown(f"**Texto OCR de {id_}** (PaddleOCR, seudonimizado según su época)")
        with st.container(height=470, border=True):
            st.markdown(f'<div class="texto-fuente">{texto_html(r["texto_ocr"])}</div>', unsafe_allow_html=True)
        st.caption("La imagen original no se publica: es pesada y queda fuera del repositorio. Puede consultarse en la fuente enlazada.")
    with der:
        st.markdown("**Ficha**")
        ficha = {"Tipo": r["tipo"] + (" (mixto)" if r["es_mixto"] else ""), "Época": r["epoca"],
                 "Observación": mostrar(r["observacion_tipo"]) if isinstance(r["observacion_tipo"], str) else "—",
                 "Licencia": mostrar(r["licencia"]), "Dimensiones": f"{r['ancho_px']} × {r['alto_px']} px",
                 "Confianza OCR": num(r["confianza_media"], 2), "Tiempo OCR": f"{num(r['tiempo_ocr_seg'], 1)} s",
                 "Privacidad": f"{r['politica_privacidad']} · {r['n_reemplazos']} reemplazos",
                 "Revisión humana de privacidad": mostrar(r["revision_privacidad"])}
        tabla_campos(ficha)
        if isinstance(r["fuente_url"], str):
            st.link_button("Ver fuente en Wikimedia Commons", r["fuente_url"], icon=":material/open_in_new:")
        else:
            st.caption(f"Fuente: {PENDIENTE_TXT}")
        if r["en_muestra"]:
            st.markdown("**Evaluación (muestra congelada)**")
            m = st.columns(2)
            m[0].metric("CER PaddleOCR", num(r["cer_paddle"]))
            m[1].metric("CER Tesseract", num(r["cer_tesseract"]))
        st.markdown("**Extracción estructurada (LLM)**")
        extraccion_llm(D, id_)


def turnos_html(texto: str) -> str:
    partes = re.split(r"\[(HABLANTE_[\d?]+)\]", texto)
    turnos: list[list[str]] = []
    for hablante, contenido in zip(partes[1::2], partes[2::2]):
        contenido = contenido.strip()
        if turnos and turnos[-1][0] == hablante:
            turnos[-1][1] += " " + contenido
        elif contenido:
            turnos.append([hablante, contenido])
    filas = []
    for hablante, contenido in turnos:
        n = hablante.split("_")[1]
        color = CAT[int(n) - 1] if n.isdigit() and int(n) <= len(CAT) else NEUTRO
        etiqueta = "Sin asignar" if n == "?" else f"Hablante {n}"
        filas.append(f'<div class="turno"><div class="hab"><span class="punto" style="background:{color}"></span>'
                     f'{etiqueta}</div><div class="txt">{texto_html(contenido)}</div></div>')
    return "".join(filas)


def tab_audios(D) -> None:
    audio = D["audio"]
    st.markdown("#### Explorador de audios")
    f1, f2, f3 = st.columns([4, 2, 2], vertical_alignment="bottom")
    fuentes = sorted(audio["fuente_etiqueta"].unique())
    fuentes_sel = f1.multiselect("Fuente", fuentes, default=fuentes, key="aud_fuente")
    hablantes = sorted(audio["n_hablantes_estimado"].unique())
    hab_sel = f2.pills("Hablantes estimados", hablantes, selection_mode="multi", default=hablantes, key="aud_hab")
    solo_muestra = f3.toggle("Solo muestra de evaluación", key="aud_muestra")
    sel = audio[audio["fuente_etiqueta"].isin(fuentes_sel) & audio["n_hablantes_estimado"].isin(hab_sel or [])]
    if solo_muestra:
        sel = sel[sel["en_muestra"]]
    st.caption(f"{len(sel)} de {len(audio)} clips · {num(sel['duracion_seg'].sum() / 60, 1)} min")
    if sel.empty:
        st.warning("Ningún clip cumple los filtros.", icon=":material/filter_alt_off:")
        return

    t1, t2 = st.columns([3, 2])
    with t1:
        vista = sel.assign(idioma=sel["idioma"].map(mostrar), wer_whisper=sel["wer_whisper"].map(metrica_txt),
                           wer_parakeet=sel["wer_parakeet"].map(metrica_txt))
        st.dataframe(vista[["id", "fuente_etiqueta", "inicio_s", "duracion_seg", "n_palabras", "n_hablantes_estimado",
                            "idioma", "pct_voz_vad", "rtf", "wer_whisper", "wer_parakeet", "licencia", "fuente_url"]],
                     hide_index=True, height=390,
                     column_config={
                         "fuente_etiqueta": "Fuente",
                         "inicio_s": st.column_config.NumberColumn("Inicio en la fuente (s)", format="%.1f"),
                         "duracion_seg": st.column_config.NumberColumn("Duración (s)", format="%.1f"),
                         "n_palabras": st.column_config.NumberColumn("Palabras"),
                         "n_hablantes_estimado": st.column_config.NumberColumn("Hablantes (estimado)", help="Diarización automática; el número real está pendiente de revisión humana"),
                         "idioma": "Idioma",
                         "pct_voz_vad": st.column_config.ProgressColumn("Voz (VAD)", min_value=0, max_value=100, format="%.0f %%"),
                         "rtf": st.column_config.NumberColumn("RTF Whisper", format="%.2f"),
                         "wer_whisper": st.column_config.TextColumn("WER Whisper", help="Solo muestra de evaluación (— = fuera de la muestra)"),
                         "wer_parakeet": st.column_config.TextColumn("WER Parakeet", help="Solo muestra de evaluación (— = fuera de la muestra)"),
                         "fuente_url": st.column_config.LinkColumn("Fuente", display_text="Commons ↗"),
                     })
        descarga(sel.drop(columns=["en_muestra", "texto_plano"]), "audios_filtrados.csv",
                 "Descargar clips filtrados (CSV)", "dl_audio")
    with t2:
        titulo_grafico("Minutos de audio por fuente", "Suma de la duración de los clips filtrados")
        por_fuente = sel.groupby("fuente_etiqueta").agg(minutos=("duracion_seg", lambda s: s.sum() / 60),
                                                        clips=("id", "count")).sort_values("minutos")
        fig = go.Figure(go.Bar(x=por_fuente["minutos"], y=por_fuente.index, orientation="h",
                               marker=dict(color=CAT[0], cornerradius=4), text=[num(v, 1) for v in por_fuente["minutos"]],
                               textposition="outside", customdata=por_fuente["clips"],
                               hovertemplate="%{y}<br>%{x:.1f} min · %{customdata} clips<extra></extra>"))
        fig.update_layout(xaxis=dict(title="Minutos", range=[0, por_fuente["minutos"].max() * 1.2]), yaxis=dict(title=None))
        grafico(fig, alto=360, leyenda=False, rejilla_x=True)

    st.divider()
    id_ = st.selectbox("Clip", sel["id"].tolist(), key="aud_sel",
                       format_func=lambda i: f"{i} · {sel.set_index('id').loc[i, 'fuente_etiqueta']}")
    r = audio.set_index("id").loc[id_]
    izq, der = st.columns([3, 2])
    with izq:
        st.markdown(f"**Transcripción diarizada de {id_}** (faster-whisper small + diarización, seudonimizada)")
        with st.container(height=470, border=True):
            st.markdown(turnos_html(str(r["texto_asr_diarizado"])), unsafe_allow_html=True)
        st.caption("El audio no se publica (privacidad y peso). La entrevista original puede escucharse en la fuente enlazada.")
    with der:
        st.markdown("**Ficha**")
        ficha = {"Fuente": r["fuente_etiqueta"], "Licencia": mostrar(r["licencia"]),
                 "Tramo en la fuente": f"{num(r['inicio_s'], 1)} s → {num(r['inicio_s'] + r['duracion_seg'], 1)} s",
                 "Idioma (revisado)": mostrar(r["idioma"]),
                 "Idioma detectado": f"{r['idioma_detectado_libre']} (p = {num(r['idioma_detectado_prob'], 2)})",
                 "Hablantes (estimado)": f"{r['n_hablantes_estimado']} · {r['hablantes_en_clip']}",
                 "Hablantes (revisado)": mostrar(r["n_hablantes"]),
                 "Voz detectada (VAD)": f"{num(r['pct_voz_vad'], 0)} %",
                 "RTF · latencia": f"{num(r['rtf'], 2)} · {num(r['latencia_primer_segmento_s'], 1)} s",
                 "Revisión humana de privacidad": mostrar(r["revision_privacidad"])}
        tabla_campos(ficha)
        if isinstance(r["fuente_url"], str):
            st.link_button("Ver fuente en Wikimedia Commons", r["fuente_url"], icon=":material/open_in_new:")
        if r["en_muestra"]:
            st.markdown("**Evaluación (muestra congelada)**")
            m = st.columns(2)
            m[0].metric("WER faster-whisper", num(r["wer_whisper"]))
            m[1].metric("WER Parakeet", num(r["wer_parakeet"]))
        st.markdown("**Extracción estructurada (LLM)**")
        extraccion_llm(D, id_)


def tab_evaluacion(D) -> None:
    res, comp, m_ocr, m_asr = D["resumen"].set_index("modelo"), D["comparacion"], D["m_ocr"], D["m_asr"]
    muestra = D["muestra"]
    st.markdown("#### Evaluación sobre la muestra congelada")
    st.caption(f"{(muestra['modalidad'] == 'documento').sum()} documentos y {(muestra['modalidad'] == 'audio').sum()} "
               f"clips elegidos con la semilla {muestra['semilla'].iloc[0]} y congelados el {muestra['fecha_congelacion'].iloc[0]}, "
               "antes de ejecutar los modelos alternativos. Las predicciones y los tiempos son salidas reales en caché.")
    c = st.columns(4)
    for i, modelo in enumerate(OCR + ASR):
        metrica = "CER" if modelo in OCR else "WER"
        c[i].metric(f"{metrica} {modelo}", num(res.loc[modelo, "promedio"]), border=True,
                    help=f"Promedio de {int(res.loc[modelo, 'n'])} elementos; ponderado por longitud: {num(res.loc[modelo, 'ponderado'])}")
    for _, r in comp.iterrows():
        signo = "**significativa**" if r["significativa"] else "**no significativa** (el intervalo incluye 0)"
        st.markdown(f"- {r['metrica']} {r['modelo_a']} − {r['modelo_b']} = {num(r['diferencia_media_a_menos_b'])} · "
                    f"IC 95 % bootstrap pareado [{num(r['ic95_inf'])}, {num(r['ic95_sup'])}]: {signo}. "
                    f"{r['modelo_a']} mejor en {r['a_mejor']}, {r['modelo_b']} en {r['b_mejor']}, empates {r['empates']}.")

    s1, s2, s3, s4 = st.tabs(["OCR · CER", "ASR · WER", "Eficiencia", "Casos difíciles"])
    with s1:
        titulo_grafico("CER por documento: PaddleOCR frente a Tesseract",
                       "Menor = mejor. Un CER de 1,0 significa no reconocer nada; Tesseract devuelve texto vacío en dos fotos")
        orden = (m_ocr.drop_duplicates("id").assign(o=lambda d: d["tipo"].map({t: i for i, t in enumerate(ORDEN_TIPO)}))
                 .sort_values(["o", "id"])["id"].tolist())
        fig = go.Figure()
        for modelo in OCR:
            d = m_ocr[m_ocr["modelo"] == modelo].set_index("id").loc[orden].reset_index()
            fig.add_bar(x=d["id"] + "<br>" + d["tipo"], y=d["cer"], name=modelo,
                        marker=dict(color=COLOR_MODELO[modelo], cornerradius=4),
                        customdata=np.c_[d["S"], d["D"], d["I"], d["N"]],
                        hovertemplate="<b>%{x}</b><br>" + modelo + ": CER %{y:.3f}<br>S %{customdata[0]} · "
                                      "D %{customdata[1]} · I %{customdata[2]} · N %{customdata[3]}<extra></extra>")
        fig.update_layout(barmode="group", yaxis=dict(title="CER", rangemode="tozero"))
        grafico(fig, alto=420)
        st.dataframe(m_ocr, hide_index=True, column_config={
            "cer": st.column_config.NumberColumn("CER", format="%.3f"),
            "cer_sin_tildes": st.column_config.NumberColumn("CER sin tildes", format="%.3f"),
            "caracteres_hipotesis": st.column_config.NumberColumn("Caracteres reconocidos"),
            "ilegible_en_referencia": st.column_config.NumberColumn("[ilegible] en la referencia"),
            "mejor_modelo_del_elemento": "Mejor modelo en el documento"})
        descarga(m_ocr, "metricas_ocr.csv", "Descargar métricas OCR (CSV)", "dl_mocr")
    with s2:
        titulo_grafico("WER por clip: faster-whisper frente a Parakeet",
                       "Menor = mejor; cada línea une los dos modelos sobre el mismo clip; un solo punto indica empate")
        grafico(figura_wer(D), alto=440, rejilla_x=True)
        st.dataframe(m_asr, hide_index=True, column_config={
            "wer": st.column_config.NumberColumn("WER", format="%.3f"),
            "duracion_s": st.column_config.NumberColumn("Duración (s)", format="%.1f"),
            "palabras_hipotesis": st.column_config.NumberColumn("Palabras reconocidas"),
            "inaudible_en_referencia": st.column_config.NumberColumn("[inaudible] en la referencia"),
            "referencia_revisada": "Revisión de la referencia",
            "mejor_modelo_del_elemento": "Mejor modelo en el clip"})
        descarga(m_asr, "metricas_asr.csv", "Descargar métricas ASR (CSV)", "dl_masr")
    with s3:
        efic = D["resumen"][["modalidad", "modelo", "metrica", "promedio", "tiempo_mediano_s", "rtf_mediano",
                             "estabilidad", "carga_modelo_s"]].copy()
        efic["estabilidad"] = efic["estabilidad"].str.replace("no medida", "No medida")
        efic["rtf_mediano"] = efic["rtf_mediano"].map(lambda v: "No aplica (OCR)" if pd.isna(v) else num(v))
        efic["carga_modelo_s"] = efic["carga_modelo_s"].map(lambda v: "No medida" if pd.isna(v) else num(v, 1))
        st.dataframe(efic, hide_index=True, column_config={
            "promedio": st.column_config.NumberColumn("CER / WER promedio", format="%.3f"),
            "tiempo_mediano_s": st.column_config.NumberColumn("Tiempo mediano por elemento (s)", format="%.1f"),
            "rtf_mediano": st.column_config.TextColumn("RTF mediano", help="Tiempo de proceso / duración del audio; < 1 = más rápido que tiempo real"),
            "estabilidad": st.column_config.TextColumn("Estabilidad (salida idéntica al repetir)"),
            "carga_modelo_s": st.column_config.TextColumn("Carga del modelo (s)")})
        st.caption(f"Los cuatro modelos se midieron en la misma sesión ({D['bench']['entorno'].iloc[0]}), una pasada por elemento después de un calentamiento.")
        st.markdown(f"""
- **OCR:** Tesseract tarda unos {num(res.loc[OCR[1], 'tiempo_mediano_s'], 0)} s por documento, frente a {num(res.loc[OCR[0], 'tiempo_mediano_s'], 0)} s de PaddleOCR (en CPU y sin oneDNN). Aun así, PaddleOCR es el único que da resultados útiles en fotos y manuscritos.
- **ASR:** Parakeet procesa unas {num(res.loc[ASR[0], 'rtf_mediano'] / res.loc[ASR[1], 'rtf_mediano'], 1)} veces más rápido que Whisper (RTF {num(res.loc[ASR[1], 'rtf_mediano'], 2)} frente a {num(res.loc[ASR[0], 'rtf_mediano'], 2)}) y es totalmente repetible. Whisper permite forzar el idioma, entrega las primeras palabras con menor latencia y da marcas de tiempo por palabra.
- **Recomendación:** un OCR híbrido, con Tesseract para impresos limpios y PaddleOCR para fotos y manuscritos. Para el audio, Parakeet en lotes, porque la precisión de ambos es estadísticamente equivalente.
""")
        descarga(D["bench"], "benchmark_tiempos.csv", "Descargar tiempos medidos (CSV)", "dl_bench")
        descarga(D["resumen"], "resumen_metricas.csv", "Descargar resumen de métricas (CSV)", "dl_resumen")
        descarga(comp, "comparacion_modelos_bootstrap.csv", "Descargar comparaciones con IC 95 % (CSV)", "dl_comp")
    with s4:
        docs_meta = D["docs"].set_index("id")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Documentos con mayor error (mejor modelo)**")
            peor = m_ocr.loc[m_ocr.groupby("id")["cer"].idxmin()].nlargest(3, "cer")
            for _, r in peor.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{r['id']}** · {r['tipo']} · CER {num(r['cer'])} ({r['modelo']})")
                    st.caption(f"{mostrar(docs_meta.loc[r['id'], 'observacion_tipo']) if isinstance(docs_meta.loc[r['id'], 'observacion_tipo'], str) else ''} "
                               f"Errores: S {r['S']} · D {r['D']} · I {r['I']} sobre N {r['N']}; "
                               f"{r['ilegible_en_referencia']} tramos [ilegible] en la referencia.")
        with c2:
            st.markdown("**Clips con mayor error (mejor modelo)**")
            peor = m_asr.loc[m_asr.groupby("id")["wer"].idxmin()].nlargest(3, "wer")
            for _, r in peor.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{r['id']}** · {r['fuente']} · WER {num(r['wer'])} ({r['modelo']})")
                    st.caption(f"Errores: S {r['S']} · D {r['D']} · I {r['I']} sobre N {r['N']}; "
                               f"{r['inaudible_en_referencia']} tramos [inaudible] en la referencia; referencia {r['referencia_revisada']}.")
        st.caption("Causas probables, analizadas en 02_evaluacion.ipynb: baja resolución, reflejos y caligrafía antigua en "
                   "documentos; música de fondo y varias voces en audio. Además, el CER penaliza el orden de lectura en "
                   "tablas, y las zonas [inaudible] de la referencia cuentan como inserciones.")

    with st.expander("Origen de las referencias (declaración de transparencia)", icon=":material/fact_check:"):
        ref = D["referencias"]
        resumen_ref = (ref.assign(origen=ref["origen_referencia"].str.split(";").str[0].str.split(":").str[0])
                       .groupby(["modalidad", "origen", "estado"]).size().rename("referencias").reset_index())
        st.dataframe(resumen_ref, hide_index=True)
        st.caption("Las referencias son borradores asistidos que la autora revisó: un LLM transcribió visualmente los documentos y "
                   "wav2vec2, que no se evalúa, transcribió el audio. Los errores que queden en ellas afectan por igual a los "
                   "dos modelos comparados.")


def tab_llm(D) -> None:
    ext, aud, acuerdo = D["ext"], D["auditoria"], D["acuerdo"]
    st.markdown("#### Extracción estructurada con LLM y auditoría humana")
    st.caption(f"Modelo local: {ext['modelo_llm'].iloc[0]}. Salida forzada a un esquema JSON y entrada seudonimizada. "
               "Si un campo no aparece en el texto, el LLM debe devolver null.")
    a = ext[ext["modalidad"] == "audio"]
    lit = a["verif_citas"].str.extract(r"(\d+)/(\d+)").astype(float)
    c = st.columns(4)
    c[0].metric("JSON válido", f"{ext['json_valido'].sum()}/{len(ext)}", border=True)
    c[1].metric("Citas literales", f"{int(lit[0].sum())}/{int(lit[1].sum())}", border=True,
                help="Citas clave que aparecen literalmente en la transcripción")
    c[2].metric("Hablantes = etiquetas", f"{(a['verif_hablantes'] == 'ok').sum()}/{len(a)}", border=True,
                help="numero_hablantes coincide con las etiquetas de diarización del texto")
    if acuerdo is not None:
        t = acuerdo.set_index("modalidad").loc["total"]
        c[3].metric("Acuerdo LLM-humano", pct(t["acuerdo"]), border=True,
                    help=f"IC 95 % de Wilson [{pct(t['ic95_inf'])}, {pct(t['ic95_sup'])}]; n = {t['n']}")
    else:
        c[3].metric("Acuerdo LLM-humano", PENDIENTE_TXT, border=True)

    g, txt = st.columns([2, 3], vertical_alignment="center")
    with g:
        titulo_grafico("Acuerdo LLM-humano por modalidad",
                       "Proporción de extracciones que la autora juzgó correctas, con IC 95 % de Wilson")
        if acuerdo is not None:
            d = acuerdo.copy()
            d["etiqueta"] = d["modalidad"].map({"documento": "Documentos", "audio": "Audios", "total": "Total"})
            fig = go.Figure(go.Bar(
                x=d["etiqueta"], y=d["acuerdo"], marker=dict(color=CAT[0], cornerradius=4),
                error_y=dict(type="data", symmetric=False, array=d["ic95_sup"] - d["acuerdo"],
                             arrayminus=d["acuerdo"] - d["ic95_inf"], color=NEUTRO, thickness=1.5, width=6),
                text=[f"{pct(v)} ({c_}/{n})" for v, c_, n in zip(d["acuerdo"], d["correctos"], d["n"])],
                textposition="inside", insidetextanchor="start",
                customdata=np.c_[d["ic95_inf"], d["ic95_sup"]],
                hovertemplate="%{x}: %{y:.0%}<br>IC 95 % [%{customdata[0]:.0%}, %{customdata[1]:.0%}]<extra></extra>"))
            fig.update_layout(yaxis=dict(title="Acuerdo", range=[0, 1], tickformat=".0%"))
            grafico(fig, alto=360, leyenda=False)
        else:
            st.info(f"Acuerdo LLM-humano: {PENDIENTE_TXT}.")
    with txt:
        st.markdown("""
**Qué muestran las 20 decisiones de la autora**
- En **documentos**, los errores vienen sobre todo de **interpretar de más un OCR deteriorado**, de mezclar fragmentos de un panel, del texto truncado y de una ausencia escrita como `"n/a"` en vez de `null`.
- En **audios**, el error típico es **contar un hablante de más** y, en menor medida, dar como cita una paráfrasis.
- Los 8 casos con alertas automáticas, como citas no literales o hablantes distintos de las etiquetas, fueron juzgados incorrectos. Los otros 2 errores son semánticos y ninguna regla los detecta.
- **Conclusión:** los campos del LLM orientan la búsqueda, pero **no son datos verificados**.
""")
    st.markdown("**Auditoría humana (20 casos)**")
    tabla = aud[["id", "modalidad", "correcto", "observacion"]].copy()
    tabla["correcto"] = tabla["correcto"].map({"SI": "✅ Correcta", "NO": "❌ Incorrecta"}).fillna(PENDIENTE_TXT)
    st.dataframe(tabla.fillna(""), hide_index=True, height=420, column_config={
        "modalidad": st.column_config.TextColumn("Modalidad", width="small"),
        "correcto": st.column_config.TextColumn("Decisión de la autora", width="small"),
        "observacion": st.column_config.TextColumn("Observación de la autora", width="large")})

    st.divider()
    id_ = st.selectbox("Ver la extracción de un elemento", ext["id"].tolist(), key="llm_sel")
    i1, i2 = st.columns([2, 3])
    with i1:
        extraccion_llm(D, id_)
    with i2:
        fila = aud.set_index("id")
        if id_ in fila.index:
            st.markdown("**Texto fuente que recibió el LLM** (seudonimizado)")
            with st.container(height=320, border=True):
                st.markdown(f'<div class="texto-fuente">{texto_html(fila.loc[id_, "texto_fuente"])}</div>', unsafe_allow_html=True)
        else:
            st.caption("El texto fuente completo de este elemento se ve en el explorador de documentos o de audios.")
    d1, d2, d3 = st.columns(3)
    with d1:
        descarga(ext, "extraccion_llm.csv", "Descargar extracciones (CSV)", "dl_ext")
    with d2:
        descarga(aud, "auditoria_llm.csv", "Descargar auditoría (CSV)", "dl_aud")
    with d3:
        if acuerdo is not None:
            descarga(acuerdo, "acuerdo_llm_humano.csv", "Descargar acuerdo (CSV)", "dl_acu")


# ---------------------------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------------------------
D = cargar()
st.markdown('<div class="cabecera"><h1>📜 Voces y documentos peruanos</h1>'
            "<p>Del archivo escaneado al texto buscable · OCR, ASR, diarización y extracción estructurada · "
            "Tarea 2 · Mirian de la Cruz Condori</p></div>", unsafe_allow_html=True)
b = st.container(horizontal=True)
with b:
    st.badge("Datos seudonimizados", icon=":material/shield_person:", color="green")
    st.badge("Solo resultados precalculados", icon=":material/database:", color="blue")
    st.badge("Fuentes: Wikimedia Commons", icon=":material/license:", color="gray")

with st.sidebar:
    st.markdown("### Sobre este tablero")
    st.markdown("""
Presenta los resultados **ya calculados** en los notebooks `01_extraccion.ipynb` y `02_evaluacion.ipynb`. No ejecuta ningún modelo.

**Qué se publica:**
- texto OCR y transcripciones **seudonimizados**;
- métricas, tiempos y extracciones del LLM;
- la auditoría humana.

**Qué no se publica:** audio, imágenes originales, pesos de modelos ni credenciales.

**Pendiente de revisión** indica un dato que requiere verificación humana y que no se completó automáticamente.
""")
    st.caption("Las descargas CSV contienen solo columnas publicables.")

tabs = st.tabs(["🏠 Resumen", "🔎 Buscar", "📄 Documentos", "🎙️ Audios", "📊 Evaluación", "🧠 Extracción LLM"])
with tabs[0]:
    tab_resumen(D)
with tabs[1]:
    tab_buscar(D)
with tabs[2]:
    tab_documentos(D)
with tabs[3]:
    tab_audios(D)
with tabs[4]:
    tab_evaluacion(D)
with tabs[5]:
    tab_llm(D)
