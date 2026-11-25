# Candidatos a nuevos indicadores: prueba con la historia (1980-2025)

Reglas fijadas **antes** de ver los resultados (sesión 15). Detalle en `engine/candidatos.py`.

- **Crisis y año previo:** 1981, 1982, 1983, 1984, 1985, 2001, 2002, 2003, 2022, 2023, 2024, 2025
- **Neutros (no cuentan):** 1980, 1986, 2015, 2016, 2019, 2020, 2021
- **Calma:** el resto de 1980-2025.
- **Índice actual (sin candidatos):** separación crisis − calma = 46.7 puntos; 10 de 12 años de crisis fuera de 'calma'; falsas alarmas: ninguna.

| Candidato | Umbrales (amarillo / rojo) | Ruido/señal | Separación con él | Falsas alarmas | Pruebas | ¿Entra? |
|---|---|---|---|---|---|---|
| Cuenta corriente (% del PIB) | ≤ -3 / ≤ -5 | 1.33 (rojo en 2/12 de crisis y 6/27 de calma) | 39.1 | ninguna | fallan: 1981-1985 en alerta; 2022 con aviso (más de 50); 2019 más de 30 puntos sobre 2014 | **no** |
| Dinero (M2) sobre reservas (veces) | ≥ 5 / ≥ 10 | 0.0 (rojo en 3/12 de crisis y 0/27 de calma) | 44.6 | ninguna | fallan: 1981-1985 en alerta | **no** |
| Exportaciones: cambio anual (%) | ≤ 0 / ≤ -10 | 0.41 (rojo en 2/11 de crisis y 2/27 de calma) | 43.1 | ninguna | fallan: 1981-1985 en alerta; 2022 con aviso (más de 50) | **no** |
| Crédito privado: cambio en un año (puntos del PIB) | ≥ 3 / ≥ 5 | 1.78 (rojo en 1/12 de crisis y 4/27 de calma) | 38.5 | ninguna | fallan: 1981-1985 en alerta; 2022 con aviso (más de 50); 2019 más de 30 puntos sobre 2014 | **no** |

Condiciones de cada candidato:

- **Cuenta corriente:** 1. ruido/señal < 1 ❌; 2. separa mejor crisis de calma ❌; 3. sin falsas alarmas nuevas ✅; 4. pruebas históricas pasan ❌
- **Dinero (M2) sobre reservas:** 1. ruido/señal < 1 ✅; 2. separa mejor crisis de calma ❌; 3. sin falsas alarmas nuevas ✅; 4. pruebas históricas pasan ❌
- **Exportaciones: cambio anual:** 1. ruido/señal < 1 ✅; 2. separa mejor crisis de calma ❌; 3. sin falsas alarmas nuevas ✅; 4. pruebas históricas pasan ❌
- **Crédito privado: cambio en un año:** 1. ruido/señal < 1 ❌; 2. separa mejor crisis de calma ❌; 3. sin falsas alarmas nuevas ✅; 4. pruebas históricas pasan ❌

Sin historia suficiente para la prueba:

- Depósitos y bolivianización (BCB/ASFI): no hay serie pública anual desde 1980; quedan como contexto posible.

**Lectura:** un indicador puede ser bueno solo y empeorar el índice, porque vota en verde en crisis que no
son de su tipo (por ejemplo, M2/reservas fue bajo en la hiperinflación de los 80, cuando la inflación había
destruido el valor del dinero). Cambiar pesos o umbrales después de ver estos resultados sería acomodar las
reglas a los datos: queda como propuesta para la revisión de junio de 2027. Los candidatos con ruido/señal < 1
se muestran en el Pulso como contexto, sin votar.
