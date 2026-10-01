%%writefile README.md
# API Vols NYC 2013 (nycflights13)

## Installation
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

## Lancement
uvicorn app.api:app          # docs OpenAPI : /docs
REFRESH=1 uvicorn app.api:app   # force le re-téléchargement
python -m pytest             # tests (sans réseau)

## Données
CSV nycflights13 téléchargé au démarrage (variable FLIGHTS_URL pour changer d'URL), mis en cache dans .cache/ (non versionné). Colonne d'index Rdatasets retirée.

## Choix techniques et règles de nettoyage
- Pandas + FastAPI, données en mémoire, agrégats précalculés au démarrage.
- Doublons exacts supprimés ; lignes sans clé (date, carrier, origin, dest) supprimées.
- Valeurs numériques manquantes non imputées : un arr_delay absent (vol annulé ou dérouté) n'est pas un retard nul.
- is_delayed = arr_delay > 15, booléen nullable (<NA> si arr_delay absent) ; arr_delay_connu en complément.
- Stats de retard calculées uniquement sur les vols à arr_delay connu ; top 5 compagnies : minimum 100 vols avec arr_delay renseigné.
- Erreurs : 404 (aéroport ou compagnie inconnus), 422 (limit hors [1, 1000], offset < 0).
- /flights : filtres origin, carrier, pagination limit/offset.

## Limites et améliorations
- Tout en mémoire : pour de gros volumes, Parquet + DuckDB/Polars lazy ou base SQL, agrégats matérialisés.
- Pas de Docker ni de SQLite ; pas de contrôles qualité planifiés (pandera / Great Expectations).
- Pas d'endpoint destinations par aéroport.