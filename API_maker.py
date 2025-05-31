from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import pandas as pd
import os

# 1. Start FastAPI
app = FastAPI(
    title="Lønns-API for EdPath",
    description="API for søk etter lønn med yrke, kjønn, sektor og år. Med CORS for Lovable og Railway.",
    version="3.0"
)

# 2. Legg til CORS-middleware (tillat Lovable-domener)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://b91623da-c9a0-4af0-939c-cc22cd1cf669.lovableproject.com",
        "https://app.lovable.no"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# 3. Data: Last inn CSV-er fra mappe
DIR_PATH = "SSB data/CSV/Clean_11418"

def load_data():
    csv_files = [os.path.join(DIR_PATH, f) for f in os.listdir(DIR_PATH) if f.endswith(".csv")]
    dfs = [pd.read_csv(f) for f in csv_files]
    all_data = pd.concat(dfs, ignore_index=True)
    # Filtrer ut kun relevante rader – ikke sektor her!
    all_data = all_data[
        (all_data["AvtaltVanlig"] == "Heltidsansatte") &
        (all_data["ContentsCode"] == "Månedslønn (kr)") &
        (all_data["Kjonn"].isin(["Menn", "Kvinner", "Begge kjønn"])) &
        (all_data["MaaleMetode"] == "Gjennomsnitt")
    ]
    return all_data

df = load_data()

# 4. Endpoint med søkefelter
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

    # Hvis INGEN filter er valgt, returner ALLE rader som en liste med dicts
    if not any([yrke, kjonn, tid, sektor]):
        return result.to_dict(orient="records")

    # Ellers, hvis det er valgt filter, gi tilbake ett resultat eller error_s
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
