import pandas as pd
import pytest
from fastapi.testclient import TestClient
import app.api as api
from app.donnees import nettoyer, stats_retard, calculer_indicateurs


def petit_jeu():
    return pd.DataFrame({
        "year": [2013] * 5, "month": [1] * 5, "day": [1, 1, 2, 3, 3],
        "arr_delay": [20.0, 10.0, None, -5.0, -5.0],
        "dep_delay": [5.0, 0.0, None, -2.0, -2.0],
        "flight": [1, 2, 3, 4, 4],
        "carrier": ["AA", "AA", "UA", "UA", "UA"],
        "origin": ["JFK", "JFK", "EWR", "EWR", "EWR"],
        "dest": ["LAX", "LAX", "SFO", "SFO", "SFO"],
    })


def test_nettoyage():
    vols = nettoyer(petit_jeu())
    assert len(vols) == 4                              # doublon supprimé
    assert str(vols["flight_date"].dtype).startswith("datetime64")
    assert vols["is_delayed"].tolist()[:2] == [True, False]
    assert pd.isna(vols["is_delayed"].iloc[2])         # inconnu, pas False
    assert vols["arr_delay"].isna().sum() == 1         # pas remplacé par 0


def test_indicateurs():
    vols = nettoyer(petit_jeu())
    s = stats_retard(vols)
    assert s["total_flights"] == 4
    assert s["delayed_flights"] == 1
    assert s["delayed_percentage"] == 33.33            # 1 sur 3 connus
    assert s["average_arrival_delay"] == 8.33          # (20+10-5)/3
    assert calculer_indicateurs(vols)["top_delayed_carriers"] == []   # pas 100 vols


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(api, "charger", lambda forcer=False: petit_jeu())
    with TestClient(api.app) as c:
        yield c


def test_api_ok(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/stats").json()["total_flights"] == 4
    assert client.get("/airports").json() == ["EWR", "JFK"]
    assert client.get("/airports/jfk/stats").json()["total_flights"] == 2
    r = client.get("/flights?origin=jfk&limit=1").json()
    assert len(r["items"]) == 1 and r["total"] == 2


@pytest.mark.parametrize("url,code", [
    ("/airports/XXX/stats", 404), ("/flights?carrier=ZZ", 404),
    ("/flights?origin=XXX", 404), ("/flights?limit=-1", 422), ("/flights?limit=99999", 422),
])
def test_api_erreurs(client, url, code):
    assert client.get(url).status_code == code