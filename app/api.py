import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from app.data import charger, nettoyer, stats_retard, calculer_indicateurs

LIMITE_MAX = 1000
COLONNES = ["flight_date", "carrier", "flight", "origin", "dest", "dep_delay", "arr_delay", "is_delayed"]

DONNEES = {}


@asynccontextmanager
async def demarrage(app):
    vols = nettoyer(charger())
    DONNEES["vols"] = vols
    DONNEES["indicateurs"] = calculer_indicateurs(vols)
    DONNEES["aeroports"] = {}
    for origine, groupe in vols.groupby("origin"):
        DONNEES["aeroports"][origine] = stats_retard(groupe)
    yield


app = FastAPI(title="API vols NYC 2013", lifespan=demarrage)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/stats")
def stats():
    return DONNEES["indicateurs"]


@app.get("/airports")
def airports():
    return sorted(DONNEES["aeroports"].keys())


@app.get("/airports/{airport}/stats")
def airport_stats(airport: str):
    code = airport.upper()
    if code not in DONNEES["aeroports"]:
        raise HTTPException(status_code=404, detail="Aéroport inconnu : " + airport)
    resultat = {"airport": code}
    resultat.update(DONNEES["aeroports"][code])
    return resultat


@app.get("/flights")
def flights(origin: str = None, carrier: str = None,
            limit: int = Query(10, ge=1, le=LIMITE_MAX), offset: int = Query(0, ge=0)):
    vols = DONNEES["vols"]

    if origin:
        if origin.upper() not in DONNEES["aeroports"]:
            raise HTTPException(status_code=404, detail="Aéroport inconnu : " + origin)
        vols = vols[vols["origin"] == origin.upper()]

    if carrier:
        if carrier.upper() not in DONNEES["indicateurs"]["flights_by_carrier"]:
            raise HTTPException(status_code=404, detail="Compagnie inconnue : " + carrier)
        vols = vols[vols["carrier"] == carrier.upper()]

    page = vols[COLONNES].iloc[offset:offset + limit].copy()
    page["flight_date"] = page["flight_date"].dt.strftime("%Y-%m-%d")
    # to_json transforme les NaN en null (sinon le JSON est invalide)
    items = json.loads(page.to_json(orient="records"))
    return {"total": len(vols), "limit": limit, "offset": offset, "items": items}