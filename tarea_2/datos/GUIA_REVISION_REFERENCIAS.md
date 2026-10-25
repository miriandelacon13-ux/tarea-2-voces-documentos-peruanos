# Guía de revisión de referencias (muestra congelada)

## Origen de las referencias (declaración de transparencia)

- **10 documentos:** a pedido explícito de la autora, Claude (un LLM) hizo un **borrador de transcripción visual** a partir de la imagen original, sin copiar PaddleOCR ni Tesseract. Lo que no se distinguía con seguridad quedó como `[ilegible]`. El requisito de la tarea pide referencias **manuales**, por eso cada borrador debe **revisarse y corregirse línea por línea contra el original** antes de marcarlo como `REVISADO_HUMANAMENTE`. Este origen debe declararse en el README.
- **10 audios:** a pedido de la autora (opción B), cada uno tiene un **borrador generado por un ASR auxiliar que NO se evalúa** (wav2vec2-large-xlsr-53-spanish, Apache-2.0) con un filtro de confianza y de léxico. **No** se usó el texto de Whisper ni el de Parakeet, para no volver circular el WER. Las palabras inseguras quedaron como `[inaudible]`. El borrador debe **escucharse completo y corregirse**; su estado es `GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION` hasta que se marque `REVISADO_HUMANAMENTE`.

Las reglas de transcripción y la normalización están en `datos/GUIA_REFERENCIAS.md`.

## Cómo trabajar

1. **Documentos:** abre el original (o las tiras ampliadas de *Apoyo*) junto al TXT. Corrige toda diferencia y reemplaza cada `[ilegible]` por lo que puedas leer con seguridad.
2. **Audio:** escucha cada fragmento (carpeta *Apoyo*) y corrige la línea con la misma marca de tiempo en el TXT. Reemplaza cada `[inaudible]` por lo que oigas con seguridad.
3. Al terminar cada caso, cambia `estado` a `REVISADO_HUMANAMENTE` en `datos/reportes/control_referencias.csv`.
4. Ejecuta `python scripts/09_preparar_referencias.py`. El CER y el WER solo se calculan sobre los casos con texto **y** marcados como revisados.

Carga: 10 documentos (revisar los borradores) y 12.1 min de audio (transcribir).

### doc_005

Original:
`datos/raw/documentos/doc_005.png`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_005.png`

Referencia:
`datos/raw/referencias/documentos/doc_005.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_005.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_005`

Atención:
impreso nítido; verificar tildes y mayúsculas

---

### doc_022

Original:
`datos/raw/documentos/doc_022.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_022.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_022.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_022.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_022`

Atención:
impreso denso; nombres de particulares (archivo privado); verificar números de resolución y fechas

---

### doc_023

Original:
`datos/raw/documentos/doc_023.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_023.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_023.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_023.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_023`

Atención:
impreso denso; nombres de particulares (archivo privado); se respetó «símbolo g / anador» y «com positor» del original

---

### doc_008

Original:
`datos/raw/documentos/doc_008.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_008.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_008.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_008.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_008`

Atención:
PARCIAL: tabla con manuscrito diminuto bajo vidrio, 79 [ilegible]; completar lo que se pueda leer

---

### doc_011

Original:
`datos/raw/documentos/doc_011.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_011.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_011.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_011.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_011`

Atención:
la placa dice «1886» (verificado con ampliación), no se corrigió a 1836 por contexto; verificar

---

### doc_019

Original:
`datos/raw/documentos/doc_019.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_019.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_019.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_019.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_019`

Atención:
collage con textos cortados por los bordes; 8 [ilegible] (pie de foto y panel del fondo)

---

### doc_001

Original:
`datos/raw/documentos/doc_001.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_001.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_001.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_001.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_001`

Atención:
MUY PARCIAL (44 [ilegible]); riesgo de lectura sesgada por conocer el texto histórico del Acta: REVISIÓN PRIORITARIA

---

### doc_009

Original:
`datos/raw/documentos/doc_009.png`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_009.png`

Referencia:
`datos/raw/referencias/documentos/doc_009.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_009.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_009`

Atención:
manuscrito claro; no se transcribió la tinta traslúcida del reverso

---

### doc_015

Original:
`datos/raw/documentos/doc_015.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_015.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_015.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_015.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_015`

Atención:
topónimo de la fecha, apellido del comandante, nombre del batallón y una abreviatura quedaron [ilegible]

---

### doc_016

Original:
`datos/raw/documentos/doc_016.jpg`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\documentos\doc_016.jpg`

Referencia:
`datos/raw/referencias/documentos/doc_016.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\documentos\doc_016.txt`

Estado:
PENDIENTE_REVISION_HUMANA

Origen:
borrador LLM (Claude) pendiente de revisión humana

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\doc_016`

Atención:
inicial del destinatario [ilegible] (no se resolvió con metadatos); lápiz y sello del margen ilegibles

---

### aud_002

Original:
`datos/raw/audio/clips/aud_002.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_002.wav`

Referencia:
`datos/raw/referencias/audio/aud_002.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_002.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
71.3 s (1 min 11 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_002`

Atención:
entrevista en la calle; ritmo de habla rápido

---

### aud_006

Original:
`datos/raw/audio/clips/aud_006.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_006.wav`

Referencia:
`datos/raw/referencias/audio/aud_006.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_006.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
70.5 s (1 min 10 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_006`

Atención:
entrevista en la calle; ritmo de habla rápido

---

### aud_010

Original:
`datos/raw/audio/clips/aud_010.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_010.wav`

Referencia:
`datos/raw/referencias/audio/aud_010.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_010.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
65.5 s (1 min 5 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_010`

Atención:
entrevista en Plaza San Martín

---

### aud_012

Original:
`datos/raw/audio/clips/aud_012.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_012.wav`

Referencia:
`datos/raw/referencias/audio/aud_012.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_012.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
81.8 s (1 min 22 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_012`

Atención:
entrevista; la fuente C tiene el ritmo más rápido del corpus

---

### aud_013

Original:
`datos/raw/audio/clips/aud_013.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_013.wav`

Referencia:
`datos/raw/referencias/audio/aud_013.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_013.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
82.3 s (1 min 22 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_013`

Atención:
entrevista a excombatiente; posibles nombres de lugares y fechas

---

### aud_019

Original:
`datos/raw/audio/clips/aud_019.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_019.wav`

Referencia:
`datos/raw/referencias/audio/aud_019.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_019.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
84.5 s (1 min 25 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_019`

Atención:
ceremonia con MÚSICA de fondo y varias voces; ASR inestable; esperable [inaudible]

---

### aud_022

Original:
`datos/raw/audio/clips/aud_022.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_022.wav`

Referencia:
`datos/raw/referencias/audio/aud_022.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_022.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
67.8 s (1 min 8 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_022`

Atención:
conferencia de prensa al aire libre; ruido de público

---

### aud_023

Original:
`datos/raw/audio/clips/aud_023.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_023.wav`

Referencia:
`datos/raw/referencias/audio/aud_023.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_023.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
68.4 s (1 min 8 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_023`

Atención:
conferencia de prensa al aire libre; ruido de público

---

### aud_026

Original:
`datos/raw/audio/clips/aud_026.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_026.wav`

Referencia:
`datos/raw/referencias/audio/aud_026.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_026.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
65.2 s (1 min 5 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_026`

Atención:
conferencia de prensa al aire libre; ruido de público; posibles otras voces

---

### aud_028

Original:
`datos/raw/audio/clips/aud_028.wav`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\audio\clips\aud_028.wav`

Referencia:
`datos/raw/referencias/audio/aud_028.txt`  
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\audio\aud_028.txt`

Estado:
GENERADO_ASISTIDO_POR_ASR_PENDIENTE_REVISION

Origen:
borrador ASR auxiliar (wav2vec2, no evaluado) pendiente de revisión humana

Duración del clip:
66.2 s (1 min 6 s)

Apoyo:
`D:\Mirian\PROGRAMACION\DIPLOMADO_PYTHON1\Diplomado_Python_Mirian\Tarea2_Python\tarea_2\datos\raw\referencias\apoyo\aud_028`

Atención:
MULTIHABLANTE (entrevistador + 2 vendedoras); nombres propios de particulares

---
