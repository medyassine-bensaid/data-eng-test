import os
import urllib.request
import pandas as pd

URL = os.getenv("FLIGHTS_URL", "https://raw.githubusercontent.com/vincentarelbundock/Rdatasets/master/csv/nycflights13/flights.csv")
FICHIER = "flights.csv"
SEUIL_RETARD = 15
MIN_VOLS = 100


def telecharger(forcer=False):
    if forcer or not os.path.exists(FICHIER):
        print("Téléchargement du fichier...")
        urllib.request.urlretrieve(URL, FICHIER)
    else:
        print("Fichier déjà présent, pas de téléchargement")


def charger(forcer=False):
    telecharger(forcer)
    df = pd.read_csv(FICHIER)
    # Rdatasets ajoute une colonne d'index : on l'enlève sinon aucun doublon n'est détectable
    for colonne in df.columns:
        if colonne.startswith("Unnamed") or colonne == "rownames":
            df = df.drop(columns=colonne)
    return df


def diagnostiquer(df):
    print("Nombre de lignes :", df.shape[0])
    print("Nombre de colonnes :", df.shape[1])

    print(df.dtypes)

    nb_manquantes = df.isna().sum()
    taux = (nb_manquantes / len(df) * 100).round(2)
    tableau = pd.DataFrame({"nombre": nb_manquantes, "taux_%": taux})
    print(tableau[tableau["nombre"] > 0])

    print(df.duplicated().sum())

    print(df.describe().T.round(2))


def nettoyer(df):
    nb_depart = len(df)

    df = df.drop_duplicates().copy()
    print("Doublons supprimés :", nb_depart - len(df))

    avant = len(df)
    df = df.dropna(subset=["year", "month", "day", "carrier", "origin", "dest"]).copy()
    print("Lignes sans info essentielle supprimées :", avant - len(df))

    df["flight_date"] = pd.to_datetime(df[["year", "month", "day"]])
    df["arr_delay_connu"] = df["arr_delay"].notna()

    df["is_delayed"] = (df["arr_delay"] > SEUIL_RETARD).astype("boolean")
    df.loc[df["arr_delay"].isna(), "is_delayed"] = pd.NA

    print("Lignes restantes :", len(df))
    return df.reset_index(drop=True)


def stats_retard(df):
    connus = df[df["arr_delay_connu"]]
    nb_connus = len(connus)
    nb_retardes = int(connus["is_delayed"].sum())

    if nb_connus > 0:
        pourcentage = round(nb_retardes / nb_connus * 100, 2)
        moyenne = round(float(connus["arr_delay"].mean()), 2)
    else:
        pourcentage = 0.0
        moyenne = None

    return {
        "total_flights": len(df),
        "delayed_flights": nb_retardes,
        "delayed_percentage": pourcentage,
        "average_arrival_delay": moyenne,
    }


def calculer_indicateurs(df):
    resultat = stats_retard(df)
    resultat["flights_by_origin"] = df["origin"].value_counts().to_dict()
    resultat["flights_by_carrier"] = df["carrier"].value_counts().to_dict()

    top_dest = []
    for dest, nb in df["dest"].value_counts().head(10).items():
        top_dest.append({"dest": dest, "flights": int(nb)})
    resultat["top_destinations"] = top_dest

    connus = df[df["arr_delay_connu"]]
    groupe = connus.groupby("carrier")["arr_delay"].agg(["mean", "count"])
    groupe = groupe[groupe["count"] >= MIN_VOLS]
    groupe = groupe.sort_values("mean", ascending=False).head(5)

    top_comp = []
    for code, ligne in groupe.iterrows():
        top_comp.append({
            "carrier": code,
            "average_arrival_delay": round(float(ligne["mean"]), 2),
            "flights": int(ligne["count"]),
        })
    resultat["top_delayed_carriers"] = top_comp
    return resultat