# Guía para las referencias manuales (verdad de referencia)

Las referencias son la **verdad de referencia humana** para calcular el CER (documentos) y el WER (audio) en `02_evaluacion.ipynb`. Mientras una referencia diga `PENDIENTE_REVISION_HUMANA`, **no se calcula ninguna métrica** sobre ese elemento.

## Dónde escribir
- **Documentos:** `datos/raw/referencias/documentos/<id>.txt`. La imagen se abre desde `datos/raw/documentos/`.
- **Audio:** `datos/raw/referencias/audio/<id>.txt`. El clip se escucha desde `datos/raw/audio/clips/`.
- Cada archivo empieza con la única línea `PENDIENTE_REVISION_HUMANA`. **Reemplázala por completo** con tu transcripción y guarda el archivo en **UTF-8**.
- La carpeta `datos/raw/` no se sube a GitHub, porque las referencias pueden contener nombres reales. Lo que se publica es la versión seudonimizada.
- La validación técnica de cada referencia está en `datos/referencias_estado.csv`, que se regenera con `python scripts/09_preparar_referencias.py`.
- El estado de revisión lo gestiona la autora en `datos/reportes/control_referencias.csv`: `REVISADO_CON_CAMBIOS` (corregida) o `REVISADO_SIN_CAMBIOS` (revisada y correcta). Una referencia entra en el CER o el WER **solo** si tiene texto válido **y** su estado es consistente con la huella del borrador (`09_preparar_referencias.py` lo comprueba y marca INCONSISTENTE lo que no cuadre). La lista de revisión dirigida está en `datos/REVISION_RAPIDA_REFERENCIAS.md` (privada, no versionada).
- La lista de los 20 casos con sus rutas, duraciones y material de apoyo (tiras ampliadas y fragmentos de audio) está en `datos/GUIA_REVISION_REFERENCIAS.md`.

## Regla de independencia (obligatoria)
**No mires** la salida de PaddleOCR, Tesseract, Whisper ni Parakeet mientras transcribes; tampoco abras `datos/documentos.csv` ni `datos/transcripciones.csv`. Transcribe solo a partir de la imagen o del audio originales. Copiar o corregir la salida de un modelo sesgaría la evaluación a su favor.

## Documentos (CER)
1. Transcribe **todo el texto legible** de la imagen a resolución completa, en orden de lectura: de arriba abajo y de izquierda a derecha; si hay columnas, primero la izquierda. Incluye encabezados, membretes, sellos y fechas legibles.
2. **Conserva la ortografía original**, sin modernizarla ni corregirla: si dice «Setbre» o «autorisado», escribe eso. Respeta las tildes tal como aparecen.
3. Si una palabra es dudosa, escribe tu mejor lectura. Usa `[ilegible]` solo cuando no puedas leer la palabra en absoluto.
4. Los saltos de línea y los espacios pueden ir como en el original, porque la normalización los unifica. Las palabras cortadas con guion a final de línea se pueden escribir tal cual.
5. Las firmas solo se transcriben si son legibles como texto.

## Audio (WER)
1. Transcribe **literalmente** las palabras dichas, en el orden en que se dicen, incluidas las repeticiones.
2. **Omite** las muletillas no léxicas (*eh*, *em*, *mmm*). La normalización también las elimina de las hipótesis de los modelos.
3. Los números pueden ir en cifras o en letras: para el WER la normalización convierte las cifras en palabras en ambos textos.
4. Los nombres propios se escriben como los oigas, ya que este archivo es privado.
5. Para lo que no se entienda, usa `[inaudible]`; si dos personas hablan a la vez, transcribe al hablante principal y marca `[solapamiento]`.
6. *Opcional, para revisar la diarización:* puedes marcar los cambios de voz con `[HABLANTE_1]`, `[HABLANTE_2]`, etc. Estas etiquetas se eliminan antes de calcular el WER.

## Normalización aplicada (idéntica para la referencia y para todos los modelos)
| Aspecto | CER (documentos) | WER (audio) |
|---|---|---|
| Unicode | NFC | NFC |
| Mayúsculas | se convierten a minúsculas | se convierten a minúsculas |
| Puntuación y símbolos | se eliminan | se eliminan |
| Tildes y ñ | **se conservan** (métrica principal); como análisis de sensibilidad también se informa el CER sin tildes | se conservan |
| Saltos de línea y espacios | se unifican en un solo espacio | se unifican en un solo espacio |
| Guion + salto de línea | se unen las dos partes de la palabra | — |
| Etiquetas `[...]` | se eliminan (`[ilegible]`) | se eliminan (`[HABLANTE_k]`, `[inaudible]`, `[solapamiento]`) |
| Números | se conservan tal cual | las cifras se convierten en palabras (num2words, es) |
| Muletillas | — | se eliminan *eh, em, mmm, mm, ah* |
