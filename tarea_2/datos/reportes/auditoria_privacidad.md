# Auditoría de privacidad antes de publicar el repositorio

**Fecha:** 2026-10-25.
**Alcance:** todo lo que se subiría a GitHub: los archivos versionados más los pendientes de versionar, excluidos los ignorados. También se revisó **el historial completo de git**: el contenido de cada commit, los mensajes, el autor y el committer.
**Estado:** todos los riesgos están corregidos, el historial fue reescrito y la revisión humana de privacidad está realizada (§5).

Este reporte no contiene nombres de personas protegidas: cada caso se identifica por su fuente o por su marcador.

## 1. Qué se revisó y cómo

| Revisión | Método | Resultado |
|---|---|---|
| **Nombres seudonimizados**: 82 patrones, formados por 37 nombres del mapa privado (sin contar 5 falsos positivos revisados), 7 de metadatos de Commons y 38 pares de palabras de nombres largos | Búsqueda sin distinguir mayúsculas ni tildes, con `_`/`-` entre palabras y también sobre el texto decodificado de las URL (`scripts/17_preparar_publicacion.py --verificar`) | **0** en todos los archivos publicables tras las correcciones |
| **Historial de git**: 84 versiones de archivos en los 12 commits reescritos, más sus mensajes, autor y committer | La misma búsqueda sobre cada versión de cada archivo y sobre los metadatos de cada commit | **0** nombres, **0** correos personales y **0** secretos tras la reescritura (§5). Antes, los títulos de Commons con nombres sí estaban en los commits antiguos |
| **Secretos** | Patrones de tokens (Hugging Face, OpenAI, GitHub, AWS), claves privadas, asignaciones `password=`/`token=`/`api_key=` y `Authorization: Bearer` | **0** |
| **Correos** | Expresión regular sobre archivos, historial y metadatos de commits | **0** correos personales. Solo aparecen el *noreply* de GitHub de la autora y `noreply@anthropic.com` (línea Co-Authored-By) |
| **Archivos prohibidos** | `git ls-files` por extensión y ruta | No hay audio, imágenes originales, pesos de modelos, `.env`, `secrets.toml` ni `datos/raw/`. Las únicas imágenes son las 3 capturas de `evidencias_ia/` |
| **Capturas** `evidencias_ia/01–03.jpg` | Revisión visual | Muestran el asistente y rutas locales; **sin** nombres de terceros, tokens ni claves |
| **Columnas sensibles** | Lectura de `fuentes.csv`, `documentos.csv`, `transcripciones.csv` y `reportes/*.csv` | Ver §2 |
| **Dashboard** | Columnas publicadas una por una en `app.py` y prueba con navegador | Solo texto seudonimizado; no muestra títulos ni autores |

## 2. Riesgos encontrados y correcciones

| # | Riesgo | Dónde | Gravedad | Corrección |
|---|---|---|---|---|
| 1 | El nombre de la **persona entrevistada** aparece en el título de Commons de las fuentes **A, B, C y F**, y en sus URL | `fuentes.csv`, `reportes/fuentes_audio_commons.csv`, `clips_audio.csv`, `validacion_audio_originales.csv`, `audio_adicional_seleccion.csv`; salidas del notebook 01; listas de títulos en los scripts `01` y `00b` | Alta: reidentifica a quien el texto seudonimiza | El nombre se reemplazó por `[PERSONA_ENTREVISTADA_A/B/C/F]` y las URL por `?curid=<pageid>`. Los scripts consultan Commons por *pageid* y se verificó que devuelven el mismo título y SHA-1. El notebook 01 se volvió a ejecutar y sus textos quedaron idénticos (huella SHA-256) |
| 2 | Nombre del **autor de doc_013** (carta contemporánea de 2014, seudonimizada en el texto) en el título, el autor, la descripción y la URL | `fuentes.csv`, `documentos.csv`, `reportes/fuentes_documentos_commons.csv`, `clasificacion_documentos.csv` | Alta | Se reemplazó por `[AUTOR_SEUDONIMIZADO]` y la URL por `?curid=`. Al ser **dominio público**, la licencia no exige atribución de autoría |
| 2b | El **crédito de autor de doc_022 y doc_023** (CC BY 4.0) corresponde a una persona que figura en el texto del acta de doc_022 como `[NOMBRE_11]`. Con el crédito al lado se podía reidentificar ese marcador. La búsqueda exacta no lo detectó porque el crédito usa tres de las cuatro palabras del nombre | `fuentes.csv` (`autor`), `reportes/fuentes_documentos_commons.csv` | Alta | El crédito se reemplazó por `[AUTOR_SEUDONIMIZADO_2]`; la atribución se cumple con el enlace a la página de origen (CC BY 4.0 §3(a)(2)). La verificación ahora busca también **pares de palabras** de cada nombre, y no hay más casos |
| 2c | Al completar la fuente de **doc_021** (2026-10-25), el usuario de Commons que subió `Himno_Chyo.jpg` coincide con el nombre y el correo que aparecen en la imagen, ya seudonimizados en el OCR | `reportes/fuentes_documentos_commons.csv` y `fuentes.csv` (`autor`) | Alta | El crédito se reemplazó por `[AUTOR_SEUDONIMIZADO_3]` antes de versionar. La obra es de **dominio público**, así que la licencia no exige atribución; el enlace a la página de origen se conserva |
| 3 | **Historial de git:** los commits antiguos contenían los nombres de los riesgos 1, 2 y 2b en títulos, URL y créditos, y el correo personal de la autora | Historial | Alta si se publicaba tal cual | **Historial reescrito antes del primer *push*** (decisión de la autora, opción A; ver §5). La misma redacción se aplicó a cada commit; nunca se publicó el historial antiguo |
| 4 | Entradas del mapa que son palabras comunes: "mayor", "papa" (palabra awajún), "inciso", "luz" y un error de ASR | Varios CSV y notebooks | Ninguna: falsos positivos del NER, revisados uno por uno | Se excluyen de la verificación con justificación en el código |
| 5 | Inconsistencias de seudonimización sin fuga: en aud_018 un nombre partido entre dos turnos recibió dos marcadores, y en aud_025 una palabra mal transcrita recibió un marcador | `transcripciones.csv` | Baja | Se documenta; no se modifica |
| 6 | Rutas locales absolutas (`D:\Mirian\…`) | `datos/GUIA_REVISION_REFERENCIAS.md` (60 apariciones) | Baja: solo revela la carpeta de trabajo de la autora | Se conservan: la guía es un registro del proceso de revisión |
| 7 | Revisión humana de privacidad | Columna `revision_privacidad` en `documentos.csv` y `transcripciones.csv`, y `revision` en `seudonimizacion_registro.csv` | Media | **Realizada:** la autora revisó los textos seudonimizados en las pestañas Documentos y Audios del dashboard el 2026-10-25. El valor es `REVISADO_HUMANAMENTE`, generado por el notebook 01 |
| 8 | **Riesgo residual inherente:** quien siga un enlace de atribución verá la página original de Commons, que muestra el título con el nombre | Enlaces `?curid=` | Baja | La publicación con nombre fue decisión de quien subió la obra. El proyecto no **propaga** ese dato en el dataset derivado. Se declara en el README |

## 3. Elementos que se conservan por atribución o licencia

- **Licencia y enlace de cada obra** (`fuentes.csv`: `licencia`, `licencia_url`, `fuente_url`), exigidos por CC BY, CC BY-SA y CC0 (este último, como buena práctica). En las 5 fuentes afectadas el enlace es `?curid=`: lleva a la misma página con la atribución completa, como permite CC BY-SA 4.0 §3(a)(2).
- **Crédito de autoría** (`fuentes.csv`, columna `autor`):
  - creadores o usuarios que subieron las obras CC BY y CC BY-SA, cuya mención exige la licencia;
  - instituciones;
  - autores históricos.
  - Se verificó contra el mapa privado, con nombre completo y por pares de palabras, que ninguno de los créditos que se mantienen corresponde a una persona seudonimizada. La única coincidencia (doc_022/023) se corrigió (riesgo 2b).
- **Figuras históricas y autoridades públicas** en los documentos históricos y sus descripciones: héroes y presidentes del siglo XIX, Ricardo Palma, un ministro en ejercicio en una nota oficial de prensa. Tienen valor documental y se rigen por la política por época del README.
- **Indicación de cambios y licencia de lo derivado:** el OCR, las transcripciones y las extracciones de obras CC BY-SA se comparten bajo CC BY-SA 4.0, y el README lo indica.
- **SHA-1 y SHA-256** de cada archivo fuente: permiten verificar la procedencia y no identifican a personas.

## 4. Datos de la autora

El nombre de la autora aparece en el README y en los commits, por decisión propia. Su **correo personal se reemplazó** por el correo *noreply* de GitHub en el autor y el committer de todos los commits y en `evidencias_ia/log_commits_parte1.txt`. El repositorio local también quedó configurado con ese correo para los commits futuros.

## 5. Reescritura del historial (realizada el 2026-10-25, antes del primer *push*)

- **Decisión de la autora:** opción A, reescribir el historial en lugar de publicarlo tal cual.
- **Respaldo previo:** el historial original completo se guardó en un *bundle* de git verificado, en `datos/raw/privacidad/respaldo_git/`. Esa carpeta no se versiona y contiene datos personales.
- **Procedimiento:** `git filter-branch` aplicó a cada commit la misma redacción que `scripts/17_preparar_publicacion.py` y reemplazó el correo personal por el *noreply* de GitHub.
  - Se conservaron los **12 commits**, sus mensajes, su orden, la autoría y las fechas originales de autor y de commit.
  - Las referencias y objetos del historial antiguo se eliminaron del repositorio local; solo quedan en el respaldo.
- **Hashes:** cambiaron. La tabla de correspondencia antiguo → nuevo es privada y está en el mismo respaldo. El commit de la **muestra congelada** pasó a ser `cddecce`, y se actualizaron sus referencias en el README, el notebook 02 y `evidencias_ia/log_commits_parte1.txt`.
- **Verificación posterior:** **0** nombres protegidos, **0** correos personales y **0** secretos en los archivos publicables, en las 84 versiones de archivos del historial reescrito y en los metadatos de sus 12 commits.
- **Revisión humana:** la autora dio por realizada la revisión de privacidad de los textos seudonimizados (riesgo 7).

Verificación reproducible: `python scripts/17_preparar_publicacion.py --verificar` (necesita los mapas privados de `datos/raw/privacidad/`).
