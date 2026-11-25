# Plan de trabajo, sesión por sesión

Cada sesión tiene un objetivo, sus tareas y una condición de **"listo cuando"** que se puede comprobar.
Una sesión se da por cerrada solo si las pruebas pasan y la corrida en GitHub termina en verde.
El orden va de lo que más mejora la confiabilidad a lo que más mejora la lectura.

| # | Sesión | Estado |
|---|---|---|
| 1 | Fuentes que no fallan | ✅ hecha (25-nov-2026) |
| 2 | Un robot que avisa | ✅ hecha (25-nov-2026) |
| 3 | Memoria del índice | ✅ hecha (25-nov-2026) |
| 4 | Dólar paralelo automático | ✅ hecha (25-nov-2026) |
| 5 | Más series oficiales automáticas | pendiente |
| 6 | El motor con datos reales | pendiente |
| 7 | El Pulso para el lector | pendiente |
| 8 | Carga semanal asistida por IA | pendiente |
| 9 | Informe semanal verificado | pendiente |

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

## 5. Más series oficiales automáticas

**Por qué:** las reservas (RIN), la inflación del INE y las proyecciones del BCB se cargan a mano.

- Revisar qué publica el BCB y el INE en formato estable (tablas, Excel, PDF con estructura fija).
- Pasar a recolector automático al menos la RIN y la inflación mensual.
- Cargar la **historia diaria del dólar oficial** desde el 29-jun-2026, con las tablas del BCB. Es lo que más mejora la reconstrucción del índice (sesión 3), porque la depreciación a 30 días vuelve a votar todos los días.

**Listo cuando:** la RIN y la inflación se actualizan sin carga manual, con prueba cada una.

## 6. El motor con datos reales

**Por qué:** los episodios históricos que validan el motor (1985, 2014-2024) son valores aproximados. Desde la sesión 1, el sistema recibe las series oficiales del Banco Mundial y el FMI, que todavía no usa.

- Reemplazar los valores aproximados de `HISTORIA` por las series oficiales, citando la fuente.
- Prueba retrospectiva: calcular el índice año por año desde 1980 y revisar si anticipó cada crisis.
- Revisar los umbrales del régimen flotante con la experiencia de jun-nov 2026 y documentar cada cambio.
- Decidir si el índice del día debe exigir un mínimo de indicadores votando, como ya lo exige el gráfico (regla de mayoría de la sesión 3).

**Listo cuando:** las pruebas históricas usan datos oficiales y siguen reconociendo 1985, 2016, 2019, 2023 y 2024.

## 7. El Pulso para el lector

- Mostrar qué cambió desde la semana pasada y por qué se movió el índice.
- Agregar una ficha por indicador: qué mide, por qué importa y su último dato con la fuente enlazada.
- Revisar que se lea bien en el celular y que sea accesible. Ya se sabe que en un celular la página se desborda a la derecha (se cortan las tarjetas de arriba) y que el texto del gráfico del índice queda muy chico.

**Listo cuando:** una persona sin formación económica puede explicar el estado actual después de leer la página.

## 8. Carga semanal asistida por IA

**Por qué:** algunos datos no tienen API, como el EMBI y las proyecciones de los organismos.

- Crear una rutina programada que cada semana busque esos datos en boletines y prensa confiable.
- La rutina propone los cambios a `data/manual/entradas.csv`, con fuente y enlace, como *pull request*. Una persona los aprueba antes de que entren.

**Listo cuando:** llega una propuesta semanal revisable y los datos aprobados pasan por la cuarentena como cualquier otro.

## 9. Informe semanal verificado

- Escribir con IA un informe corto cada semana a partir del Pulso.
- Antes de publicarlo, `engine/verificador.py` compara cada cifra con los datos; si alguna no coincide, no se publica.

**Listo cuando:** el informe aparece en el Pulso y una prueba confirma que uno con una cifra inventada queda bloqueado.
