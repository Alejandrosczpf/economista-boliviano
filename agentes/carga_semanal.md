# Carga semanal de datos manuales (instrucciones para la IA)

Tu tarea es **proponer** los datos que no tienen recolector automático. Los propones en un *pull request* y una persona los aprueba. Nunca agregas nada directamente a `main`.

## Regla de oro

**Ningún número sin una fuente que lo diga textualmente.** No calcules, no estimes, no interpoles y no "redondees desde un gráfico". Si la fuente no dice el valor y la fecha con claridad, ese dato no se carga. Una semana sin propuesta es un resultado válido.

## Pasos

1. Ponte al día: `git pull`. Después corre `python -m pipeline.propuesta pendientes`, que lista las series manuales de la más urgente a la menos.
2. Por cada serie que **vence en 14 días o menos**, o que tiene una publicación nueva esperable (ver el calendario abajo), busca el dato más reciente en las fuentes de la tabla.
3. Por cada dato encontrado, agrega una fila al final de `data/manual/entradas.csv`:
   `serie,fecha,valor,fuente,url,nota`
   - `fecha`: la fecha **a la que se refiere el valor**. No es la fecha en que lo encontraste. Para cada serie, ver la tabla.
   - `valor`: con punto decimal (`494`, `-3.39`), sin unidades.
   - `fuente`: quién produce el dato y por dónde llegó, por ejemplo `JP Morgan vía Bloomberg Línea`.
   - `url`: el enlace exacto donde se lee el valor.
   - `nota`: opcional y breve, por ejemplo `informe de enero`.
4. Trabaja en una rama `carga/AAAA-MM-DD`. Corre `python -m tests` y `python -m pipeline.propuesta revisar <copia de entradas.csv de main>`. Todo debe pasar.
5. Abre el *pull request* con el título `Carga semanal AAAA-MM-DD`. En el cuerpo, por cada fila, pon la **cita textual** de la fuente donde aparece el número y su enlace. Así quien revisa compara sin buscar.
6. **No hagas merge.** No toques `data/manual/aprobados.csv`, el código ni las series que llegan solas (el workflow las rechaza).
7. **Bitácora, siempre, aunque no hayas propuesto nada:** comenta en el issue #8 "Bitácora de las rutinas" con tus herramientas de GitHub (por ejemplo `mcp__github__add_issue_comment`). La **primera línea** debe ser exactamente `<!-- bitacora: carga AAAA-MM-DD -->`, con la fecha de hoy. Después va tu resumen: series revisadas, qué encontraste, el enlace al *pull request* si lo abriste, y los dominios que no pudiste abrir. Si falta este comentario, el robot avisa el martes que la rutina falló.

## Series y fuentes

| Serie | Qué es | Fecha que va en la fila | Fuentes, en orden de preferencia | Cuándo hay dato nuevo |
|---|---|---|---|---|
| `embi` | Riesgo país de Bolivia (EMBI de JP Morgan), en puntos básicos | El día de la cotización ("al corte del 13 de agosto"). **No** uses la fecha de la nota si el valor es de otro día | JP Morgan citado por Bloomberg Línea (notas sobre Bolivia y resúmenes regionales), La Patria, El Deber, eju.tv (incluidos los análisis de Fernando Romero), Infobae o Reuters; también los comunicados del MEFP (economiayfinanzas.gob.bo). La Razón tiene muro de pago: no sirve. Si dos fuentes difieren, toma la más reciente con fecha explícita. "Menos de 500 puntos", "este lunes" o "en febrero" no bastan: hacen falta el número exacto y la fecha exacta | Irregular, cada 2 o 3 meses con fecha explícita. Por eso su frescura es de 90 días (ver `nota_frescura` en `config/series.json`) |
| `pib_proy_fmi` | Proyección de crecimiento del PIB **del año en curso**, FMI | Fecha de publicación del informe | FMI, Perspectivas de la Economía Mundial (WEO) o comunicado de un Artículo IV | Abril y octubre |
| `pib_proy_bm` | Lo mismo, Banco Mundial | Fecha de publicación | Banco Mundial: Perspectivas Económicas Mundiales (enero y junio) o informe semestral de América Latina (abril y octubre) | Enero, abril, junio y octubre |
| `pib_proy_bcb` | Lo mismo, BCB | Fecha de publicación | BCB: Informe de Política Monetaria o presentaciones oficiales del presidente del BCB | Enero y julio (a veces más) |
| `deficit_fiscal` | Déficit del sector público no financiero, % del PIB (positivo = déficit) | 31 de diciembre del año que mide | MEFP (Ministerio de Economía y Finanzas Públicas, economiayfinanzas.gob.bo); si no, el FMI (Artículo IV) | Una vez al año (primer trimestre) |
| `base_monetaria_var_acum` | Variación acumulada de la base monetaria en el año, en millones de Bs | Último día del mes de corte | BCB, Programa Monetario mensual (PDF en bcb.gob.bo/webdocs/programamonetario) | Cada mes |

## Si una página no abre

La nube solo deja abrir los dominios permitidos del entorno. Si una fuente útil falla con "ENOTFOUND", no la uses. En el resumen final, nombra el dominio para que la persona lo agregue a la lista de permitidos.

## Cuidados que ya costaron errores en este proyecto

- **Reservas brutas y netas no son lo mismo.** La serie de reservas se mezcló así una vez. Esas series ya llegan solas, pero el cuidado vale para cualquier cifra: comprueba que sea **el mismo concepto** que el dato anterior de la serie.
- **La fecha de corte no es la fecha de vigencia.** Usa la fecha a la que se refiere el valor, como dice la tabla.
- **Cada proyección pertenece a un informe.** El Banco Mundial proyectó −1,1 % para 2026 en enero, −3,2 % en abril y junio, y −2,8 % en octubre. Se llegó a cargar el −1,1 de enero con fecha de junio. Identifica de qué informe es la cifra y usa su fecha. Si solo tienes la fecha de la nota de prensa, úsala y escribe en `nota` "fecha de la nota".
- **Revisa el signo.** Una proyección de −3,0 % no es 3,0 %, y un déficit se carga como número positivo.
- Si un valor parece un salto enorme frente al anterior, vuelve a verificarlo. Si es real, explícalo en el *pull request*: la revisión automática lo marcará y una persona decidirá si lo aprueba.
