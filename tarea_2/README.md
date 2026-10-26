# Voces y documentos peruanos: del archivo escaneado al texto buscable

> **Pregunta guía:** ¿Podemos convertir documentos escaneados y entrevistas en audio en un archivo de texto estructurado y buscable?

- **Autora:** Mirian de la Cruz Condori · Diplomado Python · Tarea 2
- **Dashboard público:** https://tarea-2-voces-documentos-peruanos-r8jc6xclfjwul2hee65ex2.streamlit.app/
- **Repositorio:** https://github.com/miriandelacon13-ux/tarea-2-voces-documentos-peruanos
- **Notebooks:** [`01_extraccion.ipynb`](01_extraccion.ipynb) (corpus, OCR, ASR, diarización, privacidad, EDA) · [`02_evaluacion.ipynb`](02_evaluacion.ipynb) (CER, WER, eficiencia, LLM, auditoría)

| | Resultado (datos reales de este repositorio) |
|---|---|
| **Corpus** | 25 documentos (8 impresos, 8 fotos, 9 manuscritos) y 30 clips con **36,72 min** de español peruano |
| **OCR** | PaddleOCR: CER **0,295** frente a Tesseract **0,659**. La diferencia es significativa: IC 95 % [−0,567, −0,176] |
| **ASR** | Parakeet: WER **0,309** frente a faster-whisper **0,326**. La diferencia no es significativa: IC 95 % [−0,014, +0,059] |
| **LLM** | JSON válido en 55/55 casos; **acuerdo LLM-humano 50 %** (10/20): documentos 40 %, audios 60 % |
| **Respuesta corta** | **Sí** para impresos y habla clara. **Parcialmente** para fotos y manuscritos. Los campos del LLM orientan, pero no reemplazan la revisión humana |

---

## Contenido
1. [Objetivo](#1-objetivo)
2. [Corpus, fuentes y licencias](#2-corpus-fuentes-y-licencias)
3. [Estructura del repositorio](#3-estructura-del-repositorio)
4. [Metodología](#4-metodología)
5. [Resultados](#5-resultados)
6. [Hallazgos principales y limitaciones](#6-hallazgos-principales-y-limitaciones)
7. [Privacidad, seudonimización y ética](#7-privacidad-seudonimización-y-ética)
8. [Instalación, ejecución y reproducibilidad](#8-instalación-ejecución-y-reproducibilidad)
9. [Cómo usar el dashboard](#9-cómo-usar-el-dashboard)
10. [Uso de asistencia de IA](#10-uso-de-asistencia-de-ia)

---

## 1. Objetivo

Construir, a partir de fuentes abiertas, un pequeño archivo peruano **buscable y estructurado**:
1. extraer el texto de documentos escaneados (OCR) y de entrevistas (ASR con diarización);
2. proteger los datos personales;
3. **medir** la calidad contra referencias revisadas por la autora, en una muestra fija;
4. estructurar el contenido con un LLM local y auditarlo;
5. presentar todo en un dashboard que solo usa resultados precalculados.

## 2. Corpus, fuentes y licencias

| Modalidad | Cantidad | Detalle |
|---|---|---|
| Documentos | **25** | 8 impresos · 8 fotos (vitrinas, relieves, pantallas, iluminación desigual) · 9 manuscritos. 21 históricos (antes de 1950) y 4 contemporáneos |
| Audio | **30 clips · 36,72 min** | 7 fuentes (A–G), clips de 58 a 89 s, en español peruano: entrevistas callejeras, una ceremonia patronal y una conferencia de prensa |
| Multihablante | **18 clips** | Con 2 o más hablantes según la diarización: 16 con 2 y 2 con 3 |
| Texto extraído | 35 634 caracteres de OCR · 5 038 palabras de ASR | |

**Control de calidad del corpus**
- **Duplicados:** se revisaron por SHA-256 y no hay ninguno.
- **Clips descartados (20):** los primeros clips estaban vacíos (3–13 ms) por un desfase en las marcas de tiempo de los WebM grabados con VLC. Se regeneraron a partir del audio normalizado y el registro está en `datos/reportes/descartes*.csv`.
- **Duración real:** se verificó con `ffprobe` y decodificación completa, porque Commons sobrestimaba la duración de 4 archivos.

**Fuentes.** Todo el material proviene de Wikimedia Commons:
- **Audio:** las 7 fuentes están verificadas por SHA-1.
- **Documentos:** 19 de 25 están verificados por SHA-1.
- **Pendientes:** en 6 documentos (doc_005, doc_006, doc_007, doc_009, doc_010 y doc_021) la fuente y la licencia quedan como `PENDIENTE_REVISION_HUMANA`, porque la autora debe aportar la URL de origen y no se inventaron.

| Licencia | Fuentes |
|---|---|
| CC BY-SA 4.0 | 11 (5 documentos y 6 audios) |
| Dominio público | 10 documentos |
| CC BY 4.0 / CC BY 2.0 | 2 + 1 documentos |
| CC0 | 1 documento y 1 audio |
| `PENDIENTE_REVISION_HUMANA` | 6 documentos |

La atribución completa (autor, licencia y enlace) está en [`datos/fuentes.csv`](datos/fuentes.csv).

**Obras derivadas:** el OCR, las transcripciones y las extracciones derivan de las fuentes y **conservan su licencia**. Lo derivado de obras CC BY-SA se comparte bajo **CC BY-SA 4.0**. Los cambios realizados fueron:
- transcripción automática;
- segmentación en clips;
- seudonimización de nombres;
- en entrevistas y en doc_013, retiro del nombre de la persona del título y uso del enlace estable `?curid=` (ver §7).

## 3. Estructura del repositorio

```
tarea_2/
├── 01_extraccion.ipynb        # Parte 1: corpus, OCR, ASR, diarización, seudonimización, EDA (ejecutado)
├── 02_evaluacion.ipynb        # Parte 2: muestra fija, CER/WER, eficiencia, LLM, auditoría (ejecutado)
├── app.py                     # Parte 3: dashboard Streamlit (solo resultados precalculados)
├── requirements.txt           # dependencias mínimas del dashboard
├── requirements-procesamiento.txt / .lock.txt   # dependencias del procesamiento completo
├── README.md
├── .gitignore
├── evidencias_ia/             # capturas y registros del uso de asistencia de IA
├── scripts/                   # 00–17: pipeline reproducible + módulos (ocr, asr, diarizacion, privacidad, evaluacion, metricas)
├── datos/
│   ├── documentos.csv         # OCR seudonimizado por documento
│   ├── transcripciones.csv    # ASR + diarización seudonimizados por clip
│   ├── extraccion_llm.csv     # JSON estructurado (55 elementos)
│   ├── auditoria_llm.csv      # 20 casos auditados por la autora
│   ├── fuentes.csv            # fuente, licencia, autor y SHA de cada archivo
│   ├── muestra_evaluacion.csv # muestra congelada (10 + 10)
│   ├── reportes/              # integridad, clips, tiempos, métricas, acuerdo, auditoría de privacidad…
│   └── raw/                   # NO versionado: originales, audio, cachés, referencias, mapas privados
└── modelos/                   # NO versionado: pesos de PaddleOCR, Parakeet, diarización, tessdata
```

## 4. Metodología

### 4.1 OCR
- **Principal:** **PaddleOCR 3.7.0** (PP-OCRv6 *medium*, `lang="es"`), en CPU.
  - Sin módulos geométricos (orientación, enderezado).
  - `enable_mkldnn=False`, por un error de oneDNN en paddle 3.3.1.
  - Confianza media 0,869: impresos 0,962, fotos 0,881 y manuscritos 0,775.
  - Tiempo total 10,2 h. El mapa doc_025, de unos 93 MP, tardó 9,5 h; el resto suma 0,74 h.
- **Alternativo (evaluación):** **Tesseract 5.4.0** con `spa` de *tessdata_best*, `--psm 3 --oem 1`, sin preprocesamiento.

### 4.2 ASR
- **Principal:** **faster-whisper small**, `int8`, en CPU.
  - Configuración: `language="es"`, `beam_size=5`, VAD y marcas de tiempo por palabra.
  - RTF mediano 0,26; latencia mediana al primer segmento 5,1 s.
- **Alternativo (evaluación):** **NVIDIA Parakeet TDT 0.6B v3** (CC-BY-4.0), en ONNX `int8` con sherpa-onnx.

### 4.3 Diarización
- **Herramientas:** sherpa-onnx con *pyannote segmentation-3.0* y WeSpeaker ResNet34-LM, agrupamiento automático con umbral 0,5.
- **Salida:** etiquetas `[HABLANTE_k]`.
- **Estimación:** 12 clips con 1 hablante, 16 con 2 y 2 con 3. El número **real** de hablantes queda `PENDIENTE_REVISION_HUMANA`, y en la fuente G la diarización subestima.

### 4.4 Seudonimización
- **Detección:** expresiones regulares (correo, DNI con contexto, teléfono, dirección) y NER `es_core_news_md`.
- **Marcadores:** `[NOMBRE_n]` consistentes en todo el corpus.
- **Política por época (Ley 29733):**
  - documentos **históricos**: solo correo, teléfono y DNI, porque los nombres de figuras históricas tienen valor documental;
  - documentos **contemporáneos** (doc_013, 021, 022 y 023) y **todo el audio**: seudonimización completa.
- **Resultado:** 52 reemplazos (25 en documentos contemporáneos y 27 en audio).
- **Verificación:** 0 fugas automáticas. El mapa nombre → marcador solo existe en `datos/raw/privacidad/` (no versionado).

### 4.5 Evaluación (CER/WER)
- **Muestra fija:**
  - 10 documentos (3 impresos, 3 fotos y 4 manuscritos) y 10 clips, elegidos con la semilla 20261024 por estrato;
  - versionada en el commit `cddecce` **antes** de ejecutar los modelos alternativos;
  - doc_025 se excluyó *a priori*: es un mapa con unos 1 400 rótulos y su referencia manual completa no era factible.
- **Referencias:** el validador solo acepta un estado `REVISADO_SIN_CAMBIOS` o `REVISADO_CON_CAMBIOS` coherente con la huella del borrador. Su origen se declara con transparencia:

  | Referencias | Origen | Revisión de la autora |
  |---|---|---|
  | 10 documentos | Borrador de transcripción visual hecho por un LLM (Claude) | Aceptadas sin cambios |
  | 7 audios | Borrador de un ASR auxiliar no evaluado (wav2vec2-large-xlsr-53-spanish) | Aceptadas sin cambios |
  | 3 audios (aud_002, aud_019 y aud_028) | El mismo borrador | **Corregidas escuchando** |

- **Normalización:** idéntica para la referencia y para todos los modelos (`scripts/evaluacion.py`, 14 autopruebas):
  - NFC, minúsculas y sin puntuación;
  - sin etiquetas `[…]`;
  - cifras convertidas a palabras y sin muletillas, solo para el WER.
- **Fórmulas** (menor es mejor):
  - CER = (S + D + I) / N caracteres; también se informa el CER sin tildes.
  - WER = (S + D + I) / N palabras.
  - RTF = tiempo de proceso / duración del audio.
- **Incertidumbre:** IC 95 % por **bootstrap pareado** (10 000 remuestreos, semilla 2026).

### 4.6 Extracción estructurada con LLM y auditoría humana
- **Modelo:** **qwen2.5:3b** local (Ollama 0.40.8), con `temperature=0`, `seed=42` y salida forzada a un esquema JSON.
- **Entrada:** el texto **seudonimizado**.
- **Campos:**
  - en todos los casos: `modalidad`, `tema` y `resumen`;
  - en documentos, solo si aparecen: `emisor`, `fecha` y `monto`;
  - en audios: `citas_clave` y `numero_hablantes`;
  - si un dato no existe, `null`.
- **Verificaciones automáticas:** que las citas sean literales, que las cifras de fecha y monto estén en el texto, y que el número de hablantes coincida con las etiquetas.
- **Auditoría:** la autora revisó 20 casos (10 documentos y 10 audios, semilla 20261025) y respondió SI o NO con una observación (`datos/respuestas_auditoria_llm.txt`).

## 5. Resultados

**OCR · CER promedio por tipo** (muestra de 10 documentos)

| Modelo | Global | Ponderado | Impresos | Fotos | Manuscritos | Tiempo mediano/doc |
|---|---|---|---|---|---|---|
| **PaddleOCR** | **0,295** | 0,322 | 0,011 | **0,365** | **0,455** | 109,7 s |
| Tesseract | 0,659 | 0,636 | **0,004** | 0,989 | 0,903 | **4,0 s** |

- PaddleOCR es mejor en 8 de 10 documentos.
- Tesseract devuelve **0 caracteres** en doc_008 (vitrina) y en doc_011 (relieve).
- El CER sin tildes casi no cambia (0,292), así que las tildes no explican los errores.

**ASR · WER promedio** (muestra de 10 clips)

| Modelo | WER | Ponderado | Tiempo mediano/clip | RTF mediano | Estabilidad |
|---|---|---|---|---|---|
| faster-whisper small | 0,326 | 0,307 | 19,9 s | 0,286 | 9/10 |
| **Parakeet TDT 0.6B v3** | **0,309** | **0,297** | **10,6 s** | **0,143** | **10/10** |

- Parakeet es mejor en 5 clips, Whisper en 2, y empatan en 3.
- Estabilidad significa que, al repetir, la salida es idéntica.

**Casos difíciles** (CER y WER del mejor modelo)
- **doc_001, CER 0,742:** manuscrito de 1821 con firmas superpuestas.
- **doc_008, CER 0,722:** tabla bajo vidrio. Además, el CER penaliza el orden de lectura.
- **doc_015, CER 0,569:** cursiva de 1840.
- **aud_019, WER 0,684:** ceremonia con música. Whisper inserta o alucina texto y Parakeet omite.

**Extracción LLM**

| Indicador | Valor |
|---|---|
| JSON válido con todas las claves | 55/55 |
| Citas clave literales | 84/89 (94 %) |
| `numero_hablantes` = etiquetas de diarización | 14/30 |
| **Acuerdo LLM-humano total** | **10/20 = 50 %** (IC 95 % de Wilson [30 %, 70 %]) |
| Acuerdo en documentos | 4/10 = 40 % [17 %, 69 %] |
| Acuerdo en audios | 6/10 = 60 % [31 %, 83 %] |

- Los 8 casos con alertas automáticas fueron juzgados incorrectos.
- Los 2 errores sin alertas (doc_013 y doc_019) son **semánticos**: un tema mal sustentado y fragmentos mezclados.

**Recomendación**
- **OCR híbrido:** Tesseract para impresos limpios, porque es igual de preciso y unas 27 veces más rápido, y PaddleOCR para fotos y manuscritos.
- **Audio:** Parakeet para lotes, porque es dos veces más rápido y repetible. Whisper cuando se necesite forzar el idioma, baja latencia o marcas por palabra.

## 6. Hallazgos principales y limitaciones

**Hallazgos**
1. **La dificultad depende del tipo de documento, no del motor.**
   - En impresos ambos OCR son casi perfectos (CER ≤ 0,011).
   - Fuera de los impresos Tesseract colapsa (≈ 0,9–1,0), mientras PaddleOCR mantiene un texto útil en fotos (0,37).
   - Los manuscritos siguen abiertos (0,46): PaddleOCR omite cerca de la mitad del texto.
2. **Un LLM pequeño produce estructura válida, pero solo la mitad de las extracciones es fiel.**
   - Hereda los errores del OCR, interpreta de más los textos deteriorados y suele contar un hablante de más.
   - Las alertas automáticas sirven para priorizar la revisión humana, no para reemplazarla.

**Limitaciones técnicas**
1. **Referencias asistidas:**
   - 17 de las 20 referencias son borradores (LLM o wav2vec2) aceptados sin cambios.
   - Sus errores y zonas `[inaudible]`/`[ilegible]` inflan el CER y el WER **de ambos modelos por igual**, así que la comparación entre modelos es más robusta que el valor absoluto.
   - Entre el 42 y el 44 % de los errores de ASR son inserciones en zonas `[inaudible]`.
2. **Muestra pequeña y CPU:**
   - Con 10 elementos por modalidad, la diferencia entre los ASR no es significativa y los intervalos del acuerdo LLM-humano son amplios.
   - PaddleOCR corrió en CPU sin oneDNN, con tiempos muy variables (de 20 s a 9,5 h).

**Otras:**
- la diarización subestima en la fuente G;
- la auditoría LLM la hizo una sola revisora que veía las alertas;
- en 6 documentos la fuente sigue pendiente.

## 7. Privacidad, seudonimización y ética

- **Qué se publica:** texto OCR y transcripciones **seudonimizados**, métricas y extracciones.
- **Qué no se publica:** audio, imágenes originales, pesos de modelos, el mapa nombre → marcador, credenciales ni el material privado de revisión (todo en `datos/raw/` y `modelos/`, ignorados por git).
- **Metadatos de Commons:** algunos contenían el nombre de una persona protegida:
  - los títulos de cuatro entrevistas (A, B, C y F);
  - los metadatos de doc_013;
  - el crédito de autor de doc_022 y doc_023, porque esa persona figura, seudonimizada, en el texto del acta.
- **Corrección** (`scripts/17_preparar_publicacion.py`):
  - reemplaza esos nombres por marcadores (`[PERSONA_ENTREVISTADA_A]`, `[AUTOR_SEUDONIMIZADO]`, …);
  - cambia las URL afectadas por la URL estable `https://commons.wikimedia.org/w/index.php?curid=<pageid>`, que lleva a la página con la atribución completa, como permite CC BY y CC BY-SA 4.0 §3(a)(2).
- **Lo que se conserva por licencia:** los demás créditos de autoría que exigen las licencias CC BY y CC BY-SA (quienes crearon o subieron las obras). Se verificó que no coinciden con ninguna persona seudonimizada.
- **Historial de git:** antes de publicar se reescribió para aplicar la misma redacción a cada commit y usar el correo *noreply* de GitHub de la autora. Se conservaron los 12 commits, sus mensajes y fechas; la muestra congelada quedó en el commit `cddecce`.
- **Detalle de la auditoría:** [`datos/reportes/auditoria_privacidad.md`](datos/reportes/auditoria_privacidad.md).
- **Seudonimización no es anonimización:** quien siga un enlace de atribución verá la fuente pública original. El objetivo es no **propagar** datos personales en el dataset derivado.
- **Revisión humana de privacidad:** la autora revisó los textos seudonimizados en el dashboard el 2026-10-25 (`revision_privacidad = REVISADO_HUMANAMENTE`).
- **Ética:** los resultados malos no se eliminaron y nada se completó con datos inventados. Lo que no se pudo verificar figura como `PENDIENTE_REVISION_HUMANA`.

## 8. Instalación, ejecución y reproducibilidad

**Dashboard (solo necesita este repositorio).** Desde la raíz del repositorio:

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (Linux/macOS: source .venv/bin/activate)
pip install -r tarea_2/requirements.txt
streamlit run tarea_2/app.py      # http://localhost:8501
```

**Pipeline completo** (Python 3.13; requiere los datos originales y los modelos, que no se versionan):

1. **Instalación:**
   - `pip install -r tarea_2/requirements-procesamiento.txt` (versiones exactas en `requirements-procesamiento.lock.txt`);
   - además: FFmpeg, Tesseract 5.4 con `spa.traineddata` (*tessdata_best*) en `modelos/tessdata` y Ollama con `qwen2.5:3b`.
2. **Corpus:**
   - `scripts/00_copiar_originales.py`;
   - `00b_descargar_audio_adicional.py` y `01_metadatos_commons.py` (consultan Commons por *pageid*);
   - `02_normalizar_audio.py` a `05_clasificar_documentos.py`.
3. **Publicación:** `scripts/17_preparar_publicacion.py`. Retira los nombres de títulos y metadatos; es idempotente.
4. **Extracción:**
   - `06_ejecutar_ocr.py` y `07_ejecutar_asr.py` (guardan caché en `datos/raw/cache/`);
   - luego `01_extraccion.ipynb` (diarización, seudonimización, EDA y CSV finales).
5. **Evaluación:**
   - `08_muestra_evaluacion.py` (muestra fija) a `16_guia_auditoria_llm.py`;
   - luego `02_evaluacion.ipynb`.
6. **Antes de publicar:** `python scripts/17_preparar_publicacion.py --verificar`, que debe responder «0 nombres».

**Reproducibilidad:**
- semillas fijas (muestra 20261024, auditoría 20261025, bootstrap 2026, LLM `seed=42`);
- versiones exactas en el *lock*;
- SHA-1 y SHA-256 de cada archivo fuente en `datos/fuentes.csv`;
- tiempos medidos en `datos/reportes/benchmark_tiempos.csv`.
- Los notebooks se ejecutan con `--ExecutePreprocessor.timeout=180` y reutilizan las cachés: no repiten el OCR ni el ASR.

## 9. Cómo usar el dashboard

| Pestaña | Para qué sirve |
|---|---|
| 🏠 **Resumen** | Indicadores del corpus y de la calidad (CER, WER, acuerdo LLM-humano), dos gráficos clave, respuesta a la pregunta guía, limitaciones, y fuentes y licencias |
| 🔎 **Buscar** | Búsqueda de texto completo en los 25 documentos y 30 clips, sin distinguir mayúsculas ni tildes, con fragmentos resaltados y descarga de resultados |
| 📄 **Documentos** | Filtros por tipo, época, confianza y muestra; tabla; gráfico de confianza; ficha de cada documento con el texto OCR, el CER y los campos del LLM |
| 🎙️ **Audios** | Filtros por fuente, hablantes y muestra; minutos por fuente; transcripción por turnos de hablante, WER y campos del LLM |
| 📊 **Evaluación** | CER y WER con IC 95 %, gráficos por elemento, eficiencia (tiempo, RTF, estabilidad), casos difíciles y origen de las referencias |
| 🧠 **Extracción LLM** | Indicadores del LLM, acuerdo por modalidad con IC, la auditoría de la autora y un explorador de las 55 extracciones |

- Los marcadores <code>[NOMBRE_n]</code> aparecen resaltados.
- "Pendiente de revisión" indica un dato que requiere verificación humana.
- Todas las tablas se pueden descargar en CSV y contienen solo columnas publicables.

## 10. Uso de asistencia de IA

El proyecto se desarrolló con la asistencia de **Claude Code** (Anthropic): scripts, notebooks, dashboard y documentación. Las capturas y registros están en [`evidencias_ia/`](evidencias_ia/).

**Decisiones humanas de la autora:**
- aprobar la clasificación documental;
- revisar y corregir las referencias;
- auditar las 20 extracciones del LLM;
- aprobar cada commit.

El borrador de las referencias de documentos lo hizo un LLM y así se declara en §4.5. Ninguna métrica ni resultado se completó sin una ejecución real.
