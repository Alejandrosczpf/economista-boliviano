# Plan de trabajo, sesión por sesión

Cada sesión tiene un objetivo, sus tareas y una condición de **"listo cuando"** que se puede comprobar.
Una sesión se da por cerrada solo si las pruebas pasan y la corrida en GitHub termina en verde.
El orden va de lo que más mejora la confiabilidad a lo que más mejora la lectura.

### Fase 1

| # | Sesión | Estado |
|---|---|---|
| 1 | Fuentes que no fallan | ✅ hecha (25-nov-2026) |
| 2 | Un robot que avisa | ✅ hecha (25-nov-2026) |
| 3 | Memoria del índice | ✅ hecha (25-nov-2026) |
| 4 | Dólar paralelo automático | ✅ hecha (25-nov-2026) |
| 5 | Más series oficiales automáticas | ✅ hecha (25-nov-2026) |
| 6 | El motor con datos reales | ✅ hecha (25-nov-2026) |
| 7 | El Pulso para el lector | ✅ hecha (25-nov-2026) |
| 8 | Carga semanal asistida por IA | ✅ hecha (25-nov-2026) |
| 9 | Informe semanal verificado | ✅ hecha (25-nov-2026) |

### Fase 2

La fase 1 dejó el sistema funcionando solo. La fase 2 cierra los huecos que quedaron a la vista y lo hace más útil para quien lo lee. El orden sigue siendo: primero lo que puede romperse o vencerse, después lo que mejora la lectura.

| # | Sesión | Por qué ahora | Estado |
|---|---|---|---|
| 10 | Riesgo país que no se vence | Es el único indicador con fecha de vencimiento cercana y sin fuente estable | ✅ hecha (25-nov-2026) |
| 11 | Vigilar a las rutinas | Una rutina que falla en silencio se confunde con "esta semana no hubo datos" | pendiente |
| 12 | Metodología y archivo públicos | Un índice público necesita explicar cómo se calcula y mostrar lo que dijo antes | pendiente |
| 13 | Compartir y accesibilidad | El Pulso se lee y se comparte desde el celular (WhatsApp); los gráficos no tienen tabla | pendiente |
| 14 | "A un paso de cambiar" | Decir qué indicadores están cerca de cambiar de color, sin predecir | pendiente |
| 15 | Nuevos indicadores con prueba histórica | Comercio exterior, depósitos y bolivianización; solo entran si pasan la prueba desde 1980 | pendiente |
| 16 | Revisión de umbrales del régimen flotante | Programada para **junio de 2027**, al cumplirse 12 meses de flotación | programada |

---

## 10. Riesgo país que no se vence

**Por qué:** el EMBI vence el 2-dic-2026 y la rutina semanal no halló un valor posterior con fecha explícita. JP Morgan no publica el EMBI abiertamente, así que solo llega a través de la prensa, de forma irregular.

- Investigar fuentes **públicas y legítimas**:
  - comunicados periódicos del MEFP o del BCB;
  - resúmenes mensuales de la prensa ("Riesgo país en noviembre", de Bloomberg Línea);
  - el rendimiento de los bonos soberanos de Bolivia publicado por bolsas o por el emisor.
- Si no hay una fuente frecuente, **ajustar el contrato a la realidad**. Si el dato es mensual, la frescura no puede ser de 30 días. Hay que documentar la decisión y cuánto pesa un dato más viejo.
- Agregar la fuente elegida a las instrucciones de la rutina y a los dominios permitidos.

**Listo cuando:** el riesgo país tiene una fuente con frecuencia conocida y su contrato coincide con esa frecuencia, de modo que no queda "vencido" por diseño.

**Hecho:**
- **No existe una fuente pública frecuente del EMBI de Bolivia.** Se revisó:
  - JP Morgan: no lo publica abiertamente.
  - API pública del BCRP (Perú): publica el EMBI de 8 países (Argentina, Brasil, Chile, Colombia, Ecuador, México, Perú y Venezuela), **no el de Bolivia**.
  - Bonos soberanos 2028 y 2030: no tienen cotización pública con permiso de uso, solo en servicios pagos. Además, el BCB los está canjeando por deuda local.
  - MEFP: anuncia el dato cuando baja, por medio de la prensa.
- **Frecuencia real:** la prensa trae cifras **con fecha explícita** cada 2 o 3 meses (18-feb, 22-may, 13-ago y 2-nov de 2026).
- **Decisión:** frescura de **90 días** (antes 30) y frecuencia "irregular". La justificación quedó en `nota_frescura` del contrato. Con 30 días el indicador estaba vencido por diseño. Pesa 1 de 10,5, sus umbrales son anchos (400 y 800) y en una crisis la prensa lo publica más seguido.
- **Dos valores recuperados y verificados**, con fecha explícita: 605 pb el 22-may (Bloomberg Línea) y 407 pb el 13-ago (La Patria, EMBI de JP Morgan). Los demás valores que aparecieron ("este lunes", "en febrero pasado", "en el último año") no se cargaron, por no tener fecha exacta.
- La rutina de carga tiene una lista de fuentes ampliada. La Razón quedó descartada por su muro de pago.
- **Resultado:** el EMBI vota los 150 días de la reconstrucción, y desaparece el aviso de "por vencer".
- 1 prueba nueva (96 en total).

## 11. Vigilar a las rutinas

**Por qué:** si una rutina en la nube no corre (cuenta, red, GitHub), hoy nadie se entera. "No hubo *pull request*" puede significar "no había datos" o "la rutina falló".

- Una **bitácora**: cada lunes, las dos rutinas dejan su resumen como comentario en un issue fijo ("Bitácora de rutinas"), aunque no propongan nada.
- El robot de los martes revisa la bitácora. Si falta el comentario del lunes de alguna rutina, abre un aviso.
- Avisar también si un *pull request* de datos o de informe lleva más de 7 días sin revisarse.

**Listo cuando:** si se desactiva una rutina a propósito, el martes llega un aviso.

## 12. Metodología y archivo públicos

**Por qué:** para que el Pulso sea creíble fuera de este repositorio, quien lo lee debe poder ver cómo se calcula y qué dijo antes.

- Página **"Cómo se calcula"**: método KLR, los 9 indicadores con sus umbrales y pesos, la regla de mayoría, la histéresis, el rezago de publicación, las fuentes con sus licencias y los límites conocidos (por ejemplo, el déficit del FMI frente al del MEFP). Se genera con los contratos y el motor, para que no envejezca.
- **Archivo de informes**: todos los informes semanales, cada uno con su sello de verificación.
- **"Qué sabía el sistema el día X"**: elegir una fecha y ver el índice y los datos de ese día (salen de `data/indice.csv` y del historial de git).

**Listo cuando:** desde el Pulso se llega a la metodología y al archivo, y una prueba confirma que la página de metodología refleja los umbrales reales del motor.

## 13. Compartir y accesibilidad

- **Vista previa al compartir** (Open Graph): título, estado e índice del día al pegar el enlace en WhatsApp o redes. La imagen se genera cada día.
- **Fuente RSS** de los informes semanales, para quien quiera recibirlos.
- **Tablas de datos** para los cuatro gráficos de "Cómo se movieron", y tooltips accesibles con teclado.
- Revisar el contraste y los textos alternativos con una herramienta automática.

**Listo cuando:** al compartir el enlace se ve el estado del día, y la página pasa una revisión automática de accesibilidad sin errores graves.

## 14. "A un paso de cambiar"

**Por qué:** saber qué indicadores están **cerca de su umbral** ayuda a anticipar movimientos del índice sin hacer predicciones.

- Calcular para cada indicador la distancia a su próximo umbral, por ejemplo "la inflación a 12 meses está a 4,9 puntos del rojo".
- Mostrar en el Pulso cuáles cambiarían de color con un movimiento chico, y cuánto cambiaría el índice si lo hicieran.
- Agregar esas distancias a la ficha de hechos, para que el informe semanal pueda citarlas verificadas.

**Listo cuando:** el Pulso muestra las distancias a los umbrales, y una prueba confirma que coinciden con los umbrales del motor.

## 15. Nuevos indicadores con prueba histórica

**Candidatos con fuente oficial automatizable:** exportaciones e importaciones mensuales (INE), depósitos y bolivianización (BCB/ASFI) y crédito al sector privado.

- Cada candidato entra **solo si mejora la prueba retrospectiva desde 1980**: debe anticipar mejor las crisis sin encender falsas alarmas en los años buenos.
- Si no la mejora, se muestra como contexto y no vota en el índice.

**Listo cuando:** cada candidato tiene su resultado documentado (entra o no entra, y por qué) y las pruebas históricas siguen pasando.

## 16. Revisión de umbrales del régimen flotante (jun-2027)

- Con 12 meses de flotación, revisar si los umbrales de depreciación, brecha y reservas siguen siendo razonables, usando la memoria del índice (`data/indice.csv`).
- Cada cambio se documenta y debe seguir pasando las pruebas históricas.

---

## 1. Fuentes que no fallan ✅

**Por qué:** en la primera corrida, el Banco Mundial y el FMI respondieron "403 Forbidden" y 7 series quedaron sin datos.

**Hallazgos:**
- **Banco Mundial:** la tilde de "económico" en la identificación del programa (User-Agent) hacía que la API rechazara la conexión. Sin la tilde responde bien.
- **FMI:** su API vieja (DataMapper) bloquea a los servidores de GitHub, aunque desde una PC responde. La API oficial nueva (`api.imf.org`, SDMX 3.0) responde y además trae solo Bolivia, unos 5 KB en vez de 120 KB.

**Hecho:**
- La identificación del programa usa solo caracteres ASCII, y una prueba lo exige.
- El FMI se lee de la API nueva y, si falla, de la vieja.
- Si un indicador falla, los demás de esa fuente se conservan (`FallaParcial`).
- Los errores 4xx ya no se reintentan; antes cada uno costaba unos 18 segundos de espera.
- Hay 3 pruebas nuevas, entre ellas una con una respuesta real del FMI guardada.

**Listo cuando:** la corrida en GitHub termina con 0 fuentes con error.

## 2. Un robot que avisa ✅

**Por qué:** hasta ahora, si una fuente se caía o un dato manual se vencía, nadie se enteraba salvo que abriera `reports/salud.md`.

**Hecho:**
- `pipeline/avisos.py` abre un *issue* con la etiqueta `robot` en cuatro casos:
  - una fuente falla 2 corridas seguidas;
  - una serie que alimenta el índice se vence;
  - una serie manual vence en 7 días o menos;
  - un indicador no vota por otra razón.

  Si el aviso sigue al día siguiente, el issue se actualiza sin mandar otro correo. Cuando el problema se resuelve, el robot lo cierra.
- Si la corrida entera falla, se abre el issue "La corrida del robot falló". Las fallas siguientes se comentan en ese mismo issue.
- La cuenta de fallas de cada fuente se guarda en `data/estado_fuentes.json`.
- El workflow usa los componentes con Node 24 (checkout v7, setup-python v7, Pages v5) y hace `git pull --rebase --autostash` antes del push.
- Al lanzar el workflow a mano se puede marcar *Simular una falla* para probar el aviso.
- `python -m tests` corre las pruebas sin instalar nada. Hay 14 pruebas nuevas, 37 en total.

**Comprobado en GitHub:**
- La primera corrida abrió dos avisos reales: el dólar paralelo vencido (#3) y el EMBI por vencer (#2).
- La falla simulada comentó en el issue #1 sin duplicarlo.
- La corrida repetida actualizó los avisos sin abrir issues nuevos.
- Ya no hay advertencias de Node.

## 3. Memoria del índice ✅

**Por qué:** el Pulso mostraba el índice de hoy, pero no cómo llegó ahí.

**Hecho:**
- `engine/memoria.py` guarda en `data/indice.csv` una fila por día desde el 29-jun-2026, con el índice, el estado, cuántos indicadores votaron y la señal de cada uno.
  - Las filas **en vivo** son lo que el robot calculó ese día y quedan congeladas.
  - Las filas **reconstruidas** se recalculan en cada corrida, así un dato histórico cargado después mejora la reconstrucción.
- Rezago de publicación: cada serie tiene `rezago_dias` en `config/series.json`. Al reconstruir el pasado, un dato cuenta recién desde su fecha más el rezago. Por ejemplo, la inflación de octubre cuenta desde el 7-nov.
- Regla de mayoría: un día en que vota menos de la mitad de los indicadores no se dibuja ni cuenta como cambio de estado. Con pocos votos, el índice depende más de cuáles votaron que de la economía; el 29-jun solo votaban el déficit y el PIB, y daba 100.
- El Pulso muestra la línea del índice, una franja con los indicadores que votaron cada día (mismo eje de fechas), los cambios de estado y la tabla día por día.
- Hay 7 pruebas nuevas, entre ellas una que exige que agregar datos posteriores a un día no cambie el índice reconstruido de ese día.

**Error encontrado y corregido:** el recolector del BCB guardaba el tipo de cambio con la **fecha de corte**, que es el día anterior, en vez de la fecha de vigencia. La página escribe "VIGENCIA: MIÉRCOLES 25…" sin el "DEL" que esperaba el programa, y este tomaba en silencio la fecha de corte. Ahora acepta los dos formatos, y si no encuentra la vigencia, falla y avisa en vez de adivinar. Se borró el dato mal fechado del 24-nov.

**Lo que la reconstrucción mostró:** entre julio y octubre el índice aparece casi siempre en "alerta". Esto se debe en buena parte a que los indicadores que suelen estar en verde (depreciación, brecha) no tienen datos: el dólar oficial se cargó a mano con saltos de semanas entre un dato y otro. La solución es de datos (sesiones 4 y 5), no de fórmula.

## 4. Dólar paralelo automático ✅

**Por qué:** era la serie que más se vencía. Tenía 33 días con un límite de 10, así que la brecha cambiaria no votaba.

**Fuente elegida:** la [API pública de paralelo.bo](https://paralelo.bo/api).
- Sin clave ni registro, con datos bajo **CC-BY 4.0**.
- Metodología publicada: la mediana de las mejores ofertas de USDT/BOB en Binance, Bybit y Bitget, como promedio entre compra y venta.
- Serie diaria continua desde agosto de 2024, sin huecos, marcada `illustrative: false`, es decir, datos observados.
- Coincide con lo que se había cargado a mano desde la prensa: 11,42 frente a 11,43 el 15-ago, y 11,99 frente a 11,93 el 23-oct.
- **En contra:** lo opera un equipo anónimo y el sitio tiene enlaces de referido. Por eso el recolector exige el formato esperado y rechaza una serie marcada como ilustrativa, y el contrato de datos sigue filtrando saltos imposibles.
- **Descartada:** `mauforonda/dolares` (GitHub). Está activa, pero no declara licencia, así que no corresponde volver a publicar sus datos.

**Hecho:**
- Recolector `paralelo`. Solo guarda días completos: el día en curso tiene un valor parcial y se guarda completo al día siguiente.
- Contrato: frescura de 5 días (antes 10, cuando se cargaba a mano) y rezago de publicación de 1 día.
- Se quitaron los 3 datos manuales del paralelo, que quedan en el historial de git, para que la serie tenga una sola fuente.
- Regla general: si dos fuentes traen la misma serie y fecha, gana la automática (`store.deduplicar`). Sin ella, los dos datos se pisaban en cada corrida.
- La atribución CC-BY aparece en el pie del Pulso, en el gráfico del dólar y en cada dato.
- Las series diarias se dibujan sin un punto por día.
- Hay 6 pruebas nuevas, 49 en total, con una respuesta real de la API guardada.

**Resultado:** entraron 841 días del paralelo sin ninguno en cuarentena. Por primera vez votan los 9 indicadores. La brecha es de 1,4 % (verde) y el índice pasó de 55,0 a 47,8, en vigilancia.

## 5. Más series oficiales automáticas ✅

**Por qué:** el dólar oficial, las reservas y la inflación se cargaban a mano desde la prensa.

**Hecho:**
- **Dólar oficial diario** (BCB, [tabla por períodos](https://www.bcb.gob.bo/librerias/indicadores/dolar/periodos.php)): trae cada día desde el 27-jun-2026, fines de semana incluidos.
  - Se contrasta con la página de la cotización del día. Si las dos traen el mismo día con valores distintos, el robot avisa.
  - De los 20 datos cargados a mano desde la prensa, 19 coincidían exactamente. El del 1-ago decía 12,15 y el BCB registra 12,13.
- **Inflación** (INE): se leen los comunicados mensuales del IPC a través de la API pública del sitio del INE, desde los datos de abril de 2026.
  - El signo mensual sale de las palabras del título ("disminuyó", "negativa").
  - Ese signo se comprueba con la inflación acumulada del mes anterior. Si no hay signo ni forma de comprobarlo, el dato no se guarda.
  - Se llenaron los meses que faltaban: abril, mayo y julio (−2,79 %).
- **Reservas** (BCB, Excel oficial "RIN por componentes", mensual desde 2002): ahora hay tres series separadas, **RIN neta**, **reservas brutas** y **divisas**.
- **Aprobación de datos en cuarentena:** cuando una persona revisa un dato en cuarentena y confirma que es real, lo anota en `data/manual/aprobados.csv` con el motivo y un enlace. Ese dato se salta el control de salto, pero no el de rango posible, y la aprobación vale solo para ese valor exacto. Un dato en cuarentena ahora abre un aviso (issue) que explica cómo aprobarlo. El registro de cuarentena ya no repite filas.
- Hay 17 pruebas nuevas, 66 en total, con archivos reales del BCB y del INE.

**Hallazgos:**
1. **La serie manual de reservas mezclaba dos conceptos.** Hasta 2024 tenía la RIN **neta**; desde 2025, las reservas **brutas**, que son la cifra que citan los informes y la prensa. En 2025-2026 la diferencia llegó a unos 750 millones de dólares en pasivos de operaciones con oro. Además, la liquidez (divisas sobre total) solo tiene sentido sobre las brutas, y ahora se calcula así.
2. **Septiembre de 2026 fue un episodio real de volatilidad del tipo de cambio oficial**: de 12,64 (9-sep) bajó a 9,83 (17-sep) y rebotó a 12,06 (23-sep), poco antes de que el BCB cambiara la forma de calcularlo. La cuarentena frenó dos saltos diarios mayores al 8 %. Se confirmaron con la prensa (Bloomberg Línea) y se aprobaron.
3. **Con datos completos, la historia del índice cambió.** Antes parecía en "alerta" casi todo el tiempo desde julio. Ahora muestra alerta en julio, calma a fines de agosto y vigilancia desde septiembre. Votan la mayoría de los indicadores los 150 días, frente a 116 antes.
4. **El índice oscila alrededor de los umbrales.** Hubo 7 cambios de estado en dos meses, como alerta↔vigilancia o calma↔vigilancia de un día para otro. Queda para la sesión 6.

**Siguen a mano:** el EMBI, las proyecciones del PIB, el déficit fiscal y la base monetaria. Pasan a la sesión 8 (carga semanal asistida).

## 6. El motor con datos reales ✅

**Hecho:**
- **Prueba retrospectiva con datos oficiales** (`engine/historia.py` y `reports/historia.md`, que se regenera en cada corrida). Calcula el índice año por año desde 1980 con:
  - inflación a fin de año, balance fiscal y crecimiento del FMI WEO;
  - RIN neta del BCB desde 2003 (antes, reservas totales del Banco Mundial);
  - liquidez del BCB desde 2002;
  - brecha de paralelo.bo desde 2024. Para 1985 se usa una aproximación documentada.

  Cada valor cita su fuente. Se eliminaron los valores aproximados que el motor tenía escritos a mano (`HISTORIA`).
- **Resultado:** alerta desde **1981** (la hiperinflación, con 4 años de anticipación); calma en 1987-2001 y en todo el auge 2005-2014; vigilancia en 2002, 2016 y 2019; alerta en 2020 (pandemia); **vigilancia con 57,7 en 2022, un año antes de la escasez de dólares**; alerta en 2023-2025.
- **Las pruebas de regresión usan los datos oficiales del repositorio.** Siguen reconociendo 1985, 2016, 2019, 2023 y 2024, y se agregaron 1981-1985, el auge 2005-2014 y la anticipación de 2022. Si una revisión de datos del FMI o el BCB las rompe, la corrida falla y avisa.
- **Histéresis asimétrica:** subir de estado es inmediato; bajar exige quedar 3 puntos por debajo del umbral. La reconstrucción de 2026 pasó de 7 cambios de estado a 3, todos con sentido.
- **Mayoría en el índice diario:** si vota menos de la mitad de los indicadores, la página lo advierte. El índice se sigue calculando, porque las pruebas históricas anteriores a 2002 tienen solo 4 de 8.
- **Cambio de metodología del BCB (RD 142/2026)**: desde el 26-sep-2026 el dólar oficial es una mediana ponderada en vez de un promedio. Quedó registrado en el contrato del TCO, y la nota de la depreciación lo menciona si su ventana lo cruza.
- 7 pruebas nuevas (73 en total).

**Decisiones:**
- **Señales de depreciación de sep-oct 2026: se mantienen.** El cambio de metodología solo bajó el valor un 1,4 % (de 12,22 a 12,05). Los grandes vaivenes (12,64 → 9,83 → 12,26) fueron anteriores y se calcularon con el método antiguo, así que son movimientos del mercado.
- **Umbrales del régimen flotante: no se cambian todavía.** Cinco meses de flotación no alcanzan para recalibrar. Lo que se vio es coherente: la depreciación > 5 % en 30 días se encendió en el episodio real de septiembre y la brecha cercana a 0 marca confianza. Se revisarán al cumplir 12 meses (jun-2027).
- **Déficit fiscal:** la prueba histórica usa el del gobierno general (FMI), que es algo menor que el del sector público no financiero que publica el MEFP. Por ejemplo, para 2016 el motor usaba 7,2 % y el FMI da 6,0 %. Se eligió la serie oficial consistente aunque sea más benigna.

## 7. El Pulso para el lector ✅

**Hecho:**
- **"En pocas palabras"**, al inicio de la página: tres o cuatro frases en lenguaje simple, armadas cada día con los datos del día. Dicen el estado y qué significa, lo que más preocupa, lo que ayuda, cómo se movió la semana y qué no votó. Cada indicador tiene su frase, por ejemplo "el déficit del Estado (11,0 % del PIB)".
- **"Qué cambió esta semana"**: compara con hace 7 días el índice, el estado y los indicadores que cambiaron de color.
- **Gráficos al ancho real de la pantalla.** Se dibujaban a 540 o 1.080 px y se achicaban; en un celular las letras del gráfico del índice medían 4 px, y ahora son de tamaño normal. Se redibujan si cambia el ancho y responden al dedo, no solo al mouse.
- **Notas de los gráficos generadas con los datos** (`notas_graficos`), en lugar del texto fijo que envejecía. Por ejemplo, la nota de la inflación decía que había repuntado "en octubre".
- **"¿Habría avisado? El índice desde 1980"**: barras por año con el color del estado, los umbrales, un punto en los años de crisis conocida, barras claras donde votó menos de la mitad de los indicadores, y una tabla año por año.
- En el celular, las barras de "Qué empuja el índice" usan el ancho disponible, y las tablas tienen desplazamiento horizontal propio.
- 4 pruebas nuevas (77 en total).

**Corrección:** el "desborde a la derecha en el celular" anotado en la sesión 3 **no existía**. Edge en modo headless no achica la ventana por debajo de unos 500 px, así que la captura se dibujaba a ~500 px y se recortaba a 390. Medido en un marco de 360 px, la página no se desborda. El problema real era el tamaño de las letras de los gráficos, que sí se corrigió.

**Pendiente menor:** los gráficos de dólar, reservas, inflación y EMBI no tienen tabla de datos para quien no puede usar el mouse ni el tacto; sus notas dicen los valores clave.

## 8. Carga semanal asistida por IA ✅

**Por qué:** algunos datos no tienen API: el EMBI, las proyecciones del PIB, el déficit fiscal y la base monetaria.

**Hecho:**
- **Rutina semanal de Claude en la nube** ("Economista Boliviano: carga semanal de datos manuales"), los **lunes a las 08:00 de Bolivia**, con el modelo `claude-sonnet-5-5`, sin conectores. Se administra en https://claude.ai/code/routines/trig_01Q34rbt31RKXUyuFrLVxRiM.
  - Sigue `agentes/carga_semanal.md`: busca en la web las series que vencen en 14 días o menos, o que tienen publicación nueva, y las agrega con fuente y enlace.
  - Abre un *pull request* "Carga semanal AAAA-MM-DD" con la cita textual de cada dato. **Nunca hace merge.** Si no encuentra nada con fuente clara, no abre nada.
- **Revisión automática de cada propuesta** (`.github/workflows/revisar-propuesta.yml` y `pipeline/propuesta.py`). En cada *pull request* que toca `data/manual/`, GitHub corre las pruebas y revisa fila por fila:
  - fuente y enlace obligatorios;
  - fecha no futura;
  - que la serie no sea una de las automáticas;
  - el rango y el salto creíble de la serie.

  Comenta el resultado en el *pull request* y falla si alguna fila no pasa. Una persona abre los enlaces y aprueba.
- `python -m pipeline.propuesta pendientes` lista las series manuales de la más urgente a la menos.
- La rutina necesita la **app de Claude en GitHub** instalada en el repositorio para poder hacer push y abrir el *pull request*. Se instaló el 25-nov-2026.
- **Primera corrida de prueba (25-nov-2026):** descargó el repositorio, corrió `pendientes` y buscó en la web. Terminó bien y **no abrió ningún *pull request***, lo cual fue correcto.
  - Para el EMBI solo halló una cifra posterior (595 pb hacia el 20-nov, en MarketData), pero apareció solo en el resumen del buscador y no pudo abrir la página para verificarla.
  - El Programa Monetario de noviembre todavía no estaba publicado.
  - Todavía no se probó el push ni la creación del *pull request*, porque no hubo dato que proponer.
- **Red del entorno:** la nube de Claude solo abre los dominios permitidos en el entorno "Default" (claude.ai/code → entornos → acceso a la red: "Limitado", un dominio por línea, cada uno con y sin `*.`).
  - El 25-nov se agregaron 14 fuentes.
  - En la segunda prueba aparecieron fuentes útiles fuera de la lista: `larazon.bo` (el riesgo país del 22-nov) y `economiayfinanzas.gob.bo`, que es el dominio real del MEFP; `economia.gob.bo` era un error.
  - Si una fuente falla, la rutina lo dice en su resumen.
- 8 pruebas nuevas (85 en total).

## 9. Informe semanal verificado ✅

**El problema del verificador de la fase 1:** comparaba cada número contra **todo el historial** (miles de valores de 20 series desde 1960), así que casi cualquier cifra inventada coincidía con algún valor viejo. Por ejemplo, "la inflación es 5,7 %" pasaba porque 5,7 fue la de septiembre. Además, no miraba de qué hablaba cada cifra.

**Hecho:**
- **Ficha de hechos del día** (`engine/hechos.py` y `data/hechos/AAAA-MM-DD.json`): la escribe el robot en cada corrida. Son unas 25 cifras citables (índice, cada indicador, dólar oficial y paralelo, reservas, proyecciones, el cambio de la semana), cada una con las palabras clave de su tema.
- **Verificador por afirmación** (`engine/verificador.py`): cada número del informe debe cumplir dos condiciones.
  1. Coincidir con un hecho de la ficha **de esa fecha**, con el redondeo con que está escrito: "47,8" exige 47,75-47,85.
  2. Estar en una oración que **nombre su tema**: "la inflación llegó a 59,6 %" se bloquea porque 59,6 es el cambio de las reservas.

  Las fechas y los años no cuentan como cifras. Los períodos ("12 meses", "30 días") solo valen junto a su unidad.
- **Rutina "Economista Boliviano: informe semanal verificado"** de Claude en la nube, los **lunes a las 10:00 de Bolivia**, después del robot de las 09:17. Es `trig_012hN8ub6FmPFmvfBtuc5797`. **No tiene acceso a la web**: solo lee la ficha. Sigue `agentes/informe_semanal.md`: 200 a 350 palabras, para cualquier persona, sin opiniones, recomendaciones ni predicciones. Corre el verificador hasta que todo pase y abre un *pull request* "Informe semanal AAAA-MM-DD".
- **Revisión del *pull request***: GitHub verifica de nuevo las cifras del informe y **rechaza cualquier cambio a `data/hechos/`**, porque un informe no puede traer su propia ficha. Comenta el resultado.
- **Publicación:** al aprobarlo, el Pulso se publica enseguida. La página muestra el informe más reciente (de hasta 14 días) **solo si todas sus cifras pasan** contra la ficha de su fecha, con el sello "las N cifras fueron verificadas". El markdown se escapa, así que no puede inyectar HTML.
- 9 pruebas nuevas (94 en total). Una exige que un informe con una sola cifra inventada quede bloqueado entero.
