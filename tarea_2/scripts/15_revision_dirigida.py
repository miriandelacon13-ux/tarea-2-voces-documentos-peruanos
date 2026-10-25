"""Genera datos/REVISION_RAPIDA_REFERENCIAS.md: lista de verificación dirigida para que la autora revise
SOLO los fragmentos problemáticos de las 20 referencias. NO modifica ninguna referencia.

Audio (por fragmento de <= 15 s, los mismos de la plantilla de tiempos):
- texto actual de la referencia (borrador del ASR auxiliar wav2vec2) frente a faster-whisper (tiempos por
  palabra de la Parte 1) y Parakeet (tiempos por token de sherpa-onnx);
- se marca el fragmento si hay [inaudible], palabras del borrador sin respaldo en ninguno de los otros dos
  modelos, desacuerdo Whisper/Parakeet, números, posibles nombres propios o cambio de hablante
  (diarización de la Parte 1).
Documentos (por línea): [ilegible], números, fechas, nombres/tratamientos, abreviaturas y las lecturas
inciertas anotadas al transcribir. Ubicación aproximada = posición de la línea en el orden de lectura.

PRIVADO: el archivo contiene texto sin seudonimizar -> está en .gitignore y no se versiona.
Limitación: los errores que comparten los tres ASR no generan discrepancia y no aparecen aquí; se
recomienda además una escucha completa a velocidad normal.
"""
from __future__ import annotations

import json
import re

import jiwer
import pandas as pd
import soundfile as sf

import asr_alternativo
import diarizacion
from evaluacion import normalizar_wer
from utilidades import DATOS, RAW, REPORTES

SALIDA = DATOS / "REVISION_RAPIDA_REFERENCIAS.md"
PRIORIDAD_AUDIO = ["aud_019", "aud_002", "aud_028", "aud_026"]
PRIORIDAD_DOCS = ["doc_001", "doc_008", "doc_015", "doc_016", "doc_011"]
NUMEROS = re.compile(r"\d|\b(uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|"
                     r"cuarenta|cincuenta|sesenta|setenta|ochenta|noventa|cien|ciento|mil|millones?)\b", re.I)
MESES = re.compile(r"\b(enero|febrero|marzo|abril|mayo|junio|julio|agosto|setiembre|septiembre|octubre|noviembre|"
                   r"diciembre)\b", re.I)
TRATAMIENTO = re.compile(r"\b(D\.|Don|Sr\.?|Sra\.?|Señor|Señora|Señorita|Dr\.?|Prof\.|Fr\.|Gral|Exmo|Alcalde)\b")
ABREVIATURA = re.compile(r"\b\w{1,4}\.\w{1,3}\b|\b(q\.|V\.|U\.|p\.a)")
TIEMPO = re.compile(r"\[(\d\d):(\d\d\.\d)–(\d\d):(\d\d\.\d)\]")

NOTAS_DOC = {
    "doc_001": {"69": "número de folio arriba al centro",
                "General en Gefe": "lectura con posible sesgo por conocer el texto histórico: compara letra por letra",
                "Pedro de la Puente": "firma: verifica nombre", "Fr. Geronimo": "firma: verifica nombre y apellido",
                "Juan de Echevarria": "firma: verifica apellido", "Man. Cogoy": "firma grande del centro: verifica lectura"},
    "doc_008": {"1 14 1 3": "fila «Dotacion actual»: verifica cada cifra contra su columna",
                "Domingo Quiroga": "nombre en «Notas»", "Abril 30 de 1879": "fecha al pie, junto a la firma",
                "Birkenhead": "topónimo (Máquinas y Casco)", "Eslora": "cifras de «Dimensiones y calado»",
                "Huascar": "nombre del buque (manuscrito, arriba a la derecha)"},
    "doc_009": {"reputación": "¿lleva tilde en el original?", "espíritus": "¿lleva tilde en el original?",
                "U reedi-": "¿«U» o «U.»?", "49": "número de folio arriba"},
    "doc_011": {"1886": "la placa dice 1886 (verificado con ampliación): confirma; no corregir a 1836 por contexto"},
    "doc_015": {"honrades": "¿«honrades» u «honradez»?", "Abancay": "topónimo", "Urubamba": "topónimo",
                "sera permitido": "¿«será» con tilde?", "tendra": "¿«tendrá» con tilde?",
                "Exmo": "abreviatura con superíndice", "Q.S.M.B.": "fórmula de cierre abreviada"},
    "doc_016": {"Motu-": "topónimo partido «Motu-pe»", "mui": "ortografía antigua «mui»",
                "Espinoza": "apellido", "Rodriguez": "apellido (tilde no visible)"},
    "doc_019": {"ANO XI": "¿«ANO XII»? el último carácter puede estar cortado", "4832": "número del diario",
                "Wells de": "pie de foto parcialmente cortado"},
    "doc_005": {"ARAGON": "sin tilde en el original"},
    "doc_022": {"N° 061- 2015": "número de acuerdo", "N°331- 2015": "número de resolución"},
    "doc_023": {"símbolo g": "palabra partida «g / anador» como en el original", "com positor": "separación original"},
}


def segundos(m, i) -> float:
    return int(m.group(i)) * 60 + float(m.group(i + 1))


def palabras_parakeet(modelo, ruta) -> list[tuple[float, str]]:
    x, sr = sf.read(str(ruta), dtype="float32")
    s = modelo.create_stream()
    s.accept_waveform(sr, x)
    modelo.decode_stream(s)
    palabras = []
    for tok, t in zip(s.result.tokens, s.result.timestamps):
        if tok.startswith((" ", "▁")) or not palabras:
            palabras.append([t, tok.strip(" ▁")])
        else:
            palabras[-1][1] += tok
    return [(t, w) for t, w in palabras if w]


def diferencias(a: str, b: str) -> list[str]:
    if not a or not b:
        return [f"W: «{a or '∅'}» · P: «{b or '∅'}»"] if a != b else []
    o = jiwer.process_words(a, b)
    ra, rb = a.split(), b.split()
    return [f"W: «{' '.join(ra[c.ref_start_idx:c.ref_end_idx]) or '∅'}» · P: «{' '.join(rb[c.hyp_start_idx:c.hyp_end_idx]) or '∅'}»"
            for c in o.alignments[0] if c.type != "equal"]


total_b = [0]  # fragmentos de nivel B (comprobación rápida)


def revisar_audio(modelo, clips, diar) -> tuple[list[str], int]:
    lineas, total = [], 0
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    ids = [i for i in PRIORIDAD_AUDIO] + sorted(set(muestra.loc[muestra["modalidad"] == "audio", "id"]) - set(PRIORIDAD_AUDIO))
    for i in ids:
        clip = clips.loc[i]
        fuente = clip["fuente"].rsplit(".", 1)[0]
        ref = (RAW / "referencias" / "audio" / f"{i}.txt").read_text(encoding="utf-8").strip().split("\n")
        whisper = json.loads((RAW / "cache" / "asr_faster_whisper_small" / f"{i}.json").read_text(encoding="utf-8"))
        pw = [((w["inicio"] + w["fin"]) / 2, w["palabra"].strip(),
               diarizacion.hablante_de(w["inicio"] + clip["inicio_s"], w["fin"] + clip["inicio_s"], diar[fuente]["segmentos"]))
              for s in whisper["segmentos"] for w in s["palabras"]]
        pp = palabras_parakeet(modelo, RAW / "audio" / "clips" / f"{i}.wav")
        items = []
        for k, linea in enumerate(ref, 1):
            m = TIEMPO.match(linea)
            a, b = segundos(m, 1), segundos(m, 3)
            texto_ref = linea[m.end():].strip()
            ws = [w for t, w, _ in pw if a <= t < b]
            ps = [w for t, w in pp if a <= t < b]
            hablantes = list(dict.fromkeys(h for t, _, h in pw if a <= t < b and h))
            nw, np_, nr = normalizar_wer(" ".join(ws)), normalizar_wer(" ".join(ps)), normalizar_wer(texto_ref)
            sin_respaldo = [x for x in nr.split() if x not in set(nw.split()) | set(np_.split())]
            difs = diferencias(nw, np_)
            n_inaud = texto_ref.count("[inaudible]")
            # Nombres y números solo cuentan si están DENTRO de una discrepancia (no en zonas de acuerdo)
            en_disputa = " ".join(difs + sin_respaldo)
            nombres = sorted({w.strip(".,;:¿?¡!") for w in (ws[1:] + ps[1:]) if w[:1].isupper()
                              and normalizar_wer(w) and normalizar_wer(w) in en_disputa} - {"Perú", "Lima"})
            numeros = bool(NUMEROS.search(en_disputa))
            motivos, escucha = [], []
            if n_inaud:
                motivos.append(f"{n_inaud} [inaudible]"); escucha.append("reemplaza cada [inaudible] por lo que oigas (o déjalo si de verdad no se entiende)")
            if sin_respaldo:
                motivos.append(f"{len(sin_respaldo)} palabra(s) del borrador sin respaldo")
                escucha.append(f"confirma o corrige: {', '.join(dict.fromkeys(sin_respaldo))}")
            if difs:
                motivos.append(f"{len(difs)} desacuerdo(s) Whisper/Parakeet")
                escucha.append("decide qué se dice en: " + " | ".join(difs[:6]) + (" | …" if len(difs) > 6 else ""))
            if len(hablantes) > 1:
                motivos.append("cambio de hablante (" + " → ".join(hablantes) + ")")
                escucha.append("marca dónde cambia la voz (opcional [HABLANTE_k])")
            if numeros:
                motivos.append("números"); escucha.append("verifica cifras/fechas dichas")
            if nombres:
                motivos.append("posibles nombres"); escucha.append(f"verifica nombres: {', '.join(nombres[:6])}")
            if not motivos:
                continue
            nivel_a = (n_inaud > 0 or len(difs) >= 2 or len(hablantes) > 1 or len(sin_respaldo) >= 3
                       or numeros or bool(nombres))
            puntaje = 3 * n_inaud + len(sin_respaldo) + len(difs) + 2 * (len(hablantes) > 1)
            items.append((nivel_a, puntaje, k, m.group(0), texto_ref, " ".join(ws), " ".join(ps), motivos, escucha,
                          sin_respaldo, difs))
        a_items = [x for x in items if x[0]]
        b_items = [x for x in items if not x[0]]
        total += len(a_items)
        total_b[0] += len(b_items)
        lineas += [f"### {i} · fuente {fuente[-1]} · {clip['duracion_real_s']:.1f} s · nivel A: {len(a_items)} · "
                   f"nivel B: {len(b_items)} · sin discrepancias: {len(ref) - len(items)} (de {len(ref)} fragmentos)", ""]
        for _, puntaje, k, marca, r, w, p, motivos, escucha, _, _ in a_items:
            lineas += [f"- [ ] **A · {marca}** · `apoyo/{i}/fragmento_{k:02d}.wav` · prioridad {puntaje} · {'; '.join(motivos)}",
                       f"  - Referencia actual: `{r}`", f"  - Whisper: `{w or '∅'}`", f"  - Parakeet: `{p or '∅'}`",
                       f"  - Escucha y verifica: {'; '.join(escucha)}", ""]
        if b_items:
            lineas += ["  Comprobación rápida (nivel B: escucha y confirma solo estas palabras):", ""]
            for _, _, k, marca, _, _, _, _, _, sin_resp, difs in b_items:
                lineas.append(f"- [ ] **B · {marca}** · `fragmento_{k:02d}.wav` · "
                              + "; ".join([f"borrador «{x}» sin respaldo" for x in sin_resp] + difs))
            lineas.append("")
    return lineas, total


def revisar_documentos(clasif) -> tuple[list[str], int]:
    lineas, total = [], 0
    muestra = pd.read_csv(DATOS / "muestra_evaluacion.csv")
    ids = PRIORIDAD_DOCS + sorted(set(muestra.loc[muestra["modalidad"] == "documento", "id"]) - set(PRIORIDAD_DOCS))
    for i in ids:
        texto = (RAW / "referencias" / "documentos" / f"{i}.txt").read_text(encoding="utf-8").strip().split("\n")
        n_tiras = len(list((RAW / "referencias" / "apoyo" / i).glob("tira_*.jpg")))
        notas = NOTAS_DOC.get(i, {})
        items = []
        for k, linea in enumerate(texto, 1):
            motivos = []
            if "[ilegible]" in linea:
                motivos.append(f"{linea.count('[ilegible]')} [ilegible]: intenta leerlo en la tira ampliada")
            if re.search(r"\d", linea):
                motivos.append("números: verifica cada cifra")
            if MESES.search(linea) and clasif[i] != "impreso":
                motivos.append("fecha: verifica día, mes y año")
            for clave, nota in notas.items():
                if clave in linea:
                    motivos.append(nota)
            if clasif[i] == "manuscrito" and i == "doc_001" and not motivos:
                motivos.append("lectura incierta (manuscrito colonial): compara palabra por palabra")
            if motivos:
                frac = (k - 0.5) / len(texto)
                tira = min(n_tiras, int(frac * n_tiras) + 1)
                items.append((k, frac, tira, linea, motivos))
        # Agrupar líneas consecutivas que solo contienen [ilegible] (p. ej., listas de nombres en una tabla)
        agrupados = []
        for it in items:
            solo_ilegible = re.fullmatch(r"(D\. )?\[ilegible\]", it[3].strip()) is not None
            if solo_ilegible and agrupados and agrupados[-1][5] and agrupados[-1][0][-1] == it[0] - 1:
                agrupados[-1][0].append(it[0])
            else:
                agrupados.append(([it[0]], it[1], it[2], it[3], it[4], solo_ilegible))
        items = [(ks, frac, tira, linea if len(ks) == 1 else f"{len(ks)} líneas seguidas con solo [ilegible]",
                  motivos if len(ks) == 1 else [f"{len(ks)} entradas [ilegible] (nombres o cifras de una lista): "
                                                "lee las que puedas en la tira ampliada"])
                 for ks, frac, tira, linea, motivos, _ in agrupados]
        total += len(items)
        orden = " (orden de lectura por secciones: la posición es aproximada)" if i in ("doc_008", "doc_019") else ""
        lineas += [f"### {i} · {clasif[i]} · {len(items)} de {len(texto)} líneas a verificar{orden}", ""]
        for ks, frac, tira, linea, motivos in items:
            rango = f"Línea {ks[0]}" if len(ks) == 1 else f"Líneas {ks[0]}–{ks[-1]}"
            lineas += [f"- [ ] **{rango}** (≈ {100 * frac:.0f} % desde arriba · `apoyo/{i}/tira_{tira:02d}.jpg`): `{linea}`",
                       f"  - Verifica: {'; '.join(dict.fromkeys(motivos))}", ""]
    return lineas, total


def main() -> None:
    clips = pd.read_csv(REPORTES / "clips_audio.csv").set_index("id")
    clasif = pd.read_csv(REPORTES / "clasificacion_documentos.csv").set_index("id")["tipo"]
    diar = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in (RAW / "cache" / "diarizacion").glob("audio_*.json")}
    modelo, _ = asr_alternativo.cargar_modelo()
    audio, n_audio = revisar_audio(modelo, clips, diar)
    docs, n_docs = revisar_documentos(clasif)
    cab = [
        "# Revisión rápida de referencias (PRIVADO: contiene texto sin seudonimizar; no se versiona)", "",
        f"**Fragmentos a comprobar:** {n_audio} de audio de nivel A (escuchar con atención) + {total_b[0]} de nivel B "
        f"(confirmar 1–2 palabras) y {n_docs} líneas de documentos. "
        f"**Prioridad:** {', '.join(PRIORIDAD_AUDIO)} (audio) y {', '.join(PRIORIDAD_DOCS)} (documentos).", "",
        "## Cómo usar esta lista", "",
        "1. **Audio:** reproduce el fragmento indicado (`datos/raw/referencias/apoyo/<id>/fragmento_XX.wav`) y corrige "
        "**solo esa línea** en `datos/raw/referencias/audio/<id>.txt`, sin borrar la marca `[mm:ss–mm:ss]`. "
        "Las alternativas de Whisper y Parakeet son **pistas para saber qué escuchar**, no respuestas: escribe lo que "
        "realmente oigas.",
        "2. **Documentos:** abre la tira indicada (`datos/raw/referencias/apoyo/<id>/tira_XX.jpg`) o el original y "
        "corrige la línea en `datos/raw/referencias/documentos/<id>.txt`.",
        "3. Marca `[x]` en cada ítem revisado (opcional; esta lista no se usa para calcular nada).",
        "4. Al terminar cada caso, escribe en `datos/reportes/control_referencias.csv`, columna `estado`:",
        "   - `REVISADO_CON_CAMBIOS` si corregiste algo;",
        "   - `REVISADO_SIN_CAMBIOS` si lo revisaste y estaba bien.",
        "5. Ejecuta `.venv\\Scripts\\python scripts\\09_preparar_referencias.py`: compara cada archivo con su borrador y "
        "marca INCONSISTENTE si el estado no coincide con lo que realmente cambió.", "",
        "> **Limitación:** si los tres ASR se equivocan igual, no hay discrepancia y ese error no aparece en la lista. "
        "Se recomienda además escuchar cada clip completo una vez a velocidad normal (≈ 12 min en total).", "",
        "## Audio", ""]
    SALIDA.write_text("\n".join(cab + audio + ["## Documentos", ""] + docs), encoding="utf-8")
    print(f"Escrito {SALIDA} · audio: {n_audio} fragmentos · documentos: {n_docs} líneas")


if __name__ == "__main__":
    main()
