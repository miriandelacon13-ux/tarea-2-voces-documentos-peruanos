"""Seudonimización reproducible de textos OCR/ASR antes de publicarlos.

Procedimiento:
1. Expresiones regulares (alta precisión, ordenadas de más a menos específica):
   - [EMAIL]      correos electrónicos;
   - [DNI]        8 dígitos precedidos de "DNI"/"D.N.I."/"documento de identidad";
   - [TELEFONO]   móviles peruanos (9 dígitos que empiezan en 9) y fijos de 7+ dígitos con prefijo;
   - [DIRECCION]  vía (Av./Jr./Calle/Pasaje/Mz.) seguida de nombre y número de casa.
   Los números de 8 dígitos sin contexto NO se reemplazan, solo se registran como candidatos.
2. NER de spaCy (es_core_news_md): entidades PER -> [NOMBRE_n].
   - Se excluyen personas públicas o históricas de PERSONAS_PUBLICAS (decisión documentada,
     PENDIENTE_REVISION_HUMANA).
   - El mismo nombre recibe el mismo marcador en todo el corpus.
3. Registro: para cada texto se guardan tipo, marcador y posición. El texto original de cada
   entidad solo se guarda en datos/raw/ (no versionado).
4. Política por época (Ley 29733 de Protección de Datos Personales protege a personas naturales
   vivas): en documentos HISTÓRICOS (anteriores a 1950) solo se aplican EMAIL/TELEFONO/DNI; no se
   reemplazan nombres ni direcciones de época. Textos contemporáneos y audios: procedimiento completo.
5. Refuerzos tras auditar fugas (el NER no detectaba todas las apariciones de un mismo nombre):
   - nombre tras tratamiento ("señorita X Y Z", "Dr. X Y"): palabras con inicial mayúscula seguidas;
   - nombres conocidos: semillas extraídas con el mismo NER de los metadatos de Commons (no versionados)
     + todos los nombres detectados en una primera pasada; se reemplazan en TODAS sus apariciones,
     sin distinguir tildes ni mayúsculas (los apellidos de 6+ letras también dentro de palabras
     mal segmentadas por el ASR, p. ej. "sa<apellido>").

La revisión final es HUMANA: el NER falla con nombres en minúscula, OCR ruidoso o nombres raros.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

PENDIENTE = "PENDIENTE_REVISION_HUMANA"

# Personas públicas/históricas cuyo nombre forma parte del valor documental o informativo.
# Se comparan sin tildes y en minúsculas; basta con que el nombre detectado contenga un apellido
# o nombre completo de la lista. Lista propuesta automáticamente -> requiere revisión humana.
PERSONAS_PUBLICAS = {
    # Figuras históricas en los documentos (según títulos/descripciones de Commons)
    "ricardo palma", "palma", "miguel grau", "grau", "arturo prat", "prat", "carmela carvajal",
    "felipe santiago salaverry", "salaverry", "agustin gamarra", "gamarra", "domingo tristan", "tristan",
    "miguel san roman", "san roman", "nicolas de pierola", "pierola", "luis antonio eguiguren", "eguiguren",
    "daniel barrera", "jose de san martin", "san martin", "simon bolivar", "bolivar",
    # Autoridades públicas mencionadas en fuentes oficiales
    "elmer schialer",
    # Figuras públicas o históricas mencionadas en las entrevistas
    "karl marx", "marx", "engels", "victor raul", "haya de la torre", "pedro castillo", "micaela bastidas",
    "antonio raimondi", "raimondi", "sanchez cerro", "tupac amaru",
}

# Falsos positivos frecuentes del NER observados en este corpus (palabras comunes y lugares).
NO_PERSONA = {"entonces", "aca", "gracias", "claro", "pucha", "queria", "sabe", "san marcos", "chives", "mache"}


def sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn").lower()


def es_persona_publica(nombre: str) -> bool:
    n = sin_tildes(nombre)
    return any(re.search(rf"\b{re.escape(p)}\b", n) for p in PERSONAS_PUBLICAS)


PATRONES = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("DNI", re.compile(r"(?i)\b(?:D\.?\s?N\.?\s?I\.?|documento\s+de\s+identidad)\s*(?:N[°ºo.]*\s*)?:?\s*\d{8}\b")),
    ("TELEFONO", re.compile(r"(?<!\d)(?:\+?51[\s-]?)?9\d{2}[\s-]?\d{3}[\s-]?\d{3}(?!\d)"
                            r"|(?<!\d)\(?0\d{1,2}\)?[\s-]?\d{3}[\s-]?\d{4}(?!\d)")),
    ("DIRECCION", re.compile(r"(?i)\b(?:Av\.|Avenida|Jr\.|Jir[oó]n|Calle|Pasaje|Psje\.|Mz\.|Manzana)\s+"
                             r"[A-ZÁÉÍÓÚÑa-záéíóúñ0-9][^\n,;]{1,40}?\s(?:N[°º]\s*)?\d{1,5}\b")),
]
CANDIDATO_DNI = re.compile(r"(?<!\d)\d{8}(?!\d)")
_MAY = "A-ZÁÉÍÓÚÑ"
_PALABRA = rf"[{_MAY}][{_MAY}a-záéíóúñü]+"
NOMBRE_TRAS_TRATAMIENTO = re.compile(
    rf"\b(?i:señoritas?|señoras?|señor(?:es)?|srta\.|sra\.|sr\.|don|doña|dr\.|dra\.|prof\."
    rf"|alcaldesa|alcalde|regidora?|autora?)"  # tratamiento sin distinguir mayúsculas ("SR.", "DON")
    rf"(?:\s+(?i:dr|dra|prof|ing|lic|sr|sra|srta)\.)?"  # título abreviado intermedio: "autor Dr. NOMBRE"
    rf"\s+({_PALABRA}(?: {_PALABRA}){{0,4}})")
TRATAMIENTOS = {"senor", "senora", "senorita", "sr", "sra", "srta", "don", "dona", "dr", "dra", "prof",
                "profesor", "profesora", "teniente", "alcalde", "regidor", "ingeniero", "licenciado"}


def _patron_flexible(nombre: str, dentro_de_palabra: bool = False) -> re.Pattern:
    """Regex que ignora tildes y mayúsculas (á≈a, ñ≈n...) para un nombre ya normalizado."""
    clases = {"a": "[aáàä]", "e": "[eéèë]", "i": "[iíìï]", "o": "[oóòö]", "u": "[uúùü]", "n": "[nñ]",
              "s": "[sz]", "z": "[sz]"}  # s/z: el ASR escribe "Vázquez" por "Vásquez"
    cuerpo = r"\s+".join("".join(clases.get(c, re.escape(c)) for c in parte) for parte in nombre.split())
    return re.compile(cuerpo if dentro_de_palabra else rf"(?<!\w){cuerpo}(?!\w)", re.IGNORECASE)


def nombres_de_metadatos(nlp, ruta_json) -> set[str]:
    """Nombres de persona (PER) en títulos y descripciones de Commons, para usarlos como semillas."""
    import json
    from html import unescape
    datos = json.loads(Path(ruta_json).read_text(encoding="utf-8"))
    textos = []
    for p in datos["query"]["pages"]:
        meta = p.get("imageinfo", [{}])[0].get("extmetadata", {})
        desc = re.sub(r"<[^>]+>", " ", unescape(str(meta.get("ImageDescription", {}).get("value", ""))))
        textos += [p["title"].removeprefix("File:").rsplit(".", 1)[0], desc]
    nombres = set()
    for doc in nlp.pipe(textos):
        nombres |= {e.text.strip() for e in doc.ents if e.label_ == "PER" and not es_persona_publica(e.text)}
        nombres |= {m.group(1) for m in NOMBRE_TRAS_TRATAMIENTO.finditer(doc.text)}
    return {n for n in nombres if len(n) >= 4}


@dataclass
class Seudonimizador:
    """Mantiene un mapa global nombre -> [NOMBRE_n] para que los marcadores sean consistentes."""
    nlp: object = None
    mapa_nombres: dict[str, str] = field(default_factory=dict)
    conocidos: dict[str, list] = field(default_factory=dict)  # nombre normalizado -> patrones

    def __post_init__(self):
        if self.nlp is None:
            import spacy
            self.nlp = spacy.load("es_core_news_md")

    def agregar_conocidos(self, nombres, semilla: bool = False) -> None:
        """Registra nombres para reemplazarlos en todas sus apariciones. Para las semillas también
        se propagan los apellidos/nombres de 6+ letras, incluso dentro de palabras mal segmentadas."""
        for nombre in nombres:
            partes = [p for p in sin_tildes(nombre).split() if p.strip(".") not in TRATAMIENTOS]
            if not partes or " ".join(partes) in NO_PERSONA or es_persona_publica(" ".join(partes)):
                continue
            clave = " ".join(partes)
            if not semilla and len(partes) < 2:
                continue  # propagar un solo token (p. ej. un topónimo mal etiquetado) causa sobre-reemplazo
            patrones = [_patron_flexible(clave)]
            if semilla:
                patrones += [_patron_flexible(p, dentro_de_palabra=True) for p in partes if len(p) >= 6]
            existentes = self.conocidos.setdefault(clave, [])
            existentes += [p for p in patrones if p.pattern not in {e.pattern for e in existentes}]

    def _marcador_nombre(self, nombre: str) -> str:
        clave = sin_tildes(re.sub(r"\s+", " ", nombre).strip())
        if clave not in self.mapa_nombres:
            self.mapa_nombres[clave] = f"[NOMBRE_{len(self.mapa_nombres) + 1}]"
        return self.mapa_nombres[clave]

    def procesar(self, texto: str, historico: bool = False) -> tuple[str, list[dict]]:
        """Devuelve (texto_seudonimizado, entidades). Cada entidad incluye el original para el
        registro privado; el registro publicable debe omitir la clave 'original'.
        historico=True: solo EMAIL/TELEFONO/DNI (sin nombres ni direcciones de época)."""
        if not isinstance(texto, str) or not texto.strip():
            return texto, []
        tramos: list[tuple[int, int, str, str, str]] = []  # inicio, fin, tipo, marcador, original

        def libre(a: int, b: int) -> bool:
            return all(b <= x or a >= y for x, y, *_ in tramos)

        for tipo, patron in PATRONES:
            if historico and tipo == "DIRECCION":
                continue
            for m in patron.finditer(texto):
                if libre(m.start(), m.end()):
                    tramos.append((m.start(), m.end(), tipo, f"[{tipo}]", m.group()))

        if not historico:
            for m in NOMBRE_TRAS_TRATAMIENTO.finditer(texto):
                nombre = m.group(1)
                if libre(m.start(1), m.end(1)) and not es_persona_publica(nombre) \
                        and sin_tildes(nombre) not in NO_PERSONA:
                    tramos.append((m.start(1), m.end(1), "NOMBRE", self._marcador_nombre(nombre), nombre))
            for clave, patrones in sorted(self.conocidos.items(), key=lambda kv: -len(kv[0])):
                for patron in patrones:
                    for m in patron.finditer(texto):
                        if libre(m.start(), m.end()):
                            tramos.append((m.start(), m.end(), "NOMBRE", self._marcador_nombre(clave), m.group()))

        for ent in ([] if historico else self.nlp(texto).ents):
            if ent.label_ != "PER" or len(ent.text.strip()) < 3 or not libre(ent.start_char, ent.end_char):
                continue
            limpio = sin_tildes(ent.text.strip(" .,;:¡!¿?"))
            if es_persona_publica(ent.text) or limpio in NO_PERSONA or (len(ent) == 1 and ent[0].is_stop):
                continue
            tramos.append((ent.start_char, ent.end_char, "NOMBRE", self._marcador_nombre(ent.text), ent.text))

        entidades = [{"tipo": t, "marcador": mk, "inicio": a, "fin": b, "original": o, "accion": "reemplazado"}
                     for a, b, t, mk, o in sorted(tramos)]
        for m in CANDIDATO_DNI.finditer(texto):
            if libre(m.start(), m.end()):
                entidades.append({"tipo": "POSIBLE_DNI", "marcador": "", "inicio": m.start(), "fin": m.end(),
                                  "original": m.group(), "accion": "no_reemplazado_revisar"})

        salida = texto
        for a, b, _, marcador, _ in sorted(tramos, reverse=True):
            salida = salida[:a] + marcador + salida[b:]
        return salida, entidades
