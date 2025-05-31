from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional
import pandas as pd
import os
import math  # ← LEGG TIL DENNE

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

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
        # Også sørg for at ALLE rader har 'value' uten NaN
        records = result.to_dict(orient="records")
        for rec in records:
            v = rec.get("value")
            if isinstance(v, float) and math.isnan(v):
                rec["value"] = None
        return records

    if not result.empty:
        value = result["value"].mean()
        # FIX: Unngå NaN!
        if isinstance(value, float) and math.isnan(value):
            value = None
        else:
            value = round(value, 1)
        return {
            "Yrke": yrke,
            "Kjonn": kjonn,
            "Tid": tid,
            "Sektor": sektor,
            "value": value
        }
    else:
        return {"error": "Ingen data funnet for valgt filter."}

@app.options("/lonn/")
async def options_lonn():
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "*",
        },
    )
