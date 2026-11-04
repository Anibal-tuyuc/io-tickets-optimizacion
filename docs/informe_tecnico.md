# Universidad Mariano Gálvez de Guatemala

**Facultad de Ingeniería en Sistemas de Información y Ciencias de la Computación**
**Curso:** Investigación de Operaciones — Sexto Semestre

---

# Herramienta de Optimización Asistida por IA para la Asignación Equitativa de Tickets y Programación de Acompañamiento Docente

**Modalidad:** Individual
**Autor:** Aníbal Tuyuc
**Fecha de entrega:** 10 de noviembre de 2026

---

## Resumen ejecutivo

El Departamento de Docencia recibe solicitudes de capacitación a través de un HelpDesk y las asigna a uno de cinco gestores académicos mediante un turno rotativo. Esa política supone que todo ticket representa la misma cantidad de trabajo, cuando en realidad un ticket puede exigir una sesión con un docente interno, o bien dieciocho sesiones con un docente externo que debe contratarse mediante compras públicas.

Este trabajo desarrolla una herramienta que reemplaza ese supuesto por un modelo de carga ponderada. Sobre los 44 tickets abiertos de la base de prueba, la asignación vigente arroja un desbalance de **2.03×** entre el gestor más cargado y el menos cargado; tres gestores con exactamente diez tickets tienen cargas de 24.50, 20.36 y 12.07 unidades. El modelo propuesto reduce ese desbalance a **1.01×** moviendo únicamente **6 de 44 tickets**, y programa el acompañamiento docente con **cero colisiones diarias** y **100 % de cobertura de las sesiones obligatorias**.

El análisis de la base reveló tres hallazgos que el enunciado no anticipa y que condicionan el modelo: el cálculo de días hábiles del Excel no descuenta asuetos; tres días del calendario tienen más sesiones obligatorias que gestores disponibles, lo que hace **infactible** la restricción de un evento diario por gestor; y la restricción de muestreo propuesta en el enunciado está formulada de forma que se satisface trivialmente. Los tres se documentan y se corrigen.

---

## Índice

1. [Análisis del proceso](#1-análisis-del-proceso)
2. [Análisis de la base de datos](#2-análisis-de-la-base-de-datos)
3. [Formulación matemática del modelo](#3-formulación-matemática-del-modelo)
4. [Diseño del algoritmo](#4-diseño-del-algoritmo)
5. [Arquitectura e implementación](#5-arquitectura-e-implementación)
6. [Manual de usuario](#6-manual-de-usuario)
7. [Manual técnico](#7-manual-técnico)
8. [Pruebas de validación](#8-pruebas-de-validación)
9. [Resultados](#9-resultados)
10. [Limitaciones y trabajo futuro](#10-limitaciones-y-trabajo-futuro)
11. [Anexo A — Bitácora de uso de IA](#anexo-a--bitácora-de-uso-de-ia)
12. [Anexo B — Diccionario de datos](#anexo-b--diccionario-de-datos)
13. [Anexo C — Evidencia de ejecución](#anexo-c--evidencia-de-ejecución)

---

# 1. Análisis del proceso

## 1.1 Flujo actual

El HelpDesk genera un número de ticket con formato `NNNN-PPPP-AA` (por ejemplo `6281-PFIN-26`). La Mesa de Entrada lo registra en una matriz de Excel y lo asigna de inmediato a un gestor siguiendo estrictamente el turno rotativo, sin consultar la carga acumulada de cada gestor.

Una vez asignado, el gestor ejecuta cuatro fases:

| Fase | Actividades | Variable de carga dominante |
| :--- | :--- | :--- |
| Gestión del docente | Identificación, nombramiento, coordinación o contratación | Tipo de docente |
| Coordinación académica | Reunión de mediación andragógica | Ninguna (constante por ticket) |
| Ejecución | Seguimiento, observación en aula, atención de consultas | Número de sesiones y modalidad |
| Cierre | Evaluaciones, notas, informe, archivo | Ninguna (constante por ticket) |

El punto crítico es que **solo la fase de ejecución consume tiempo de calendario**. La gestión del docente y el cierre consumen tiempo de gestión, pero no bloquean días. El modelo debe distinguir ambas dimensiones: la carga acumulada (para el balance) y la ocupación diaria (para el calendario).

## 1.2 Las cinco reglas de negocio

**Regla 1 — Capacidad dinámica.** El número de gestores no puede estar codificado. La herramienta debe permitir altas y bajas temporales en tiempo de ejecución, reasignando la carga pendiente de quien se ausenta.

**Regla 2 — Complejidad administrativa.** El tipo de docente determina el peso y el plazo previo al inicio:

| Tipo | Peso base | Plazo mínimo |
| :--- | ---: | ---: |
| Interno | 1.0 | 5–8 días hábiles |
| Cooperante | 1.8 | 10–15 días hábiles |
| Externo (contratación) | 3.5 | 20–30 días hábiles |

El cambio de tipo en mitad de la gestión —frecuente, y presente en 20 de los 112 tickets— debe recalcular peso, alerta de plazo y balance.

**Regla 3 — Rutas de trabajo.** Los eventos presenciales, sincrónicos y mixtos (Ruta A) consumen el ciclo completo del gestor. Los asincrónicos se trasladan al Departamento de Formación Virtual (Ruta B): el gestor no supervisa sesiones ni bloquea calendario, y solo recupera el ticket para el cierre.

**Regla 4 — Restricciones duras de calendario.** Máximo un evento supervisado por gestor y día; cobertura obligatoria del 100 % de las sesiones críticas (docente nuevo, primera vez, tema nuevo); muestreo controlado del resto.

**Regla 5 — Prioridad y antigüedad.** La prioridad (Urgente > Alta > Media > Baja) y los días transcurridos desde el ingreso deben influir en la asignación, para que un ticket urgente no quede estancado en un gestor saturado.

## 1.3 Por qué falla el turno rotativo

El turno rotativo es correcto si y solo si el trabajo por ticket es homogéneo. Sobre los datos reales no lo es:

- Los 44 tickets abiertos varían entre 1 y 18 sesiones programadas.
- 17 son de docente externo (peso 3.5), 7 de cooperante (1.8) y 20 de interno (1.0).
- 12 son de Ruta B y no deberían consumir calendario en absoluto.

Como el turno rotativo no observa ninguna de esas tres dimensiones, el resultado es el que reportan los gestores: saturación asimétrica con el mismo número de tickets.

---

# 2. Análisis de la base de datos

## 2.1 Estructura

El archivo `Control_Prueba_IO.xlsx` contiene doce hojas. Siete son fuentes de datos y cinco son tableros del Excel original que se usaron como referencia visual, no como insumo.

| Hoja | Filas útiles | Fila de encabezado | Observación |
| :--- | ---: | ---: | :--- |
| `Registro` | 113 | 7 | Tabla maestra; la columna A está vacía, los datos empiezan en B |
| `GestionDocente` | 110 | 7 | Días hábiles precalculados con fórmula |
| `EjecucionXGrupos` | 333 | 4 | La fila 3 contiene totales sueltos |
| `Sesiones` | 389 | 4 | 363 con fecha válida |
| `Docentes` | 342 | 4 | Docente por ticket y grupo |
| `DB_Docentes` | 1441 | 1 | Catálogo limpio |
| `Listas` | 57 | 1 | Catálogos de validación |

**Consecuencia de diseño:** cada hoja tiene su encabezado desplazado a una fila distinta. El lector debe declarar por hoja la fila de encabezado y las columnas a descartar. Un lector genérico falla silenciosamente y reporta cero registros.

## 2.2 La hoja `Sesiones` está incompleta por diseño

`Sesiones` no contiene gestor, modalidad ni marca de obligatoriedad. Esos tres datos —los tres que el algoritmo de calendario necesita— deben derivarse cruzando la columna `No. Solicitud` contra `Registro`.

La marca de obligatoriedad no existe como columna: está codificada en el texto libre de `Observaciones`. Las seis categorías presentes son:

| Valor de `Observaciones` | Frecuencia | Interpretación para el modelo |
| :--- | ---: | :--- |
| `TRASLADO A DFV - Ruta B` | 25 | Carga de ejecución ≈ 0; no ocupa calendario |
| `CAMBIO DINÁMICO: Interno a Externo` | 20 | Ticket ya migrado; insumo de la Prueba 3 |
| `REGULAR - Muestreo Aleatorio` | 20 | Sujeto a muestreo θ |
| `OBLIGATORIO - Docente Nuevo` | 18 | Cobertura 100 % |
| `OBLIGATORIO - Primera Vez` | 15 | Cobertura 100 % |
| `OBLIGATORIO - Tema Nuevo` | 14 | Cobertura 100 % |

Las 47 sesiones obligatorias se reparten entre los tres criterios, que el enunciado trata como equivalentes pero que en los datos son tres etiquetas distintas.

## 2.3 Calidad de los datos: 24 incidencias detectadas

La herramienta no corrige en silencio: registra cada defecto con su acción tomada. El panel *Calidad de datos* los expone al usuario.

| Gravedad | Incidencia | Casos | Acción tomada |
| :--- | :--- | ---: | :--- |
| Alta | Ticket abierto sin fecha de inicio | 5 | Se incluye en el balance; excluido del calendario |
| Media | Fecha de sesión no interpretable (`19/011/2026`) | 1 | Sesión conservada sin fecha |
| Media | Ticket duplicado en el Registro | 1 | Se conserva la primera aparición |
| Media | Fecha de inicio difiere entre hojas | 1 | Prevalece el Registro |
| Baja | Ticket abierto desde 2025 (legado) | 3 | Se incluye, marcado para revisión |
| Baja | Sesión reprogramada (misma clave, dos fechas) | 9 | Se tratan como sesiones distintas |
| Baja | Días hábiles discrepan con el recálculo | 3 | Prevalece el recálculo |
| Baja | Sesiones sin fecha (modalidad asincrónica) | 27 | Excluidas del calendario |

Los cinco tickets abiertos sin fecha son `5795`, `5796`, `5797-PFAN-26`, `6384` y `6404-PFIN-26`. El modelo los incluye en el balance de carga —trabajo pendiente son— pero no puede programarlos ni calcular su plazo.

## 2.4 Hallazgo 1: el cálculo de días hábiles del Excel es incorrecto

La hoja `GestionDocente` calcula la columna `Dias hábiles para el inicio` con una fórmula que **no es `NETWORKDAYS`**. Al cotejar las 106 filas contra distintas hipótesis:

| Hipótesis | Coincidencias |
| :--- | ---: |
| `NETWORKDAYS` con asuetos de Guatemala, excluyendo extremos | 0 / 106 |
| Lunes a viernes, inclusive ambos extremos, sin asuetos | **104 / 106** |

Las dos filas restantes tienen las fechas invertidas en origen (asignación posterior al inicio), lo que produce valores negativos en el Excel.

El modelo implementa **ambas** versiones: `dias_habiles_excel()` para auditar contra el archivo, y `dias_habiles_entre()` —con asuetos, excluyendo extremos— que es la definición correcta y la que usa el motor de plazos. La discrepancia se reporta en el panel de calidad.

Esto importa operativamente: entre el 1 de mayo y el 31 de diciembre de 2026 hay cuatro asuetos oficiales que el Excel ignora, por lo que sus plazos son sistemáticamente más holgados que la realidad.

## 2.5 Hallazgo 2: tres días del calendario son infeasibles

Sobre los 44 tickets abiertos hay 122 sesiones fechadas, entre el 21 de septiembre y el 9 de diciembre de 2026. Al agrupar por día:

| Fecha | Sesiones | Obligatorias | Gestores | Faltan |
| :--- | ---: | ---: | ---: | ---: |
| 2026-10-13 | **8** | 5 | 5 | 3 |
| 2026-10-12 | **7** | 3 | 5 | 2 |
| 2026-10-26 | **6** | 2 | 5 | 1 |

Con la restricción "máximo un evento por gestor y día", esos tres días **no admiten solución factible ni con los cinco gestores**. El 13 de octubre requeriría ocho gestores disponibles y solo hay cinco.

La restricción del enunciado, `Σ_g y_{s,g,d} ≤ 1 ∀g,∀d`, es por tanto incapaz de satisfacerse en esos días. Un modelo que la imponga como restricción dura devolverá "infactible" sin explicar por qué, y un modelo que la relaje en silencio producirá colisiones ocultas.

**Solución adoptada:** variable de holgura penalizada y declaración explícita.

```
Σ_g y_{s,g,d} + u_{s,d} = 1     ∀ s ∈ S_ob
```

con `u_{s,d}` penalizada con peso 1000 en la función objetivo. Si `u = 1`, el sistema emite la alerta *DÍA SATURADO — requiere gestor de apoyo externo*, con la lista de sesiones en conflicto. Es exactamente el escenario que el FAQ del enunciado contempla cuando sugiere asignar un gestor de apoyo.

## 2.6 Hallazgo 3: la restricción de muestreo del enunciado es trivialmente satisfacible

El enunciado propone:

```
Σ_{s ∈ S_reg} y_{s,g,d} ≥ ⌈θ · |S_reg|⌉
```

Sumando sobre todos los gestores y todos los días, la restricción se satisface con que el conjunto completo de gestores cubra el mínimo global, aunque un gestor concreto no supervise ni una sola sesión. Un gestor podría quedar con 0 % de muestreo mientras otro absorbe el 100 % global.

**Solución adoptada:** el mínimo se exige **por gestor dueño del ticket**, calculado sobre sus propias sesiones regulares:

```
Σ_{s ∈ S_reg(g)} y_{s} ≥ ⌈θ · |S_reg(g)|⌉     ∀ g ∈ G
```

El verificador independiente comprueba esta condición gestor por gestor (véase §8.2).

## 2.7 Hallazgo 4: falta una restricción esencial en el enunciado

El enunciado no impone que una sesión solo pueda supervisarse **el día en que realmente ocurre**. Sin esa restricción, el solver puede "mover" supervisiones a días libres y reportar cero colisiones de forma artificial.

Es el error más peligroso del ejercicio, porque produce un resultado que parece correcto. Se añadió:

```
y_{s,g,d} = 0     si d ≠ fecha(s)
```

y un verificador independiente que comprueba la fecha real de cada sesión asignada (§8.2, regla `fecha_incorrecta`).

---

# 3. Formulación matemática del modelo

## 3.1 Conjuntos e índices

| Símbolo | Descripción |
| :--- | :--- |
| `G` | Gestores activos, `g = 1…m` |
| `T` | Tickets abiertos, `i = 1…n` (`n = 44` en los datos de prueba) |
| `S` | Sesiones de Ruta A de tickets abiertos (`|S| = 122`) |
| `S_ob` | Sesiones obligatorias (`|S_ob| = 55`) |
| `S_reg` | Sesiones regulares (`|S_reg| = 67`) |
| `D` | Días del horizonte de planificación |
| `S_d` | Sesiones que ocurren el día `d` |

## 3.2 Parámetros

**Peso del docente** (Regla 2):

```
PesoDocente(Interno) = 1.0
PesoDocente(Cooperante) = 1.8
PesoDocente(Externo) = 3.5
```

**Factor de modalidad** (Regla 3):

```
FactorModalidad(Presencial) = 1.00
FactorModalidad(Mixto) = 1.10
FactorModalidad(Virtual Sincrónico) = 0.90
FactorModalidad(Virtual Asincrónico) = 0.12
```

El factor 0.12 de la Ruta B no es arbitrario: refleja que el gestor solo conserva las tareas de coordinación inicial y cierre, sin seguimiento diario.

**Índice de carga ponderada:**

```
W_i = α · PesoDocente(TD_i)
    + β · FactorModalidad(M_i) · Sesiones_i
    + γ · ln(1 + Participantes_i)

α = 0.60,  β = 0.35,  γ = 0.05
```

El término logarítmico en participantes satura el efecto de grupos grandes: pasar de 10 a 110 participantes no multiplica por once el trabajo de gestión, porque el esfuerzo crece con la coordinación, no linealmente con la matrícula.

**Carga por gestor:**

```
L_g = Σ_i W_i · x_{i,g}
```

**Plazos requeridos:** `ReqDias(Interno) = 8`, `(Cooperante) = 15`, `(Externo) = 30`. Se toma el extremo alto del rango sugerido, criterio conservador.

## 3.3 Variables de decisión

```
x_{i,g} ∈ {0,1}     ticket i asignado al gestor g
y_{s,g} ∈ {0,1}     sesión s supervisada por el gestor g
u_s     ∈ {0,1}     sesión obligatoria sin cobertura (holgura)
Cmax, Cmin ≥ 0      carga máxima y mínima
```

## 3.4 Función objetivo

```
min Z = w1 · (Cmax − Cmin)                       equidad
      + w2 · Σ_i PenalizacionPlazo_i             retraso vs. inicio
      + w3 · Σ_s u_s                             días saturados
      + w4 · Σ_i urgencia_i · movido_i           antigüedad y prioridad

w1 = 1.0   w2 = 3.0   w3 = 50.0   w4 = 0.8
```

La penalización por movimiento (`movido_i`) merece explicación. Mover un ticket en curso tiene costo operativo real: el gestor nuevo debe reconstruir el contexto. Si ese costo no se modela, el solver reorganiza la cartera completa para lograr una equidad perfecta. En la primera versión del modelo, con una penalización de 0.15 que el redondeo entero convertía en cero, el solver movía **38 de 44 tickets** —técnicamente óptimo, operativamente absurdo.

Con `COSTO_MOVIMIENTO = 6.0` y un presupuesto de 6 movimientos, el resultado es aplicable:

| Movimientos permitidos | Ratio resultante |
| ---: | ---: |
| Sin límite | 1.007 |
| 6 | 1.007 |
| 4 | 1.02 |
| 3 | 1.05 |
| 0 (actual) | 2.03 |

## 3.5 Restricciones

**(1) Asignación única**

```
Σ_g x_{i,g} = 1     ∀ i ∈ T
```

**(2) Capacidad dinámica** (Regla 1)

```
x_{i,g} = 0     si g no está activo
y_{s,g} = 0     si d ∈ vacaciones(g)
```

**(3) No colisión diaria** (Regla 4.1)

```
Σ_{s ∈ S_d} y_{s,g} ≤ 1     ∀ g ∈ G, ∀ d ∈ D
```

**(4) Cobertura obligatoria con holgura** (Regla 4.2, corregida)

```
Σ_g y_{s,g} + u_s = 1     ∀ s ∈ S_ob
```

**(5) Muestreo mínimo por gestor** (Regla 4.3, corregida)

```
Σ_{s ∈ S_reg(g)} y_{s,g} ≥ ⌈θ · |S_reg(g)|⌉     ∀ g ∈ G
```

**(6) Fecha real** (añadida)

```
y_{s,g} = 0     si el día de la sesión s no es el día de la supervisión
```

**(7) Solo el gestor dueño, salvo apoyo declarado**

```
y_{s,g} ≤ x_{i(s),g} + apoyo_s
```

**(8) Definición de Cmax y Cmin**

```
Cmax ≥ L_g ≥ Cmin     ∀ g ∈ G
```

## 3.6 Diferencias respecto del modelo del enunciado

| Elemento | Enunciado | Este trabajo | Motivo |
| :--- | :--- | :--- | :--- |
| Muestreo | Suma global | Por gestor | La global se satisface trivialmente |
| Obligatorias | `y = x` | `Σy + u = 1` | `y = x` impide el gestor de apoyo que el propio FAQ autoriza |
| Fecha real | No contemplada | Restricción (6) | Sin ella el calendario reporta cero choques falsos |
| Días saturados | No contemplados | Holgura penalizada | Tres días son infeasibles con los datos reales |
| Costo de movimiento | No contemplado | `w4` con presupuesto | Sin él la solución es inaplicable |

---

# 4. Diseño del algoritmo

## 4.1 Decisión: CP-SAT sobre LP relajado

Se usa **OR-Tools CP-SAT** en lugar de un solver de programación lineal continua por tres razones:

1. Todas las variables de decisión son binarias. Un LP relajado daría valores fraccionarios que habría que redondear con heurísticas ad hoc.
2. La restricción de equidad (`Cmax − Cmin`) y el conteo de movimientos se expresan de forma natural como enteros.
3. El tamaño del problema (44 tickets × 5 gestores + 122 sesiones × 5 gestores) resuelve en menos de 0.05 s, muy por debajo del umbral de tiempo real.

## 4.2 Algoritmo de asignación

```
Entrada: tickets abiertos T, gestores activos G, parámetros
Salida:  x[i,g], movimientos

1. Calcular W_i para cada ticket
2. Modelo CP-SAT:
     variables   x[i,g] binaria
     restricción Σ_g x[i,g] = 1
     restricción Σ movimientos ≤ max_movimientos
     objetivo    w1·(Cmax − Cmin) + w4·Σ urgencia·movido
3. Resolver con límite de 30 s, 8 hilos
4. Si no hay solución factible → error explícito
5. Extraer asignación y comparar con la previa
```

## 4.3 Algoritmo de calendario (dos etapas)

**Etapa 1 — obligatorias.** Modelo CP-SAT sobre las 55 sesiones obligatorias:

```
variables   y[s,g] binaria, u[s] binaria
restricción Σ_g y[s,g] + u[s] = 1
restricción Σ_{s∈día d} y[s,g] ≤ 1
restricción y[s,g] = 0 si g no disponible ese día
objetivo    min Σ 1000·u[s] + Σ 5·apoyo[s] + Σ 1·carga[g]
```

El término `5·apoyo[s]` prefiere al gestor dueño del ticket. El término `Σ carga[g]` reparte las supervisiones entre gestores para que un solo gestor no absorba todas.

**Etapa 2 — regulares (muestreo).** Esta etapa no usa CP-SAT porque el muestreo debe ser aleatorio por definición del enunciado. Procedimiento:

```
para cada gestor g (orden alfabético, reproducible):
    minimo = ⌈θ · |S_reg(g)|⌉
    ordenar sus sesiones por carga global del día ascendente
    desempatar aleatoriamente con semilla = 20261008
    para cada sesión en ese orden:
        si el gestor tiene el día libre → asignar
        si no → buscar gestor de apoyo libre ese día
        si nadie puede → dejar sin cubrir (el verificador lo reporta)
        detener al alcanzar `minimo`
```

Resultado: **19 de 67** sesiones regulares cubiertas (28.4 %, por encima del 25 % exigido), con 13 supervisiones delegadas a gestores de apoyo.

## 4.4 Verificación independiente

El error metodológico más frecuente en este tipo de trabajo es usar el solver como verificador de sí mismo: si el modelo tiene un error conceptual, la verificación lo confirma en lugar de detectarlo.

`app/engine/verificador.py` no importa ni conoce el solver. Recibe el plan ya construido y comprueba ocho reglas:

| Regla | Comprueba |
| :--- | :--- |
| `sesion_duplicada` | Ninguna sesión asignada dos veces |
| `obligatoria_no_cubierta` | Las 55 obligatorias tienen supervisor |
| `muestreo_insuficiente` | Cada gestor alcanza su mínimo individual |
| `fecha_incorrecta` | Cada sesión se supervisa en su fecha real |
| `ruta_b_supervisada` | Ninguna sesión asincrónica tiene supervisor |
| `colision_diaria` | Ningún gestor con dos sesiones el mismo día |
| `gestor_no_disponible` | Ningún gestor supervisa en vacaciones |
| `gestor_ajeno_sin_apoyo` | Un gestor ajeno solo cubre si está declarado como apoyo |

Este verificador detectó el error de fecha real descrito en §2.7 durante el desarrollo (véase Anexo A, iteración 4).

---

# 5. Arquitectura e implementación

## 5.1 Stack

| Capa | Tecnología | Versión |
| :--- | :--- | :--- |
| Ingesta y cálculo | Python + pandas | 3.12 / 3.1.0 |
| Optimización | OR-Tools CP-SAT | 9.15.6755 |
| API | FastAPI + Uvicorn | 0.162.0 / 0.54.0 |
| Calendario hábil | `holidays` (GT) | 0.108 |
| Interfaz | React + TypeScript + Vite | 18.3.1 / 5.5 / 5.4 |
| Gráficas | Recharts | 2.12.7 |
| Pruebas | pytest | 9.2.0 |
| Empaquetado | Docker multi-etapa | 603 MB |

## 5.2 Estructura

```
backend/app/
  core/           config, parámetros del modelo, calendario hábil GT
  etl/            lector del Excel (una config por hoja) + caché
  models/         entidades tipadas del dominio
  engine/         pesos, verificador, solver tickets, solver calendario, SLA
  api/            routers FastAPI + esquemas Pydantic
  services/       estado mutable de la demo + orquestador

frontend/src/
  api/            cliente tipado
  components/     UI compartida (semáforos, KPIs, paneles)
  views/          seis vistas
```

## 5.3 Decisiones de implementación

**El Excel se abre en solo lectura.** El archivo original nunca se modifica. Toda escritura va a `data/results/`.

**Separación entre datos y presentación.** Ningún módulo fuera de `etl` toca pandas ni nombres de columna del Excel. El resto del sistema consume entidades tipadas, lo que permite cambiar el formato de origen sin tocar el motor.

**Estado mutable aislado.** Altas, vacaciones y cambios de docente viven en un único objeto con reinicio explícito (`POST /demo/reset`). La demo del video siempre parte del mismo punto con un clic.

**Caché por fecha de modificación.** El dataset normalizado se serializa en `data/cache/` y se invalida si el Excel cambia. El arranque pasa de 2.8 s a 0.2 s.

---

# 6. Manual de usuario

## 6.1 Instalación con Docker (recomendada)

```bash
docker compose up --build
```

La aplicación queda en `http://localhost:8080`. El puerto es configurable con la variable `IO_PORT`.

La imagen contiene el backend, el frontend compilado y la base de datos de prueba. No requiere instalar Python ni Node.

## 6.2 Instalación en desarrollo

```bash
# Backend
python -m venv .venv
.venv/Scripts/python -m pip install -r backend/requirements.txt
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

# Frontend (otra terminal)
cd frontend && npm install && npm run dev
```

Interfaz en `http://localhost:5173`, documentación de la API en `http://127.0.0.1:8000/docs`.

## 6.3 Las seis vistas

**Tablero.** KPIs y el gráfico comparativo de tickets nominales contra carga ponderada. Es la evidencia central del problema: tres gestores con diez tickets y cargas de 24.50, 20.36 y 12.07.

**Mesa de entrada.** Registro de un ticket nuevo con sugerencia de gestor. La sugerencia muestra la carga actual y resultante de cada candidato, y marca el recomendado.

**Equipo.** Tabla de gestores con estado, alta de gestor nuevo, registro de vacaciones y botón *Optimizar y rebalancear*. Incluye el control de θ (muestreo) y del máximo de reasignaciones.

**Simulador.** Selección de un ticket activo, cambio de tipo de docente y visualización del impacto en peso, carga y semáforo de plazo.

**Calendario.** Programación resultante con filtro por gestor, marca de sesiones obligatorias y de supervisiones de apoyo, y listado de días saturados.

**Calidad de datos.** Auditoría de la base con las 24 incidencias, su gravedad y la acción tomada.

## 6.4 Preparar la demo

El botón **Reiniciar demo** de la barra lateral restaura el estado original. Conviene pulsarlo antes de grabar y antes de cada prueba del video.

---

# 7. Manual técnico

## 7.1 Endpoints principales

| Método | Ruta | Función |
| :--- | :--- | :--- |
| `GET` | `/health` | Estado y conteos del dataset |
| `GET` | `/dashboard` | KPIs, cargas y distribuciones |
| `GET` | `/diagnostico` | Auditoría de calidad de la base |
| `GET` | `/tickets?estado=Abierto` | Tickets con severidad calculada |
| `POST` | `/tickets/nuevo` | Sugerencia de gestor sin crear el ticket |
| `POST` | `/tickets` | Crear ticket y asignarlo |
| `POST` | `/tickets/{id}/cambio-docente` | Simular o aplicar cambio de tipo |
| `GET` | `/recursos` | Estado del equipo y cargas |
| `POST` | `/recursos` | Alta de gestor |
| `POST` | `/recursos/vacaciones` | Registrar baja temporal |
| `DELETE` | `/recursos/{nombre}` | Inhabilitar gestor |
| `POST` | `/optimizar` | Asignación + calendario completo |
| `GET` | `/optimizar/capacidad` | Días con más sesiones que gestores |
| `POST` | `/demo/reset` | Restaurar estado original |

## 7.2 Parámetros configurables

Todos viven en `backend/app/core/model_params.py`. Cambiarlos altera el comportamiento del motor completo; no hay constantes de negocio dispersas.

```python
PESO_DOCENTE        = {"Interno": 1.0, "Cooperante": 1.8, "Externo": 3.5}
REQ_DIAS_HABILES    = {"Interno": 8, "Cooperante": 15, "Externo": 30}
FACTOR_MODALIDAD    = {"Presencial": 1.0, "Mixto": 1.1,
                       "Virtual Sincrónico": 0.9, "Virtual Asincrónico": 0.12}
THETA_MUESTREO_DEFAULT = 0.25
W_EQUIDAD = 1.0   W_PLAZO = 3.0   W_DIA_SATURADO = 50.0   W_ANTIGUEDAD = 0.8
```

Los coeficientes α, β, γ de `W_i` son parte de `PesosCarga` y también son configurables.

## 7.3 Pruebas

```bash
cd backend && ../.venv/Scripts/python -m pytest tests -q
# 34 passed
```

| Archivo | Cobertura |
| :--- | :--- |
| `test_etl.py` | Estructura, integridad, unicidad de IDs, clasificación de observaciones, detección de las 24 incidencias, cotejo de días hábiles |
| `test_pruebas_obligatorias.py` | Las tres pruebas del enunciado más las invariantes del modelo |

---

# 8. Pruebas de validación

## 8.1 Prueba 1 — Optimización inicial y detección de choques

**Estado inicial.** Cargas calculadas sobre los 44 tickets abiertos:

| Gestor | Tickets | Carga W | Sesiones |
| :--- | ---: | ---: | ---: |
| Gestor 1 | 10 | 20.36 | 25 |
| Gestor 2 | 7 | 19.46 | 27 |
| Gestor 3 | 10 | **24.50** | 26 |
| Gestor 4 | 10 | **12.07** | 16 |
| Gestor 5 | 7 | 23.14 | 37 |

`Cmax = 24.50`, `Cmin = 12.07`, rango `12.43`, **ratio 2.03×**, desviación estándar 4.32.

El argumento central: Gestores 1, 3 y 4 tienen exactamente diez tickets cada uno, con cargas de 20.36, 24.50 y 12.07. La diferencia entre el primero y el último es del **102 %**.

**Colisiones actuales.** 24 días tienen más de una sesión para el mismo gestor. El máximo es de ocho sesiones el 13 de octubre y siete el 12 de octubre.

**Resultado tras optimizar** (máximo 6 movimientos):

| Gestor | Tickets | Carga W |
| :--- | ---: | ---: |
| Gestor 1 | 10 | 19.88 |
| Gestor 2 | 7 | 19.96 |
| Gestor 3 | 7 | 19.85 |
| Gestor 4 | 14 | 19.86 |
| Gestor 5 | 6 | 19.98 |

Ratio **1.007×**, rango **0.13**. Movimientos aplicados:

| Ticket | De | A | Peso | Prioridad |
| :--- | :--- | :--- | ---: | :--- |
| `6285-PFIN-26` | Gestor 5 | Gestor 4 | 3.16 | Baja |
| `6376-PFIN-26` | Gestor 3 | Gestor 1 | 1.30 | Media |
| `6384-PFIN-26` | Gestor 3 | Gestor 2 | 2.10 | Baja |
| `6389-PFIN-26` | Gestor 1 | Gestor 4 | 1.78 | Baja |
| `6400-PFIN-26` | Gestor 2 | Gestor 4 | 1.60 | Baja |
| `6412-PFIN-26` | Gestor 3 | Gestor 4 | 1.25 | Alta |

Observación metodológica: el Gestor 4 recibe cuatro de los seis movimientos porque es quien tiene capacidad ociosa. El número nominal de tickets sube de 10 a 14, lo que ilustra que **el conteo de tickets no es el indicador correcto**.

**Calendario.** 55/55 obligatorias cubiertas, 19/67 regulares muestreadas, **0 colisiones**, cobertura total 60.66 %.

## 8.2 Prueba 2 — Baja por vacaciones

Se inhabilita al Gestor 1 del 12 al 30 de octubre.

**Comportamiento esperado y verificado.**

1. El Gestor 1 no recibe ninguna sesión en la ventana: verificado por test.
2. Sus diez tickets se redistribuyen entre los cuatro gestores restantes.
3. El calendario se regenera con cero colisiones.
4. El sistema reporta los días que dejan de ser cubribles.

**Resultado.**

| Métrica | Valor |
| :--- | ---: |
| Colisiones | 0 |
| Obligatorias cubiertas | 54 / 55 |
| Cargas resultantes | G2 24.89, G3 24.88, G4 24.90, G5 24.87 |
| Días saturados | 6 |

**El día 13 de octubre es infeasible.** Con cuatro gestores hay cinco sesiones obligatorias ese día. Es aritmética, no un fallo del algoritmo:

```
5 sesiones obligatorias > 4 gestores disponibles  →  una queda sin cobertura
```

El sistema reporta:
> `[obligatoria_no_cubierta] Sesión obligatoria 6377-PFIN-26|g1|s4|2026-10-13 sin supervisión (día saturado: más sesiones obligatorias que gestores disponibles).`

Un sistema que reportara 55/55 en este escenario estaría violando la restricción de un evento diario o asignando la sesión a un día en que no ocurre. Declarar la infactibilidad es la respuesta correcta.

Los seis días saturados en la ventana son 12, 13, 14, 15, 21 y 26 de octubre. Con la dotación completa solo tres lo eran; la baja temporal añade tres.

## 8.3 Prueba 3 — Cambio dinámico a contratación externa

Con corte al 8 de octubre de 2026 y plazo de 30 días hábiles para contratación externa:

| Ticket | Gestor | Inicio | Días hábiles | Holgura antes | Semáforo antes | Holgura después | Semáforo después |
| :--- | :--- | :--- | ---: | ---: | :--- | ---: | :--- |
| `6376-PFIN-26` | Gestor 3 | 22-oct | 9 | +1 | Ámbar | **−21** | **Rojo** |
| `6286-PFIN-26` | Gestor 4 | 24-nov | 32 | +24 | Verde | +2 | Ámbar |
| `6400-PFIN-26` | Gestor 2 | 16-nov | 26 | +18 | Verde | −4 | Rojo |
| `6412-PFIN-26` | Gestor 3 | 19-oct | 7 | −1 | Rojo | −23 | Rojo |

Los dos primeros forman el contraste que prueba que el semáforo calcula y no está codificado: misma operación, resultados opuestos en función de la fecha de inicio real.

**Impacto en carga.** El peso de cada ticket sube 1.50 unidades (de 1.30 a 2.80 en `6376`, de 0.64 a 2.14 en `6286`), por el cambio de `PesoDocente` de 1.0 a 3.5 ponderado por α = 0.60.

**Consecuencia agregada.** De los 20 tickets abiertos con docente interno, **18 quedan en alerta roja** al convertirse a externo. De los 17 tickets que ya son externos, 15 están en rojo con el corte del 8 de octubre. Esto no es un defecto del modelo: es el hallazgo operativo del ejercicio. La contratación externa exige 30 días hábiles y el departamento recibe tickets con menos de ese margen.

---

# 9. Resultados

## 9.1 Resumen

| Indicador | Antes | Después | Variación |
| :--- | ---: | ---: | ---: |
| Ratio de desbalance | 2.03× | 1.007× | −50 % |
| Rango de carga (W) | 12.43 | 0.13 | −99 % |
| Desviación estándar | 4.32 | 0.04 | −99 % |
| Días con colisión | 24 | 0 | −100 % |
| Tickets movidos | — | 6 / 44 | 13.6 % |
| Cobertura obligatorias | — | 55 / 55 | 100 % |
| Muestreo regulares | — | 19 / 67 | 28.4 % (θ = 25 %) |

## 9.2 Lectura de los resultados

**Mover poco y lograr mucho.** El resultado más defendible no es el ratio, sino la relación entre el ratio y el esfuerzo: seis movimientos bastan para casi eliminar el desbalance. Una propuesta que moviera 38 tickets tendría el mismo ratio final pero sería rechazada en cualquier comité.

**El número de tickets no mide la carga.** El Gestor 4 pasa de 10 a 14 tickets mientras su carga se mantiene en ~19.9. Los cuatro tickets que recibe son de peso bajo; los tickets que cede el Gestor 3 son de peso alto. Es la demostración empírica de la tesis del proyecto.

**La Ruta B distorsiona cualquier métrica ingenua.** Los 12 tickets asincrónicos abiertos suman 17.28 unidades de carga sin bloquear un solo día de calendario. Un modelo que los tratara como presenciales inflaría artificialmente la carga de sus gestores.

## 9.3 Sobre los días saturados

Los tres días infeasibles no son un defecto a corregir, son un hecho a comunicar. La herramienta debe servir para que la dirección sepa que el 13 de octubre necesita un gestor de apoyo, no para que el software esconda la aritmética.

La recomendación operativa que se deriva es concreta: **reprogramar sesiones o habilitar un gestor de apoyo para tres fechas del trimestre**. Es una acción de gestión, no de software.

---

# 10. Limitaciones y trabajo futuro

## 10.1 Limitaciones conocidas

**El modelo no reprograma sesiones.** Toma las fechas de la hoja `Sesiones` como dadas. Si el 13 de octubre tiene ocho sesiones, el modelo lo reporta pero no propone mover ninguna. Incorporar reprogramación con penalización por desviación de la fecha original sería la extensión natural.

**El costo de movimiento es un parámetro, no una medición.** El valor 6.0 se calibró empíricamente para que el resultado fuera aplicable, no a partir de tiempos observados. Con datos reales de tiempo de reenganche por ticket podría estimarse mejor.

**Los pesos no están validados contra tiempos reales.** La fórmula `W_i` es una construcción razonada, no una regresión sobre horas efectivas. La validación requeriría un registro de tiempo por ticket y fase.

**Cinco tickets abiertos no tienen fecha de inicio** y por tanto no entran al calendario. El modelo los incluye en el balance pero no puede programarlos.

**La base es sintética.** El archivo se autodenomina `Control_Prueba` y los nombres son genéricos (`Curso 1`, `Gestor 1`). Las conclusiones sobre proporciones son válidas; las conclusiones sobre valores absolutos de horas no.

## 10.2 Extensiones sugeridas

1. **Reprogramación asistida.** Permitir al modelo proponer fechas alternativas para sesiones en días saturados, con penalización por desviación y respeto al calendario del docente.
2. **Aprendizaje de pesos.** Registrar tiempo real por ticket y ajustar α, β, γ por regresión.
3. **Restricciones de disponibilidad del docente.** El modelo actual solo conoce la disponibilidad del gestor, no la del docente.
4. **Notificaciones.** Alertas por correo cuando un ticket entra en rojo.
5. **Histórico de reasignaciones.** Trazabilidad de por qué se movió cada ticket para auditoría.

---

# Anexo A — Bitácora de uso de IA

## A.1 Herramientas utilizadas

| Herramienta | Versión | Uso |
| :--- | :--- | :--- |
| Claude (Claude Code) | Modelo Sonnet 5.5 | Diseño del modelo, implementación, revisión crítica |
| OR-Tools CP-SAT | 9.15.6755 | Solver (documentación consultada) |

La IA se usó en todas las fases: estructuración del modelo matemático, generación del ETL, implementación de los solvers, diseño de la interfaz y redacción del presente informe. El estudiante verificó cada resultado contra los datos y corrigió los errores que se documentan a continuación.

## A.2 Registro cronológico de prompts principales

| # | Prompt (resumen) | Resultado |
| ---: | :--- | :--- |
| 1 | "Lee el .md de instrucciones y el Excel, hazme el plan de trabajo y dime si es posible" | Análisis de 12 hojas, plan de 6 fases, detección temprana de 3 días infeasibles |
| 2 | "Confirmo la fecha de entrega es el martes 10; iniciemos" | Implementación de Fase 0 a 5 |
| 3 | "Hagamos los dos documentos y el guion, súbelo a GitHub y dockerízalo" | Informe, guion, publicación y contenedor |

Los prompts completos con las respuestas están en el historial de la sesión.

## A.3 Análisis crítico: errores de la IA y su corrección

Esta sección es la más importante del anexo, porque documenta el proceso real de validación.

### Iteración 1 — El ETL reportó cero tickets

**Error.** La primera versión del lector asumía que todas las hojas tenían el encabezado en la fila 1. `Registro` lo tiene en la fila 7 y con la columna A vacía.

**Síntoma.** `tickets=0`, sin excepción ni advertencia. El programa "funcionaba" produciendo un dataset vacío.

**Corrección.** Se introdujo `SHEET_CONFIG`, un diccionario que declara por hoja la fila de encabezado y si debe descartarse la primera columna. Se añadieron tests que comparan los conteos conocidos (112 tickets, 361 sesiones, 334 grupos) para que una regresión de este tipo falle de inmediato.

**Lección.** Un ETL que falla en silencio es peor que uno que falla ruidosamente. El test sobre conteos conocidos es la defensa.

### Iteración 2 — El cálculo de días hábiles no coincidía con el Excel

**Error de diagnóstico, no de código.** Al cotejar los días hábiles calculados contra la columna del Excel, ninguna de las 106 filas coincidía. La primera hipótesis de la IA fue que el cálculo propio estaba mal.

**Investigación.** Se probaron tres hipótesis:

| Hipótesis | Coincidencias |
| :--- | ---: |
| `NETWORKDAYS` correcta (con asuetos, sin extremos) | 0 / 106 |
| Misma fecha de corte en ambos lados | 0 / 106 |
| Lunes a viernes, inclusive extremos, sin asuetos | **104 / 106** |

**Hallazgo.** El Excel no usa `NETWORKDAYS`: cuenta días de lunes a viernes incluyendo ambos extremos y sin descontar asuetos. Las dos filas restantes tienen fechas invertidas en origen.

**Corrección.** Se implementaron ambas funciones —`dias_habiles_excel()` para auditar, `dias_habiles_entre()` para el modelo— y se documentó la diferencia. Este hallazgo se convirtió en un punto fuerte del informe (§2.4) en lugar de un defecto.

**Lección.** Cuando dos cálculos difieren, la hipótesis por defecto no debe ser "el mío está mal". Hay que caracterizar la regla del otro.

### Iteración 3 — El solver movía 38 de 44 tickets

**Error.** La función objetivo incluía una penalización por movimiento de `COSTO_MOVIMIENTO = 0.15`, que al convertirse a entero para CP-SAT se redondeaba a **0**. Mover un ticket no costaba nada.

**Síntoma.** El solver lograba una equidad perfecta (ratio 1.000) moviendo el 86 % de la cartera. Técnicamente óptimo, operativamente inaceptable: ningún jefe de departamento reasigna 38 de 44 tickets en curso.

**Corrección.** Tres cambios:
1. `COSTO_MOVIMIENTO = 6.0`, del orden de la carga que se mueve.
2. Factor de urgencia en el costo: mover un ticket urgente cuesta más.
3. Restricción explícita `Σ movimientos ≤ max_movimientos` (6 por defecto).

**Resultado.** Ratio 1.007 con seis movimientos.

**Lección.** Un modelo correcto matemáticamente puede ser inaplicable. Las penalizaciones son restricciones de política, no detalles de implementación, y su magnitud debe ser del orden de las cantidades que gobiernan.

### Iteración 4 — El calendario reportaba cero colisiones sin tenerlas

**Error.** La primera versión del solver de calendario no imponía que una sesión se supervisara **el día en que ocurre**. El solver asignaba cada sesión al día que le resultaba conveniente para evitar colisiones.

**Síntoma.** Cobertura 100 %, cero colisiones, verificación limpia. Un resultado impecable y falso: las sesiones aparecían supervisadas en días en que no había clase.

**Detección.** El verificador independiente comprobó por primera vez la fecha real de cada sesión asignada y reportó 55 violaciones de tipo `fecha_incorrecta`.

**Corrección.** Restricción (6): `y_{s,g,d} = 0` si `d ≠ fecha(s)`. Se mantuvo la comprobación en el verificador.

**Lección y decisión metodológica.** Este fue el error que motivó que el verificador no importara el solver. Si el verificador hubiera reutilizado el modelo, habría confirmado el error. La separación no es un lujo académico: es la única forma de detectar un error conceptual del modelo.

### Iteración 5 — La hoja `Sesiones` perdía seis sesiones

**Error.** El identificador de sesión se construía como `ticket|grupo|número`. Nueve sesiones del archivo están reprogramadas: comparten ticket, grupo y número, pero tienen dos fechas distintas.

**Síntoma.** `sesion_id` no era único (`361` sesiones, `352` únicos). Al construir el diccionario de sesiones en el solver, seis sesiones colapsaban en tres.

**Corrección.** La fecha se incorporó al identificador: `ticket|grupo|número|fecha`. El ETL emite ahora una incidencia `sesion_reprogramada` por cada caso, que aparece en el panel de calidad.

**Lección.** Un identificador derivado de columnas puede colisionar cuando los datos permiten duplicados lógicos. La comprobación de unicidad debe ser un test explícito, no una suposición.

### Iteración 6 — `Path("")` es `Path(".")` y siempre existe

**Error.** Al preparar la configuración para Docker, la resolución del archivo Excel incluía `Path(os.getenv("IO_SOURCE_XLSX", ""))` entre los candidatos. Sin la variable de entorno, `Path("")` se resuelve como el directorio actual, que siempre "existe".

**Síntoma.** `PermissionError: [Errno 13] Permission denied: '.'` al intentar abrir el directorio como libro de Excel.

**Corrección.** Filtrado explícito de nulos con `p is not None and p.is_file()`.

**Lección.** En una cadena de fallback, la comprobación de existencia no basta: hay que comprobar que el tipo de objeto es el esperado.

## A.4 Validaciones que el estudiante realizó

| Validación | Método | Resultado |
| :--- | :--- | :--- |
| Conteos del ETL | Comparación contra el archivo abierto en Excel | 112 tickets, 361 sesiones, 334 grupos — coincide |
| Días hábiles del Excel | Cotejo fila por fila de 106 registros | 104 coinciden con la regla caracterizada |
| Equidad del modelo | Cálculo manual de una carga `W_i` | Coincide con el motor |
| Colisiones del calendario | Conteo manual de sesiones por gestor y día | 24 días con más de una sesión |
| Infactibilidad del 13-oct | Conteo directo de sesiones obligatorias (5) contra gestores (5) | Confirmado |
| Cambio de docente | Recálculo manual de la holgura en días hábiles | Coincide con el simulador |
| Pruebas de la interfaz | Ejecución de las tres pruebas con capturas | Verificado por captura de pantalla |

## A.5 Declaración

La IA generó código, texto y estructura. El estudiante verificó cada cifra contra el archivo fuente, identificó y documentó los seis errores anteriores, y tomó las decisiones de política del modelo —el costo de movimiento, la declaración de días saturados en lugar de forzar factibilidad, y la separación del verificador— que son las que determinan si la herramienta es aplicable.

---

# Anexo B — Diccionario de datos

## B.1 Hoja `Registro` (encabezado en fila 7, datos desde columna B)

| Columna | Tipo | Uso en el modelo |
| :--- | :--- | :--- |
| `Ticket #` | texto | Clave primaria |
| `Estado` | texto | Filtra el universo (Abierto / Resuelto / Cancelado) |
| `Prioridad` | texto | `w4`, criterio de antigüedad |
| `Tipo de evento` | texto | `FactorModalidad`, determina Ruta A/B |
| `Evento Formativo según PFA / Extraordinario` | texto | Etiqueta del curso |
| `Dependencia` | texto | Descriptivo |
| `Fecha de ingreso` | fecha | Cálculo de antigüedad |
| `Fecha de Asignación` | fecha | Ventana total de días hábiles |
| `Asignado a:` | texto | Gestor actual (línea base) |
| `Inicio del Evento` | fecha | Plazo, severidad, calendario |
| `Fin del Evento` | fecha | Descriptivo |
| `Grupos programados` | entero | Componente de carga |
| `Sesiones por grupo` | entero | Componente de carga |
| `Total de sesiones` | entero | Componente dominante de `W_i` |
| `Tipo docente` | texto | `PesoDocente`, `ReqDias` |
| `Observaciones` | texto | Obligatoriedad y Ruta B |

## B.2 Derivaciones

| Dato requerido | Origen | Regla |
| :--- | :--- | :--- |
| Gestor de una sesión | `Registro.Asignado a:` | Cruce por `No. Solicitud` |
| Modalidad de una sesión | `Registro.Tipo de evento` | Cruce por `No. Solicitud` |
| Obligatoriedad | `Registro.Observaciones` | Prefijo `OBLIGATORIO` |
| Ruta B | `Registro.Observaciones` | Contiene `DFV` |
| Días hábiles restantes | `hoy` → `Inicio del Evento` | `dias_habiles_entre()` con asuetos GT |
| Severidad | Días restantes vs. `ReqDias` | Rojo si holgura < 0; ámbar si ≤ 25 % de `ReqDias` |

---

# Anexo C — Evidencia de ejecución

## C.1 Salida de las pruebas

```
$ cd backend && ../.venv/Scripts/python -m pytest tests -q
..................................                                       [100%]
34 passed in 4.58s
```

## C.2 Ejecución en contenedor

```
$ docker build -t io-tickets-optimizacion:latest .
$ docker run -d -p 8090:8000 io-tickets-optimizacion:latest
$ curl http://127.0.0.1:8090/health
{"ok":true,"version":"0.1.0","tickets":112,"sesiones":361,"gestores":5}

$ curl -X POST http://127.0.0.1:8090/optimizar -d '{"max_movimientos":6}'
movs: 6
ratio: 2.03 -> 1.007
colisiones: 0   oblig: 55 / 55
```

## C.3 Capturas

| Archivo | Contenido |
| :--- | :--- |
| `data/results/01-dashboard.png` | Tablero con el gráfico nominal vs. ponderado |
| `data/results/03-recursos.png` | Equipo con cargas y controles |
| `data/results/p1-optimizado.png` | Resultado de la Prueba 1 |
| `data/results/p2-vacaciones.png` | Resultado de la Prueba 2 |
| `data/results/p3-rojo.png` | Simulador, caso en rojo |
| `data/results/p3-verde.png` | Simulador, caso con holgura |
| `data/results/docker-dashboard.png` | Interfaz servida desde el contenedor |

---

*Fin del informe técnico.*
