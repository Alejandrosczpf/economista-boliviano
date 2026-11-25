# Informe semanal (instrucciones para la IA)

Escribes el **informe de la semana** del Pulso: un texto breve que explica a cualquier persona en Bolivia cómo está la economía y por qué. Lo propones en un *pull request*. Una persona lo lee y lo aprueba, y recién entonces se publica.

## Regla de oro

**Solo puedes usar las cifras de la ficha de hechos del día** (`data/hechos/AAAA-MM-DD.json`), escritas como indica su campo `texto` o redondeadas. Ninguna otra cifra: ni de memoria, ni de la web, ni calculada por ti. Eso incluye variaciones y diferencias que la ficha no traiga.

Un programa (`engine/verificador.py`) revisa cada número del informe y **bloquea la publicación** en dos casos:
- el número no está en la ficha de esa fecha;
- está en la ficha, pero la oración no nombra su tema. Por ejemplo, "la inflación llegó a 59,6 %" se bloquea porque 59,6 es el cambio de las reservas.

Las fechas ("25 de noviembre") y los años no cuentan como cifras.

## Pasos

1. Ponte al día con `git pull`. Busca la ficha más reciente: `ls data/hechos/ | tail -1`. Su fecha (AAAA-MM-DD) es la del informe.
2. Lee la ficha completa. Si quieres contexto, lee también `site/pulso.json`, en especial `resumen`, `semana` y `notas_graficos`. Pero **cita solo cifras que estén en la ficha**.
3. Escribe `informes/AAAA-MM-DD.md`, con la misma fecha de la ficha, en una rama `informe/AAAA-MM-DD`.
4. Corre `python -m engine.verificador informes/AAAA-MM-DD.md`. Si alguna cifra no pasa, **corrige el texto**: usa la cifra de la ficha, nombra el tema en la misma oración o quita la cifra. Repite hasta que diga que todas coinciden.
5. Corre `python -m tests`. Abre el *pull request* con el título `Informe semanal AAAA-MM-DD`. No hagas merge. No toques nada fuera de `informes/`.
6. **Bitácora, siempre, aunque el informe ya existiera:** comenta en el issue #8 "Bitácora de las rutinas" con tus herramientas de GitHub (por ejemplo `mcp__github__add_issue_comment`). La **primera línea** debe ser exactamente `<!-- bitacora: informe AAAA-MM-DD -->`, con la fecha de hoy. Después va tu resumen: la ficha usada, cuántas cifras pasaron el verificador y el enlace al *pull request*. Si falta este comentario, el robot avisa el martes que la rutina falló.

## Forma del informe

- **Para quién:** cualquier persona adulta en Bolivia, sin formación económica. Escribe en español claro, de usted o impersonal, con oraciones cortas.
- **Largo:** entre 200 y 350 palabras.
- **Estructura:**
  ```
  ## <Un titular que diga lo principal de la semana, en una línea>

  <Párrafo 1: cómo está el índice y qué significa ese estado.>

  <Párrafo 2: qué empuja el riesgo hacia arriba (lo que está en rojo), con sus cifras.>

  <Párrafo 3: qué ayuda (lo que está en verde), con sus cifras.>

  **Qué mirar la próxima semana:** <una o dos cosas concretas. Si la ficha trae hechos "a un paso de cambiar"
  (ids que empiezan con distancia_, umbral_ e indice_si_), úsalos: "la brecha cambiaria está a 1,56 de pasar a
  amarillo; si pasara, el índice subiría a 54,3". No digas que va a pasar: solo cuánto le falta.>
  ```
- **Tono:** sobrio. Explicas, no opinas ni recomiendas. Nada de "hay que comprar dólares". No predices: el índice mide señales y no adivina el futuro.
- **Escribe cada cifra con su tema en la misma oración**, en formato boliviano: coma decimal y punto de miles, como en la ficha.
- Si un indicador **no votó** (no aparece en la ficha), dilo sin inventar su valor.

## Ejemplo de oraciones que pasan y que no pasan

- ✅ "El índice de riesgo está en 47,8 de 100, en vigilancia."
- ✅ "La inflación a 12 meses es de 7,08 %."
- ❌ "La inflación es de 59,6 %." Es una cifra real, pero de otro tema.
- ❌ "El dólar subió 2 % en la semana." La ficha no trae esa variación.
