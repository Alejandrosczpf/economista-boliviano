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
python -m pytest -q         # 23 pruebas (necesita pytest)
```

Then open `site/index.html` in a browser. The page carries its data inside, so it doesn't need a server.

## Structure

| Folder | What it holds |
|---|---|
| `config/series.json` | **Contract** for each series: possible range, credible jump, maximum age, known breaks (e.g. 29 Jun 2026) |
| `collectors/fuentes.py` | Collectors: manual, BCB official exchange rate, World Bank API, IMF API (SDMX 3.0, with DataMapper as fallback) |
| `pipeline/validate.py` | Quarantine: data that breaks its contract doesn't enter the calculation. The allowed jump grows with elapsed time |
| `pipeline/store.py` | `data/observaciones.csv`. Each git commit is a "vintage": you can see what the system knew on any date |
| `engine/motor.py` | KLR-style risk index, **recalibrated to the June 2026 float**, plus historical episodes |
| `engine/pulso.py` | Builds `site/pulso.json` and `site/index.html` with educational explanations |
| `engine/verificador.py` | Compares every number in an AI-written report against the data; if one doesn't match, publication is blocked |
| `reports/salud.md` | Health report: freshness of each series, quarantine, failed sources |
| `.github/workflows/recolectar.yml` | Runs Monday to Friday at 09:17 Bolivia time, saves data and publishes to GitHub Pages |

## Rules the system enforces

1. **No guessing.** An indicator without fresh data does not vote in the index; it shows as "Sin dato fresco".
2. **No unchecked data gets in.** Anything out of range or with an impossible jump goes to quarantine with its reason.
3. **No unverified number gets published.** That is the job of `verificador.py`.
4. **No formula change goes through if it breaks history.** The tests require it to keep recognizing 1985, 2016, 2019, 2023 and 2024.

## Data that is still loaded by hand

Some sources have no public API: the parallel dollar, EMBI, BCB reserves, INE inflation and agency projections. They are entered in `data/manual/entradas.csv`, each with a source and a link. The plan is for the AI to add them every week from the official bulletins, and over time to replace them with automatic collectors.

## Upload to GitHub (once)

1. Create an empty **public** repository named `economista-boliviano`. Public repositories have unlimited free Actions minutes.
2. Upload this folder: `git init && git add . && git commit -m "Fase 1" && git branch -M main && git remote add origin https://github.com/<usuario>/economista-boliviano.git && git push -u origin main`
3. In **Settings → Pages**, under *Source*, choose **GitHub Actions**.
4. In **Actions**, run "Recolectar y publicar el Pulso" with *Run workflow*.

Private material (bitácora, notes, preferences) does **not** go in this repository.
