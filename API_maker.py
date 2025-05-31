from fastapi import FastAPI, Query
from typing import Optional
import pandas as pd
import os

DIR_PATH = "SSB data/CSV/Clean_11418"

def load_data():
    csv_files = [os.path.join(DIR_PATH, f) for f in os.listdir(DIR_PATH) if f.endswith(".csv")]
    dfs = []
    for file in csv_files:
        df = pd.read_csv(file)
        dfs.append(df)
    all_data = pd.concat(dfs, ignore_index=True)
    # IKKE filtrer bort sektor her – vi skal filtrere på sektor i endpointet!
    all_data = all_data[
        (all_data["AvtaltVanlig"] == "Heltidsansatte") &
        (all_data["ContentsCode"] == "Månedslønn (kr)") &
        (all_data["Kjonn"].isin(["Menn", "Kvinner", "Begge kjønn"])) &
        (all_data["MaaleMetode"] == "Gjennomsnitt")
    ]
    return all_data

df = load_data()

app = FastAPI(
    title="Lønns-API for EdPath",
    description="Nå med SEKTOR som søkefilter! Endelig.",
    version="2.5"
)

@app.get("/lonn/")
def get_lonn(
    yrke: Optional[str] = Query(None, description="F.eks. 'Sykepleier'"),
    kjonn: Optional[str] = Query(None, description="Menn, Kvinner, Begge kjønn"),
    tid: Optional[int] = Query(None, description="År, f.eks. 2022"),
    sektor: Optional[str] = Query(None, description="Sektor, f.eks. 'Sum alle sektorer', 'Privat sektor og offentlige eide foretak', 'Statsforvaltningen', 'Kommune og fylkeskommune'")
):
    result = df.copy()
    if yrke:
        result = result[result["Yrke"].str.lower() == yrke.lower()]
    if kjonn:
        result = result[result["Kjonn"].str.lower() == kjonn.lower()]
    if tid:
        result = result[result["Tid"] == tid]
    if sektor:
        # Sektor må samsvare nøyaktig, men case-insensitive og strip for spaces
        result = result[result["Sektor"].str.lower().str.strip() == sektor.lower().strip()]

    if not result.empty:
        value = result["value"].mean()
        return {
            "Yrke": yrke,
            "Kjonn": kjonn,
            "Tid": tid,
            "Sektor": sektor,
            "value": round(value, 1)
        }
    else:
        return {"error": "Ingen data funnet for valgt filter."}
