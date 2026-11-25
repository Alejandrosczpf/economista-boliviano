# Economista Boliviano — Fase 1: cimientos

A system that collects data on the Bolivian economy, validates it, computes an early-warning risk index and publishes the **Pulso**, a dashboard with an educational layer, every weekday.

```
recolectar → validar (contratos + cuarentena) → guardar (CSV con historial en git)
          → calcular (motor de riesgo) → publicar (site/index.html) → informe de salud
```

The work plan, session by session, is in [PLAN.md](PLAN.md).

## Running it on your PC

Requires Python 3.10 or newer. No packages need to be installed: only Python's standard library is used.

```bash
python run.py --sin-red     # solo datos de data/manual/entradas.csv
python run.py               # además BCB, Banco Mundial y FMI por internet
python -m tests             # todas las pruebas, sin instalar nada
python -m pytest -q         # lo mismo con pytest (más detalle si algo falla)
```

Then open `site/index.html` in a browser. The page carries its data inside, so it doesn't need a server.

## Structure

| Folder | What it holds |
|---|---|
| `config/series.json` | **Contract** for each series: possible range, credible jump, maximum age, known breaks (e.g. 29 Jun 2026) |
| `collectors/fuentes.py` | Collectors: manual; BCB official exchange rate (daily table + day's page); BCB reserves (official Excel: net, gross, foreign currency); INE inflation (monthly CPI releases); parallel dollar from [paralelo.bo](https://paralelo.bo) (data under CC-BY 4.0); World Bank API; IMF API (SDMX 3.0, with DataMapper as fallback) |
| `data/manual/aprobados.csv` | Data a person reviewed after quarantine and confirmed as real, with the reason and a link. Skips the jump check, not the range check |
| `pipeline/validate.py` | Quarantine: data that breaks its contract doesn't enter the calculation. The allowed jump grows with elapsed time |
| `pipeline/store.py` | `data/observaciones.csv`. Each git commit is a "vintage": you can see what the system knew on any date |
| `engine/motor.py` | KLR-style risk index, **recalibrated to the June 2026 float**, with asymmetric hysteresis between states |
| `engine/historia.py` | Year-by-year backtest since 1980 with official series (IMF WEO, BCB, World Bank, paralelo.bo), each value with its source. Written to `reports/historia.md` |
| `engine/memoria.py` | The index for each day since 29 Jun 2026 (`data/indice.csv`): "en vivo" rows are frozen; the rest are rebuilt using only data that had been published by each date (`rezago_dias`) |
| `engine/pulso.py` | Builds `site/pulso.json` and `site/index.html` with educational explanations |
| `engine/verificador.py` | Compares every number in an AI-written report against the data; if one doesn't match, publication is blocked |
| `reports/salud.md` | Health report: freshness of each series, quarantine, failed sources, current alerts |
| `pipeline/avisos.py` | Alerts as GitHub issues (label `robot`): a source down 2 runs in a row, an expired series, a manual series that expires within 7 days. Closes them by itself once solved |
| `.github/workflows/recolectar.yml` | Runs Monday to Friday at 09:17 Bolivia time, saves data and publishes to GitHub Pages |

## Rules the system enforces

1. **No guessing.** An indicator without fresh data does not vote in the index; it shows as "Sin dato fresco".
2. **No unchecked data gets in.** Anything out of range or with an impossible jump goes to quarantine with its reason.
3. **No unverified number gets published.** That is the job of `verificador.py`.
4. **No formula change goes through if it breaks history.** With official data stored in the repository, the tests require it to keep recognizing 1981-1985, 2016, 2019, 2023 and 2024, calm in 2005-2014, and the warning of 2022.
5. **No state change from a one-day wobble.** Moving up a state is immediate; moving down requires falling 3 points below the threshold.

## Alerts

You don't need to check the report every day. When something needs attention, the robot opens an *issue* in the repository's **Issues** tab, and GitHub sends you an email. When the problem is fixed, the robot closes it. If the whole run fails, it also opens an issue. To test that path: **Actions → Run workflow**, tick *Simular una falla*.

## Data that is still loaded by hand

Some sources have no public API: EMBI, agency GDP projections, the fiscal deficit and the monetary base. They are entered in `data/manual/entradas.csv`, each with a source and a link. The plan is for the AI to add them every week from the official bulletins, and over time to replace them with automatic collectors.

## Upload to GitHub (once)

1. Create an empty **public** repository named `economista-boliviano`. Public repositories have unlimited free Actions minutes.
2. Upload this folder: `git init && git add . && git commit -m "Fase 1" && git branch -M main && git remote add origin https://github.com/<usuario>/economista-boliviano.git && git push -u origin main`
3. In **Settings → Pages**, under *Source*, choose **GitHub Actions**.
4. In **Actions**, run "Recolectar y publicar el Pulso" with *Run workflow*.

Private material (bitácora, notes, preferences) does **not** go in this repository.
