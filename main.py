from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import httpx
from datetime import datetime, timezone
import pytz

app = FastAPI()

STORMGLASS_API_KEY = "hier-je-api-key"
TIMEZONEDB_API_KEY = "hier-je-api-key"

@app.get("/tide")
async def tide(request: Request):
    try:
        plaats = request.query_params.get("plaats")
        lat = request.query_params.get("lat")
        lng = request.query_params.get("lng")

        if not lat or not lng:
            if not plaats:
                return JSONResponse({"fout": "lat en lng zijn verplicht"}, status_code=400)
            async with httpx.AsyncClient() as client:
                geo_response = await client.get("https://nominatim.openstreetmap.org/search",
                                                params={"q": plaats, "format": "json"})
            if geo_response.status_code != 200 or not geo_response.json():
                return JSONResponse({"fout": "Kon locatie niet vinden"}, status_code=400)
            data = geo_response.json()[0]
            lat = data["lat"]
            lng = data["lon"]

        timezone_url = f"http://api.timezonedb.com/v2.1/get-time-zone?key={TIMEZONEDB_API_KEY}&format=json&by=position&lat={lat}&lng={lng}"
        async with httpx.AsyncClient() as client:
            tz_response = await client.get(timezone_url)

        if tz_response.status_code != 200:
            return JSONResponse({"fout": "Kon tijdzone niet bepalen"}, status_code=500)

        tz_data = tz_response.json()
        local_tz = pytz.timezone(tz_data["zoneName"])

        now_utc = datetime.now(timezone.utc).isoformat()
        stormglass_url = f"https://api.stormglass.io/v2/tide/extremes/point?lat={lat}&lng={lng}&start={now_utc}&end={now_utc}"
        headers = {"Authorization": STORMGLASS_API_KEY}

        async with httpx.AsyncClient() as client:
            sg_response = await client.get(stormglass_url, headers=headers)

        if sg_response.status_code != 200:
            return JSONResponse({"fout": "Stormglass gaf geen geldige response"}, status_code=500)

        sg_data = sg_response.json()
        return JSONResponse(sg_data)

    except Exception as e:
        return JSONResponse({"fout": f"Interne serverfout: {str(e)}"}, status_code=500)
