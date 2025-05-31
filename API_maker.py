from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd
import os

# Start FastAPI
app = FastAPI(
    title="Lønns-API for EdPath",
    description="API for søk etter lønn med yrke, kjønn, sektor og år. Med CORS for Lovable og Railway.",
    version="3.0"
)

# NB! For utvikling: tillat ALLE origins (fjerner CORS-problemer på Lovable/dev/prod/preview)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- Endre til bare prod-domener senere!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DIR_PATH = "SSB data/CSV/Clean_11418"

def load_data():
    csv_files = [os.path.join(DIR_PATH, f) for f in os.listdir(DIR_PATH) if f.endswith(".csv")]
    dfs = [pd.read_csv(f) for f in csv_files]
    all_data = pd.concat(dfs, ignore_index=True)
    all_data = all_data[
        (all_data["AvtaltVanlig"] == "Heltidsansatte") &
        (all_data["ContentsCode"] == "Månedslønn (kr)") &
        (all_data["Kjonn"].isin(["Menn", "Kvinner", "Begge kjønn"])) &
        (all_data["MaaleMetode"] == "Gjennomsnitt")
    ]
    return all_data

df = load_data()

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
        result = result[result["Sektor"].str.lower().str.strip() == sektor.lower().strip()]

    if not any([yrke, kjonn, tid, sektor]):
        return result.to_dict(orient="records")

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
