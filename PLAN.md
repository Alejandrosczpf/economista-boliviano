# Plan de trabajo, sesión por sesión

Cada sesión tiene un objetivo, sus tareas y una condición de **"listo cuando"** que se puede comprobar.
Una sesión se da por cerrada solo si las pruebas pasan y la corrida en GitHub termina en verde.
El orden va de lo que más mejora la confiabilidad a lo que más mejora la lectura.

| # | Sesión | Estado |
|---|---|---|
| 1 | Fuentes que no fallan | ✅ hecha (25-nov-2026) |
| 2 | Un robot que avisa | pendiente |
| 3 | Memoria del índice | pendiente |
| 4 | Dólar paralelo automático | pendiente |
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

## 2. Un robot que avisa

**Por qué:** hoy, si una fuente se cae o un dato manual se vence, nadie se entera salvo que abra `reports/salud.md`.

- Abrir automáticamente un *issue* en GitHub cuando una fuente falla dos días seguidos o una serie que vota se vence. GitHub avisa por correo.
- Avisar con una semana de anticipación cuando una serie manual está por vencerse.
- Actualizar los componentes del workflow (checkout v4→v7, setup-python v5→v7, Pages v3/v4→v5), que GitHub marca como obsoletos. Hay que verificar que el robot pueda seguir haciendo `git push`.
- Agregar una forma simple de correr las pruebas en la PC sin instalar pytest.

**Listo cuando:** al provocar un error a propósito se abre un issue, y la corrida no muestra advertencias de Node.

## 3. Memoria del índice

**Por qué:** el Pulso muestra el índice de hoy, pero no cómo llegó ahí.

- Guardar el índice de cada día con sus señales en `data/indice.csv`.
- Reconstruirlo hacia atrás desde el 29-jun-2026 con los datos que se conocían en cada fecha, sin usar datos del futuro.
- Mostrar un gráfico de la evolución del índice en el Pulso, con las fechas de los cambios de estado.

**Listo cuando:** el Pulso muestra la línea del índice desde el inicio de la flotación, y una prueba comprueba que la reconstrucción no usa datos posteriores a cada fecha.

## 4. Dólar paralelo automático

**Por qué:** es la serie que más se vence. Su límite de frescura es de 10 días y hoy tiene 33, así que la brecha cambiaria no vota.

- Investigar fuentes públicas y legítimas que publiquen el paralelo o el dólar digital con fecha.
- Escribir el recolector, su prueba con una página guardada y su contrato de datos.
- Si ninguna fuente sirve, que lo cargue la IA cada semana (sesión 8).

**Listo cuando:** el paralelo se actualiza solo, al menos cada semana, y la brecha vuelve a votar.

## 5. Más series oficiales automáticas

**Por qué:** las reservas (RIN), la inflación del INE y las proyecciones del BCB se cargan a mano.

- Revisar qué publica el BCB y el INE en formato estable (tablas, Excel, PDF con estructura fija).
- Pasar a recolector automático al menos la RIN y la inflación mensual.

**Listo cuando:** la RIN y la inflación se actualizan sin carga manual, con prueba cada una.

## 6. El motor con datos reales

**Por qué:** los episodios históricos que validan el motor (1985, 2014-2024) son valores aproximados. Desde la sesión 1, el sistema recibe las series oficiales del Banco Mundial y el FMI, que todavía no usa.

- Reemplazar los valores aproximados de `HISTORIA` por las series oficiales, citando la fuente.
- Prueba retrospectiva: calcular el índice año por año desde 1980 y revisar si anticipó cada crisis.
- Revisar los umbrales del régimen flotante con la experiencia de jun-nov 2026 y documentar cada cambio.

**Listo cuando:** las pruebas históricas usan datos oficiales y siguen reconociendo 1985, 2016, 2019, 2023 y 2024.

## 7. El Pulso para el lector

- Mostrar qué cambió desde la semana pasada y por qué se movió el índice.
- Agregar una ficha por indicador: qué mide, por qué importa y su último dato con la fuente enlazada.
- Revisar que se lea bien en el celular y que sea accesible.

**Listo cuando:** una persona sin formación económica puede explicar el estado actual después de leer la página.

## 8. Carga semanal asistida por IA

**Por qué:** algunos datos no tienen API (EMBI, proyecciones de organismos y, quizás, el paralelo).

- Crear una rutina programada que cada semana busque esos datos en boletines y prensa confiable.
- La rutina propone los cambios a `data/manual/entradas.csv`, con fuente y enlace, como *pull request*. Una persona los aprueba antes de que entren.

**Listo cuando:** llega una propuesta semanal revisable y los datos aprobados pasan por la cuarentena como cualquier otro.

## 9. Informe semanal verificado

- Escribir con IA un informe corto cada semana a partir del Pulso.
- Antes de publicarlo, `engine/verificador.py` compara cada cifra con los datos; si alguna no coincide, no se publica.

**Listo cuando:** el informe aparece en el Pulso y una prueba confirma que uno con una cifra inventada queda bloqueado.
