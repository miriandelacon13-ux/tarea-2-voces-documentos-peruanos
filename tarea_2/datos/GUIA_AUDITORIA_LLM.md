# Guía de auditoría humana de la extracción LLM (20 casos)

**Qué se evalúa:** si la extracción es **fiel al texto fuente que recibió el LLM** (OCR/ASR seudonimizado), no si el OCR/ASR era correcto.

**Marca SI** cuando se cumplen todas estas condiciones:
- `tema` y `resumen` describen lo que realmente dice el texto, sin agregar hechos;
- `emisor`, `fecha` y `monto` son correctos, o `null` cuando el texto no los contiene;
- las `citas_clave` aparecen en el texto, salvo diferencias mínimas de puntuación;
- `numero_hablantes` coincide con las etiquetas `[HABLANTE_k]` del texto, o es `null` si no hay etiquetas.

**Marca NO** si algún campo está inventado o es claramente incorrecto, aunque el resto esté bien. Si es parcial, pon NO y explica en la observación.

**Cómo responder:** completa `datos/respuestas_auditoria_llm.txt`, una línea por caso:
`doc_003: SI` o `aud_017: NO | la cita 2 no está en el texto`.

Las alertas automáticas son pistas, **no decisiones**: un caso con alertas puede ser SI y uno sin alertas puede ser NO.

---

### doc_003 · documento (manuscrito) · 113 caracteres de texto fuente

**Texto fuente (inicio):** ral & South American Telegraph Co. RECIBO. Para, parklite Ofevele 1915 487/45 Ralabras, Tasa, Empleado, le Fechal

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "recibo",
 "resumen": "Recibo emitido por Ral & South American Telegraph Co.",
 "emisor": "Ral & South American Telegraph Co.",
 "fecha": "1915",
 "monto": "487/45"
}
```

**Alertas automáticas:** verifica que el monto sea realmente una cantidad de dinero del documento

**Tu decisión:** `doc_003: SI` o `doc_003: NO | observación`

---

### doc_007 · documento (impreso) · 2329 caracteres de texto fuente

**Texto fuente (inicio):** EI DERNYLUSTRADO SEMANARIO ILUSTRADO PARA LAS FAMILIAS – Editores Propietarios, PETER BACIGALUPI & Co. AÑO I.} {NUM. 3. LIMA, SABADO ₂8 DE MAYO DE 1887. PRECIOS. Nuestro tercer graba- do es una bellísima fan- Número suelto.... 0 10 cts. tasía destinada à servir Entregado á domi- de carátula á una pieza cilio, al més...... 0 40 » de música para piano, Al semestre......... 2 00 cuya impresión se halla Al año..…… . 3 50…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "documentos ilustrados",
 "resumen": "El documento presenta información sobre grabados y precios de un periódico ilustrado.",
 "emisor": null,
 "fecha": "MAYO, 28 DE 1887",
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_007: SI` o `doc_007: NO | observación`

---

### doc_008 · documento (foto) · 1276 caracteres de texto fuente

**Texto fuente (inicio):** Nenitai Iluascare Armada del Pera. 手手手手手手手 ESTADO GENERAL En que, se encuentra en el mes de la fecha. Oficiales de guerra. Guardias Marinas. Municiones y artificios. Trasporte. Oficiales mayores y maquinistas. Armamento. Doames te tpulyd fseathe Nanar Ae de Egth af Pasageros Oeiles pectheank d Medcina Tropa seginde god Jetes Total Andenede y Grater Rapiter fhe de de lun 1 Dapraltates de prbia Gasicisa Clises Chr, sut…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "estado general",
 "resumen": "El documento describe el estado general de diferentes elementos militares y de transporte.",
 "emisor": "Imp, del Es ado-Lima",
 "fecha": "n/a",
 "monto": null
}
```

**Alertas automáticas:** «fecha» = «n/a» indica ausencia como texto: debería ser null; OCR de baja confianza (0.72, foto): riesgo de que tema/resumen se basen en texto erróneo

**Tu decisión:** `doc_008: SI` o `doc_008: NO | observación`

---

### doc_012 · documento (foto) · 1228 caracteres de texto fuente

**Texto fuente (inicio):** MONITORHUASCAR. PISAGUA, JUNIO 2 DE 1879. SEÑORA CARMELA CARVAJAL DE PRAT DIGNISIMA SEÑORA: "UN SAGRADO DEBER ME AUTORIZA A DIRIGIRME A UD. Y SIENTO PROFUNDAMENTE QUE ESTA CARTA,POR LAS LUCHAS QUE VA A REMEMORAR,CONTRIBUYA A AUMENTAR EL DOLOR QUE HOY JUSTAMENTE DEBE DOMINARLA. EN EL COMBATE NAVAL DEL 21 PROXIMO PASADO QUE TUVO LUGAR EN LAS AGUAS DE IQUI- QUE, ENTRE LAS NAVES PERUANAS Y CHILENAS, SU DIGNO Y VA- LEROSO…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "condolencia y entrega de prendas",
 "resumen": "El emisor condena la muerte de su esposa y le entrega prendas que pertenecían a ella.",
 "emisor": "MIGUELGRAU",
 "fecha": "PISAGUA, JUNIO 2 DE 1879",
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_012: SI` o `doc_012: NO | observación`

---

### doc_013 · documento (manuscrito) · 1104 caracteres de texto fuente

**Texto fuente (inicio):** 25De0ciabiadal2014 [NOMBRE_1]. nunash ashijuk yu papa jujuma agajan auatajama antakta payasma fuyash aa tsaskugtusta avaz atsamai [NOMBRE_2] yatsujun sega Rasai nouiambratinia taa aa ni tajamaimina embratiniah tata nuas dakaai dos mina promocion 1:corta ina. [NOMBRE_3] [NOMBRE_4] jujui y:cajetilla cigarra 3 ano nuavonak inapkeaktatjai yna tabmu 2:botella zxxx. pá [NOMBRE_5] yetsug 1 par zapatilla. [NOMBRE_6] nui [NOM…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "promocion",
 "resumen": "Promoción de productos y servicios",
 "emisor": null,
 "fecha": "25De0ciabiadal2014",
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_013: SI` o `doc_013: NO | observación`

---

### doc_015 · documento (manuscrito) · 405 caracteres de texto fuente

**Texto fuente (inicio):** Suniti 12 me Agosk vu1840 Mi reppetabe hal yPadrino. la diventiria a. he lontraido en mi confi. nacion de tbaneay, me he Lituado in este ba, me sena pernitid Eajar, a bubambay No me canvare in zecomemdan a to, In honrsades ul comandante tiabima-Aste Jege eh katallon lmeo- t basin al, enta indicacion, ceo eumplin con lo pusticin, Sesea a t. may buena Labnd in decidids aligads e inbariable dexvidon Ge1.0

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "diventiria a. he lontraido",
 "resumen": "El emisor ha estado en su país y ahora se retira del bando.",
 "emisor": null,
 "fecha": "Suniti 12 me Agosk vu1840",
 "monto": null
}
```

**Alertas automáticas:** OCR de baja confianza (0.77, manuscrito): riesgo de que tema/resumen se basen en texto erróneo

**Tu decisión:** `doc_015: SI` o `doc_015: NO | observación`

---

### doc_016 · documento (manuscrito) · 335 caracteres de texto fuente

**Texto fuente (inicio):** $30 Sr I.n. Rodignuer R. Lamtayeque Moi querids Ir Frefecto: El Ir Pedro Adolfo Espinoza, despes de conversar conmigo, regresa a Mbotu. pe lugar de su pesidencia para ocuarse de us a suntos particubares. Recomiéndolo mui especialmente a su dietinguida considevacion i a la de sus auto- ridades subaltermas. Aictuosamente singe lierola

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "recomendación de funcionario",
 "resumen": "El documento recomienda a un funcionario para un cargo",
 "emisor": null,
 "fecha": null,
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_016: SI` o `doc_016: NO | observación`

---

### doc_017 · documento (manuscrito) · 543 caracteres de texto fuente

**Texto fuente (inicio):** Agradenco muy sineeromenls ming, mio Untomin Eginiguren al infimits gut, rnmanth b and pooitle, Gavo- roxia con in oprcita slite aest Merafhores, 2hode Oetibre de/912. Tarjeta dirigida a Luis Antonio Eguiguren por Don Ricardo Palma: "Agradezco muy sinceramente la fina atención de mi joven amigo Luis Antonio Eguiguren al obsequiarme dos folleti tos cuya lectura haré próximamente, y le estimaré infinito que, cuando sea…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "financiamiento y atención",
 "resumen": "El emisor agradece la atención de su amigo y le pide que visite a su amigo enfermo",
 "emisor": "Ricardo Palma",
 "fecha": "24 de Octubre de 1912",
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_017: SI` o `doc_017: NO | observación`

---

### doc_019 · documento (foto) · 775 caracteres de texto fuente

**Texto fuente (inicio):** Mocolo de Arbitr os en Wáshington. América, pa tación 0 PERÚ Ministerio de Relaciones Exteriores Momen proce serár del Pe ejempla. LA dera que ahora abre sus pliegues amparándose en la cindad de Tarata estta el instante en que las señoras Wells de Alvares ntregaron al Presidente de la M CRONICA OFICINAS Y TALLERES: PANDO Nám 758-TELEFONO Núm. 2106-APARTADO Nm 1087 DIARIO ILUSTRADO POLIT ICO-INDEPENDIENTE E INF ORMATI…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "documentos de pago",
 "resumen": "El documento habla sobre el pago de un módulo de arbitraje en Washington y la reincorporación de la provincia de Tarata al Perú.",
 "emisor": null,
 "fecha": "2 SETIEMBRE 1925",
 "monto": null
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `doc_019: SI` o `doc_019: NO | observación`

---

### doc_025 · documento (impreso) · 11468 caracteres de texto fuente

**Texto fuente (inicio):** 80 78 81 79 77 76 83 82 75 74 73 84 72 71 70 S.R NUE VoldanSietebocas OSA Cabode SLorenzo Dueved Montecristi PORTOVIE.JO Ambato I.s E L.Yand Cuiyacus Balxan X PicoLlanganate Curarai GRANADA Salto de Capati Rio Apaporis Jipijapa 乐 Mocha L. Bombonaza VinceSie Cotimes Rio Putuma Aguar Chimbonazo Rio RIOBAMBA I. Salango L.Chiripunos Napo R Mazanhas Rio Yapurá Babahoyo Guaranda ptaSalango ie PieoAltar Canelos e SnPedro I.…

**Campos extraídos:**

```json
{
 "modalidad": "documento",
 "tema": "documentos",
 "resumen": "información sobre documentos",
 "emisor": null,
 "fecha": null,
 "monto": null
}
```

**Alertas automáticas:** el texto fuente se truncó a 8000 caracteres para el LLM

**Tu decisión:** `doc_025: SI` o `doc_025: NO | observación`

---

### aud_001 · audio (audio) · 1042 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] Bueno, así aquí nos encontramos en una calle, por favor, ¿me podría decir su nombre? [HABLANTE_2] [NOMBRE_20]. [HABLANTE_1] Ok, muchas gracias [NOMBRE_20]. Quedé a preguntarle para usted, ¿qué es el Perú? El Perú es una idea, ¿ya? Primero es una idea, ¿y qué embarca esta idea, qué coge, ¿no? La idea de un Estado, ¿ya? Entonces, el Perú es una nación que se dice que tiene cierto sistema. Mucho dice que ti…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "Perú",
 "resumen": "La entrevista discute sobre el concepto de Perú y su identidad.",
 "citas_clave": [
  "[NOMBRE_20].",
  "El Perú es una nación que se dice que tiene cierto sistema. Mucho dice que tiene sistema capitalista, sistema mixto. Mucho dice que vimos en un sistema democrático.",
  "El Perú le está conformado por individuos, que venimos ser los ciudadanos."
 ],
 "numero_hablantes": 3
}
```

**Alertas automáticas:** numero_hablantes no coincide con las etiquetas: LLM=3 vs etiquetas=2

**Tu decisión:** `aud_001: SI` o `aud_001: NO | observación`

---

### aud_002 · audio (audio) · 892 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_2] lo hermoso y deleitable, [HABLANTE_1] y como seguiría esta palabra, a ver, no se me vea la cabeza, pero el Perú tiene, bueno, hablando de ciudad, tiene a las personas que buscan de una otra manera el trabajo, los perros somos trabajadores, eso es algo también, que a nivel personal y de una óptica sociológica, podemos decir de que se caracteriza por eso, es muy, podría poner un énfasis en eso, y algo de l…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "perú, trabajo, perros, comunismo, socialismo",
 "resumen": "El hablante explica aspectos positivos y negativos de la sociedad peruana, destacando la resistencia a ideas como el comunismo.",
 "citas_clave": [
  "[HABLANTE_1] los perros somos trabajadores",
  "[HABLANTE_1] hay un condicionamiento que inhibe ese proceso a llegar esa idea utópica",
  "[HABLANTE_1] también algún aspecto negativo que le pueda resaltar de Perú, bueno en el tema de la sociedad vendría a ser la delincuencia"
 ],
 "numero_hablantes": 2
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_002: SI` o `aud_002: NO | observación`

---

### aud_004 · audio (audio) · 1376 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] Pero vaya a preguntar a lugares como Vía Salvador, Vía María, [HABLANTE_2] la gente les conoce. ¿Quién sabe quién [HABLANTE_1] es [NOMBRE_21] y la Policía? No, ni siquiera saben cuál es la cultura chavín, de quién nos formó, no conocen los grandes arqueólogos, no conocen la historia de Perú, los grandes políticos, quiénes fueron los que lucharon para la libertad, como uno de los grandes partidos, que es …

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "cultura y sociedad peruana",
 "resumen": "La entrevista discute la falta de conocimiento sobre la cultura y la historia de Perú, incluyendo la sociedad andina y la participación de mujeres en el voto.",
 "citas_clave": [
  "[NOMBRE_21] y la Policía? No, ni siquiera saben cuál es la cultura chavín, de quién nos formó, no conocen los grandes arqueólogos, no conocen la historia de Perú, los grandes políticos, quiénes fueron los que lucharon para la libertad, como uno de los grandes partidos, que es el APRA, a través de uno de los grandes líderes, Víctor Raúl.",
  "Antes, las mujeres no votaban. Entonces, ¿cuándo diría que no había autofonio? Es más, el punto es que antes no solo había gramachismo, sino que también había lo que se conoce como una sociedad, el tema andino, y es más, se desconocía.",
  "Si no fuera por uno de los diputados, por así decirlo, que también pertenecía al gobierno de [NOMBRE_22], no se hubiera conocido que hubiera sociedad ahí."
 ],
 "numero_hablantes": 2
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_004: SI` o `aud_004: NO | observación`

---

### aud_006 · audio (audio) · 1223 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] pero que lean de todo, [HABLANTE_?] que [HABLANTE_1] lean economía, que lean biología, zoología, filosofía... No, [HABLANTE_?] porque [HABLANTE_1] la filosofía abarca muchos temas, ética, epismetología, lógica, metafísica, que estudien ciencia, que estudien historia, que estudien los distintos sin fin número de conocimiento, ¿por qué? Es simple, porque cuando tú, acabamos un punto ya, tú te solo te enfoc…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "formación empresarial y ética ambiental",
 "resumen": "El hablante 1 enfatiza la importancia de la formación en diversos campos para una buena formación empresarial, mientras que el hablante 2 menciona la ética empresarial y su relación con la filosofía y la ecología.",
 "citas_clave": [
  "[HABLANTE_1] No, la filosofía abarca muchos temas, ética, epistemología, lógica, metafísica, que estudien ciencia, que estudien historia, que estudien los distintos sin fin número de conocimiento, ¿por qué? Es simple, porque cuando tú, acabamos un punto ya, tú te solo te enfocas en, por ejemplo, finanzas.",
  "[HABLANTE_2] tú eres una empresa de un minera, y si tú no tienes una ética para ti, te debe importar poco, poder contaminar los ríos, en la sierra. En el medio ambiente, la ecología.",
  "[HABLANTE_1] Entonces, pero cuando hay una ética, que esa ética te la aporta la filosofía, a través de un entendimiento moral, tú puedes no solo ser un buen empresario, pero con ética y moral, teniendo una noción de lo que es la ecología."
 ],
 "numero_hablantes": 3
}
```

**Alertas automáticas:** citas literales: 2/3 literales (alguna puede estar parafraseada o inventada)

**Tu decisión:** `aud_006: SI` o `aud_006: NO | observación`

---

### aud_014 · audio (audio) · 1210 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] y me dice si hoy día cuántos asaltos ha visto usted ninguno y no se acuerda se acuerda entonces estamos contrarrestando como contra este estamos yendo en contra de la realidad lo que los medios de presa hacen vender un producto un producto que a la larga les hace daño a la gente bien tensionada si el cobi no ha matado de del virus y no lo ha matado porque la gente se ha asustado se aterrao pero a su vez …

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "crisis sanitaria y corrupción",
 "resumen": "El hablante discute sobre la crisis sanitaria y la corrupción en Perú",
 "citas_clave": [
  "no se acuerda se acuerda entonces estamos contrarrestando como contra este estamos yendo en contra de la realidad",
  "el cobi no ha matado de del virus y no lo ha matado porque la gente se ha asustado se aterrao",
  "el sé corrupto de arriba hasta abajo es algo normal debemos erradicarlo"
 ],
 "numero_hablantes": 1
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_014: SI` o `aud_014: NO | observación`

---

### aud_017 · audio (audio) · 1179 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] Buenos días, su nombre. ¿Qué es [HABLANTE_?] el [HABLANTE_1] mundo entero? [HABLANTE_2] La [HABLANTE_1] pregunta es, ¿qué significado tiene para usted la música? ¿Qué significado tiene para usted la música y esta celebración? [HABLANTE_3] Ah, [HABLANTE_1] es [HABLANTE_3] un baile costumbrista de este pueblo de Chives. El revista de Pohambá, el Partamento del Centro y Poblado de Chives. Este baile es un c…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "música y tradiciones",
 "resumen": "La entrevista discute la música y las tradiciones musicales de un pueblo peruano.",
 "citas_clave": [
  "[HABLANTE_1] ¿Qué es el mundo entero?",
  "[HABLANTE_3] El revista de Pohambá, el Partamento del Centro y Poblado de Chives.",
  "[HABLANTE_3] ¿Cuál es el nombre, por favor?"
 ],
 "numero_hablantes": 4
}
```

**Alertas automáticas:** numero_hablantes no coincide con las etiquetas: LLM=4 vs etiquetas=3

**Tu decisión:** `aud_017: SI` o `aud_017: NO | observación`

---

### aud_021 · audio (audio) · 999 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] ¿Qué esperamos? Bien, [HABLANTE_2] estamos en Plata San Martín. Antes que nada, ¿me podría decir su nombre, por favor? [HABLANTE_1] Mi nombre es la señora [NOMBRE_33]. Vengo desde el departamento de Apurima en Marcha en solidarizarnos con nuestro gobierno y pedimos que cierren el Congreso contra esos congresistas que no trabajan para su pueblo. Queremos que se retiren ya del Congreso y queremos que deje …

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "patria y gobierno",
 "resumen": "La entrevistada expresa su descontento con el Congreso y pide que se retiren los congresistas no productivos.",
 "citas_clave": [
  "[HABLANTE_1] estamos en Plata San Martín.",
  "[HABLANTE_1] nuestro Perú no debe ser así. Estropeado, pisado por gente que no sirven a su pueblo.",
  "[HABLANTE_1] El Perú es una patria grande donde todos los peruanos acá somos parte de eso y nuestro Perú no debe ser así."
 ],
 "numero_hablantes": 2
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_021: SI` o `aud_021: NO | observación`

---

### aud_025 · audio (audio) · 720 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] [NOMBRE_42] nuestros derechos fundamentalmente y principalmente de nosotras, las mujeres para ellos se han unido desde la derecha a patria, a patria acá y su puesta izquierda que sorprendentemente se autodenominan provincianas. Ambos han inflado sus baterías para intentar destruir el ministerio de la mujer y poblaciones vulnerables y una entidad producto de lucha de todas las mujeres peruanas desde la re…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "derechos de las mujeres",
 "resumen": "El hablante critica a sectores políticos por amenazar el ministerio de la mujer y la igualdad de género.",
 "citas_clave": [
  "[NOMBRE_42] nuestros derechos fundamentalmente y principalmente de nosotras, las mujeres para ellos se han unido desde la derecha a patria, a patria acá y su puesta izquierda que sorprendentemente se autodenominan provincianas.",
  "ambos han inflado sus baterías para intentar destruir el ministerio de la mujer y poblaciones vulnerables y una entidad producto de lucha de todas las mujeres peruanas desde la región apurima",
  "buscan desconocer el rol fundamentalmente de la mujer en la sociedad y en anda de todas las normatibilidades como la ley 30 36 ley para erradicar sancionar la violencia contra las mujeres y los integrantes del grupo familiar ley 28 98 de igualdad"
 ],
 "numero_hablantes": 1
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_025: SI` o `aud_025: NO | observación`

---

### aud_026 · audio (audio) · 757 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] de oportunidades entre mujeres y hombres, principalmente la violan, la normatibilidad internacional, que nos protege como la convención internacional para prevenir y sancionar y erradicar la violencia contra las mujeres, especialmente el convenio de [NOMBRE_35]. En tal sentido, las mujeres peruanas, principalmente las apurimeñas, nada nos han regalado, todo lo hemos conquistado con lucha sacrificio, nos …

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "violencia contra mujeres",
 "resumen": "Se habla sobre la violencia hacia mujeres y la necesidad de protegerlas con convenios internacionales.",
 "citas_clave": [
  "[NOMBRE_35]",
  "las mujeres peruanas, principalmente las apurimeñas, nada nos han regalado, todo lo hemos conquistado con lucha sacrificio",
  "nos dejamos pasar esta frente"
 ],
 "numero_hablantes": 1
}
```

**Alertas automáticas:** sin alertas automáticas (igual verifica tema y resumen)

**Tu decisión:** `aud_026: SI` o `aud_026: NO | observación`

---

### aud_027 · audio (audio) · 959 caracteres de texto fuente

**Texto fuente (inicio):** [HABLANTE_1] para construir una patria de igualdad en libertad. Somos peruanos y nos regresaremos al mundo de la caver, cavernícola, de tanto extrañan estos herederos del coloniaje. Impulsaremos y recolostaremos la firma de todas las mujeres peruanas para defender nuestros hijos. ¡Viva el Ministerio de la Mujer! ¡Viva la población de es vulnerables! Muchísimas gracias. [HABLANTE_4] Gracias, señora [NOMBRE_36], que su…

**Campos extraídos:**

```json
{
 "modalidad": "audio",
 "tema": "patria de igualdad",
 "resumen": "El hablante 1 habla sobre la necesidad de construir una patria de igualdad y libertad, mientras que el hablante 4 agradece a la hablante 36.",
 "citas_clave": [
  "[HABLANTE_1] para construir una patria de igualdad en libertad.",
  "[HABLANTE_1] somos peruanos y nos regresaremos al mundo de la caver, cavernícola, de tanto extrañan estos herederos del coloniaje.",
  "[HABLANTE_1] nosotros somos, aperturamos la nuestra lucha en favor de ustedes, porque ustedes son nuestros hijos, yo tengo hijos y quiero que mis hijos algún día velen por esta hermosa patria que tanto amamos y es una patria grande, lleno de millonario, lleno de oro, de riqueza, adelante jóvenes la lucha"
 ],
 "numero_hablantes": 3
}
```

**Alertas automáticas:** citas literales: 2/3 literales (alguna puede estar parafraseada o inventada); numero_hablantes no coincide con las etiquetas: LLM=3 vs etiquetas=2

**Tu decisión:** `aud_027: SI` o `aud_027: NO | observación`

---
