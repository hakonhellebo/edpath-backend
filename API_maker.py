from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from typing import Optional, List
import pandas as pd
import os
import math


app = FastAPI()


# CORS
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


DIR_PATH = "SSB data/CSV/Clean_11418"  # dette er riktig, men pass på at mappen finnes!


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
   yrke: Optional[str] = Query(None),
   kjonn: Optional[str] = Query(None),
   tid: Optional[List[int]] = Query(None),  # <-- støtte for FLERE år
   sektor: Optional[str] = Query(None)
):
   result = df.copy()
   if yrke:
       result = result[result["Yrke"].str.lower() == yrke.lower()]
   if kjonn:
       result = result[result["Kjonn"].str.lower() == kjonn.lower()]
   if tid:
       result = result[result["Tid"].isin(tid)]
   if sektor:
       result = result[result["Sektor"].str.lower().str.strip() == sektor.lower().strip()]


   if not any([yrke, kjonn, tid, sektor]):
       records = result.to_dict(orient="records")
       for rec in records:
           v = rec.get("value")
           if isinstance(v, float) and math.isnan(v):
               rec["value"] = None
       return records


   if not result.empty:
       grouped = result.groupby("Tid")["value"].mean().reset_index()
       output = []
       for _, row in grouped.iterrows():
           year = int(row["Tid"])
           val = row["value"]
           if isinstance(val, float) and math.isnan(val):
               val = None
           else:
               val = round(val, 1)
           output.append({"Tid": year, "value": val})
       return output
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
