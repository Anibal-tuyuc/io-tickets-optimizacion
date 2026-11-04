# Guion del video explicativo

**Duración objetivo:** 13–14 minutos (límite 15)
**Formato:** cámara + captura de pantalla, alternando
**Requisito del enunciado:** el estudiante debe aparecer en cámara explicando la lógica del modelo y ejecutar en vivo las tres pruebas

---

## Preparación previa (10 minutos antes de grabar)

**Checklist técnico**

- [ ] `docker compose up` funcionando, o backend y frontend en desarrollo
- [ ] Navegador en `http://localhost:8080` (o `5173`), ventana maximizada a 1920×1080
- [ ] Zoom del navegador al 110 % para que el texto se lea en el video
- [ ] Pestaña *Calidad de datos* abierta en segundo plano (la vas a necesitar en el minuto 2)
- [ ] `POST /demo/reset` ejecutado, o botón **Reiniciar demo** pulsado
- [ ] Cerrar notificaciones, Slack, correo
- [ ] Micrófono probado: 30 segundos de prueba y escuchar
- [ ] Guion impreso o en segunda pantalla (no en la pantalla que grabas)

**Errores que arruinan una grabación**

1. Empezar sin reiniciar la demo → las cifras no coinciden con el guion
2. Grabar la pantalla del portátil con reflejos
3. Hablar mirando la pantalla y no a la cámara en las explicaciones conceptuales
4. Que el video pase de 15 minutos (penaliza)
5. Enlaces privados o rotos (anula la calificación de funcionalidad)

---

## Estructura y minutaje

| Bloque | Minutos | Contenido |
| :--- | :--- | :--- |
| 1. Presentación y problema | 0:00 – 1:30 | Quién soy, qué problema resuelve la herramienta |
| 2. Análisis de datos | 1:30 – 3:30 | Las 12 hojas, las 24 incidencias, los tres hallazgos |
| 3. Modelo matemático | 3:30 – 6:00 | Carga ponderada, función objetivo, restricciones, las 3 correcciones |
| 4. **Prueba 1** | 6:00 – 8:30 | Desbalance y colisiones → optimización |
| 5. **Prueba 2** | 8:30 – 10:15 | Vacaciones del Gestor 1 |
| 6. **Prueba 3** | 10:15 – 12:00 | Cambio a contratación externa |
| 7. Cierre y uso de IA | 12:00 – 13:30 | Resultados, limitaciones, bitácora de IA |

---

# BLOQUE 1 — Presentación y problema (0:00 – 1:30)

**[CÁMARA, plano medio]**

> Buenos días. Soy Aníbal Tuyuc, y este es mi proyecto final de Investigación de Operaciones.
>
> El Departamento de Docencia recibe solicitudes de capacitación por un HelpDesk. Cada solicitud llega como un ticket, y la Mesa de Entrada lo asigna a uno de los cinco gestores académicos por turno rotativo: al gestor uno, al dos, al tres, y así.
>
> Ese procedimiento tiene un supuesto escondido: que todos los tickets son iguales. Y no lo son.

**[PANTALLA — pestaña Calidad de datos, desplazarse a la tabla de incidencias]**

> En la base de prueba hay cuarenta y cuatro tickets abiertos. Miren la diferencia entre estos dos.
>
> Este ticket tiene un grupo, una sesión y un docente interno. El gestor lo resuelve en una llamada.
>
> [señalar en pantalla] Y este tiene seis grupos, tres sesiones por grupo —dieciocho sesiones— y un docente externo que hay que contratar por compras públicas: requisición, especificaciones, cotizaciones, adjudicación.
>
> Al turno rotativo, esos dos tickets valen exactamente lo mismo: uno.

**[CÁMARA]**

> Eso explica la queja de los gestores: sobrecarga asimétrica con el mismo número de tickets. Y es lo que esta herramienta corrige.

---

# BLOQUE 2 — Análisis de datos (1:30 – 3:30)

**[PANTALLA — pestaña Calidad de datos completa]**

> El archivo tiene doce hojas. Siete son fuentes de datos y cinco son tableros del Excel original.
>
> La herramienta no asume que los datos vienen limpios. Los audita, y encontró veinticuatro incidencias.

**[señalar la tabla]**

> Cinco tickets abiertos no tienen fecha de inicio: no se pueden programar.
> Una fecha de sesión es imposible de interpretar: `19/011/2026`, con un cero de más.
> Hay nueve sesiones reprogramadas —misma clave, dos fechas distintas— y un ticket duplicado en el Registro.
>
> Cada incidencia muestra qué hizo la herramienta con ella. Nada se corrige en silencio.

**[PANTALLA — señalar tres filas concretas]**

> Y tres hallazgos que el enunciado no anticipa y que cambian el modelo.

**[CÁMARA, contar con los dedos — son tres, vale la pena enumerarlos]**

> **Uno.** El Excel calcula los días hábiles con una fórmula que no es NETWORKDAYS. Cuenta lunes a viernes incluyendo ambos extremos y **no descuenta asuetos**. Lo cotejé contra las ciento seis filas del archivo: ciento cuatro coinciden con esa regla. Los plazos que reporta el Excel son sistemáticamente más holgados que la realidad.
>
> **Dos.** La hoja de sesiones no trae gestor, ni modalidad, ni marca de obligatoriedad. Todo eso hay que derivarlo cruzando con el Registro. La obligatoriedad no es una columna: está en el texto libre de Observaciones, en tres variantes distintas.
>
> **Tres.** Y el más importante.

**[PANTALLA — volver a la herramienta, ir a Equipo]**

> Hay tres días en el calendario con más sesiones que gestores. El trece de octubre tiene ocho sesiones: cinco de ellas obligatorias. Con cinco gestores, y con la regla de un solo evento por día por gestor, ese día **no tiene solución**. Es aritmética, no un fallo del programa.
>
> Lo explico en detalle cuando lleguemos al modelo.

---

# BLOQUE 3 — Modelo matemático (3:30 – 6:00)

**[CÁMARA — esta es la parte conceptual, mirar a cámara]**

> El modelo reemplaza el conteo de tickets por un **índice de carga ponderada**:
>
> carga = alfa por el peso del docente, más beta por el factor de modalidad por las sesiones, más gamma por el logaritmo de participantes.
>
> Alfa es cero punto seis, beta cero punto treinta y cinco, gamma cero punto cero cinco.

**[PANTALLA — pestaña Mesa de entrada, bajar a "Trazabilidad del cálculo"]**

> El peso del docente va de uno para interno, uno punto ocho para cooperante y tres punto cinco para externo, porque la contratación pública es la parte administrativa más pesada.
>
> La modalidad multiplica ese componente: un evento asincrónico vale cero punto doce, porque se traslada al Departamento de Formación Virtual y el gestor no supervisa sesiones.
>
> Y el logaritmo de participantes evita que un grupo de cien personas valga diez veces un grupo de diez. El trabajo de coordinación no crece linealmente con la matrícula.

**[CÁMARA]**

> La función objetivo minimiza la diferencia entre la carga máxima y la mínima, más una penalización por plazo incumplido, más una penalización por días saturados, más la antigüedad.

**[PANTALLA — volver a Equipo]**

> Y aquí están las tres correcciones que hice al modelo del enunciado.

**[CÁMARA, pausado — estas tres son el corazón de la defensa]**

> **La primera.** El enunciado pide que el muestreo aleatorio cubra al menos el veinticinco por ciento de las sesiones regulares, pero lo formula sumando sobre **todos** los gestores. Vista así, la restricción se cumple si el conjunto completo cubre el mínimo global, aunque un gestor concreto no supervise ni una sola sesión. En mi modelo el mínimo se exige **por gestor**, sobre sus propias sesiones.
>
> **La segunda.** El enunciado propone que la sesión obligatoria quede asignada al gestor dueño del ticket. Eso impide usar un gestor de apoyo, que el propio documento autoriza en las preguntas frecuentes. Lo separé: el dueño intenta cubrir y, si el día está saturado, una variable de holgura permite el apoyo, con penalización.
>
> **La tercera, y la más peligrosa.** El modelo del enunciado no exige que una sesión se supervise **el día en que ocurre**. Sin esa restricción, el solver puede mover supervisiones a días libres y reportar cero colisiones de forma artificial. Un resultado que parece perfecto y es falso. Yo lo sufrí durante el desarrollo y lo cuento en el anexo de IA.

**[CÁMARA]**

> Por eso el verificador es independiente del solver. No comparte una línea de código con el modelo que valida. Si el modelo tiene un error conceptual, el verificador lo detecta en lugar de confirmarlo.

---

# BLOQUE 4 — PRUEBA 1: Optimización inicial (6:00 – 8:30)

**[PANTALLA — pestaña Equipo, vista limpia]**

> **Prueba uno.** Optimización inicial y detección de choques.

**[señalar la tabla de gestores]**

> Este es el estado actual. Miren estas tres filas: Gestor uno, Gestor tres y Gestor cuatro tienen **diez tickets cada uno**.

**[señalar la columna de carga]**

> Y sus cargas son veinte treinta y seis, veinticuatro cincuenta y doce cero siete.

**[CÁMARA]**

> El mismo número de tickets. El doble de carga en uno que en otro. Este es el problema del turno rotativo, medido.

**[PANTALLA]**

> El indicador de desbalance está en **dos punto cero tres**. Eso significa que el gestor más cargado tiene el doble de trabajo que el menos cargado.

**[señalar la gráfica, sin optimizar todavía]**

> Y en el calendario actual hay **veinticuatro días** con más de una sesión por gestor. El trece de octubre tiene ocho sesiones para cinco gestores.

**Ahora la optimización.** [clic en "Optimizar y rebalancear"]

**[esperar el resultado — menos de un segundo]**

> Seis tickets reasignados. De cuarenta y cuatro.

**[señalar el panel de resultado]**

> El desbalance baja de dos punto cero tres a **uno punto cero uno**. Prácticamente perfecto.
>
> Y miren cuánto costó: **seis movimientos**. No reorganicé la cartera, moví seis tickets.

**[señalar la tabla de movimientos]**

> El Gestor cuatro recibe cuatro de esos seis, porque era quien tenía capacidad ociosa. Fíjense en algo: el Gestor cuatro pasa de diez a catorce tickets.
>
> **Más tickets, la misma carga.** Porque los tickets que recibe son de peso bajo y los que cede el Gestor tres son de peso alto. Eso es exactamente lo que el conteo nominal no captura.

**[señalar el calendario]**

> Y el calendario: **cero colisiones**. Cincuenta y cinco de cincuenta y cinco sesiones obligatorias cubiertas.

**[Bajar al panel de días saturados — debe estar visible]**

> Aquí está el detalle honesto: tres días siguen marcados como saturados. El trece de octubre, con ocho sesiones y cinco gestores, no se puede resolver. La herramienta lo declara en lugar de inventar una asignación.

**[CÁMARA]**

> Y eso es una decisión de diseño, no una limitación. Un software que reportara cero problemas en ese día estaría mintiendo.

---

# BLOQUE 5 — PRUEBA 2: Vacaciones (8:30 – 10:15)

**[PANTALLA — pestaña Equipo, panel de vacaciones]**

> **Prueba dos.** Baja por vacaciones.

**[seleccionar Gestor 1, fechas 12 a 30 de octubre]**

> El Gestor uno sale de vacaciones del doce al treinta de octubre. Casi tres semanas.

**[clic en "Registrar vacaciones y rebalancear"]**

**[esperar]**

> El sistema bloquea sus fechas y redistribuye la carga entre los cuatro restantes.

**[señalar la tabla]**

> El Gestor uno queda en estado Vacaciones. Si lo verifican en el calendario, no tiene ninguna sesión entre esas fechas.

**[señalar las cargas]**

> Y los cuatro gestores restantes quedan en veinticuatro punto ocho, veinticuatro punto ocho, veinticuatro punto nueve y veinticuatro punto ocho. Reparto equitativo entre los que quedan.

**[bajar al diagnóstico de capacidad]**

> Pero aquí está lo interesante.

**[señalar el trece de octubre]**

> El trece de octubre tenía cinco sesiones obligatorias. Con un gestor menos, quedan **cuatro** gestores disponibles para cinco sesiones.

**[CÁMARA, pausado]**

> Cinco es mayor que cuatro. No hay asignación posible que respete la regla de un evento por día.

**[PANTALLA — señalar las violaciones]**

> El sistema reporta: sesión obligatoria `6377` sin supervisión, día saturado, más sesiones obligatorias que gestores disponibles.
>
> Y fíjense en el conteo: **cincuenta y cuatro de cincuenta y cinco**. No cincuenta y cinco de cincuenta y cinco.

**[CÁMARA]**

> Si el programa mostrara cincuenta y cinco de cincuenta y cinco con cuatro gestores, estaría violando la restricción de un evento diario o poniendo la sesión en un día que no corresponde. Prefiero declarar la infactibilidad.
>
> La acción de gestión que se deriva es concreta: para esas tres fechas del trimestre, reprogramar o habilitar un gestor de apoyo.

---

# BLOQUE 6 — PRUEBA 3: Cambio dinámico de docente (10:15 – 12:00)

**[PANTALLA — pestaña Simulador]**

> **Prueba tres.** Cambio dinámico a contratación externa.

**[seleccionar `6376-PFIN-26`, tipo Externo, clic en "Simular impacto"]**

> Este ticket inicia el veintidós de octubre con un docente interno. Faltan nueve días hábiles.

**[señalar el panel de resultado]**

> Antes: semáforo ámbar, con un día de holgura sobre los ocho que exige un docente interno.

**[señalar el después]**

> Después: **rojo**, con menos veintiún días de holgura. La contratación externa exige treinta días hábiles y solo hay nueve.
>
> El peso del ticket sube de uno punto tres a dos punto ocho, y la carga del gestor también.

**[CÁMARA]**

> Ahora el contraste, con otro ticket.

**[seleccionar `6286-PFIN-26`, tipo Externo, simular]**

> Mismo cambio. Pero este inicia el veinticuatro de noviembre, con treinta y dos días hábiles disponibles.

**[señalar]**

> Pasa de verde a ámbar. Dos días de holgura. Ajustado, pero viable.

**[CÁMARA, mirar a cámara — este es el punto]**

> Dos tickets, la misma operación, resultados opuestos. Eso es lo que prueba que el semáforo **calcula** y no está codificado. Si ambos dieran el mismo color, el indicador no serviría.

**[PANTALLA]**

> Y hay un hallazgo operativo que salió de aquí. De los veinte tickets activos con docente interno, **dieciocho quedan en rojo** al convertirlos a externo.

**[CÁMARA]**

> No es un defecto del modelo. Es el problema real del departamento: la contratación externa exige treinta días hábiles, y el HelpDesk recibe tickets con menos de ese margen. Cualquier política que ignore ese desfase está condenada a incumplir.

---

# BLOQUE 7 — Cierre y uso de IA (12:00 – 13:30)

**[CÁMARA]**

> Los resultados, en una tabla.

**[PANTALLA — opcional, o mostrar el informe]**

> El desbalance pasa de dos punto cero tres a uno punto cero uno, moviendo seis tickets de cuarenta y cuatro.
> Las colisiones bajan de veinticuatro días a cero.
> La cobertura de sesiones obligatorias es del cien por ciento, salvo los días que son aritméticamente imposibles.
> Y el muestreo regular cubre veintiocho por ciento, por encima del veinticinco exigido.

**[CÁMARA]**

> Tres cosas que no resolví y que declaro.
>
> El modelo **no reprograma** sesiones. Toma las fechas como dadas. Si el trece de octubre tiene ocho sesiones, lo reporta pero no propone mover ninguna.
>
> Los pesos están razonados, no medidos contra tiempos reales. Validarlos requeriría registrar horas por ticket y fase.
>
> Y el costo de reasignación es un parámetro calibrado empíricamente, no una medición.

**[PANTALLA — Anexo A del informe, si se puede mostrar]**

> Sobre el uso de inteligencia artificial. El anexo documenta seis errores reales que la IA cometió durante el desarrollo.
>
> El más serio: la primera versión del calendario reportaba cero colisiones y era falso, porque no exigía que la sesión se supervisara el día en que ocurre. El solver movía las supervisiones a días libres.
>
> [CÁMARA] Lo detecté porque el verificador no comparte código con el solver. Si lo hubiera reutilizado, habría confirmado el error.
>
> El segundo: el modelo movía treinta y ocho de cuarenta y cuatro tickets porque una penalización se redondeaba a cero. Matemáticamente correcto, operativamente inaplicable.
>
> Documentar esos errores y sus correcciones es parte de la entrega, y es lo que hace verificable el trabajo.

**[CÁMARA, plano medio — cierre]**

> La herramienta está publicada en GitHub con Docker, así que se puede levantar con un solo comando sin instalar nada.
>
> Lo que la herramienta demuestra no es que el departamento esté mal gestionado, sino que **el problema estaba mal definido**. Asignar por turno rotativo es correcto si el trabajo es homogéneo. Aquí no lo es, y hasta que se mide la carga real, cualquier política de reparto —incluso una más justa— va a seguir produciendo la misma queja.
>
> Gracias.

---

## Anexo: frases de enlace (si una toma no queda)

Por si hay que regrabar y las transiciones suenan secas:

- Antes de una prueba: *"Vamos a la primera prueba: la optimización inicial."*
- Al mover el ratón a un gráfico: *"Miren este dato, porque es el que importa."*
- Al obtener un resultado inesperado: *"Y esto es exactamente lo que esperaba encontrar."*
- Si algo falla en vivo: *"El sistema está mostrando un caso que ya anticipé; déjenme explicarlo."* (nunca decir "esto no debería pasar" sin explicar por qué)

## Anexo: defensa anticipada de preguntas

Si el profesor pregunta después:

| Pregunta probable | Respuesta corta |
| :--- | :--- |
| ¿Por qué CP-SAT y no Solver de Excel? | Variables binarias, restricciones de equidad entre máximos y mínimos, y conteo de movimientos. Un LP relajado daría valores fraccionarios. |
| ¿Por qué solo mueves 6 tickets? | Porque mover un ticket en curso tiene costo operativo. Sin ese costo el solver movía 38 de 44, que es inaplicable. |
| ¿Por qué hay días sin resolver? | Porque tienen más sesiones obligatorias que gestores. Es aritmética. Declararlo es más honesto que esconderlo. |
| ¿Los pesos son inventados? | Son razonados a partir de las reglas del enunciado, no medidos. Es una limitación que declaro. Validarlos requiere registro de horas. |
| ¿Cómo sé que el calendario es correcto? | Porque un verificador independiente, que no comparte código con el solver, comprueba ocho reglas sobre el resultado. |
