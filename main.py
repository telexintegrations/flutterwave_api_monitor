import json
import feedparser
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import re
import os 
from dotenv import load_dotenv


load_dotenv()


logging.basicConfig(filename="app.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"], 
)

STATUS_API_URL = "https://status.flutterwave.com/api/v2/status.json"

class MonitorPayload(BaseModel):
    return_url: str
    channel_id: str
    
@app.get("/")
def fetch_status_api():
    """Fetch and parse the Flutterwave Status API"""
    try:
        response = httpx.get(STATUS_API_URL)
        response.raise_for_status()
        status_data=response.json()
        
        logging.info("Fetched latest status: %s", status_data["status"]["description"])
        
        return JSONResponse(content={
            "status": status_data["status"]["description"],
            "indicator": status_data["status"]["indicator"],
            "updated_at": status_data["page"]["updated_at"]
        }) 
        
    except Exception as e:
        logging.error("Failed to fetch Status API: %s", str(e))
        return JSONResponse(content={"error": f"Failed to fetch Status API: {str(e)}"}, status_code=500)
    

def monitor_task():
    try:
        rss_data = fetch_status_api().body.decode()
        parsed_data = json.loads(rss_data)

        data = {
            "message": f"Flutterwave Incident Update \n {parsed_data}",
            "status": "success",
            "event_name":"Status update",
            "username":"Flutterwave monitor"
        
        }
        
        logging.info("Sending data to Telex: %s", json.dumps(data, indent=2))
        response = httpx.post(os.getenv("TELEX_WEBHOOK"), json=data)
        
        response.raise_for_status()
        
        logging.info("Successfully sent data to Telex, response: %s", response.text)
        
    except Exception as e:
        logging.error("Error posting data to Telex: %s", str(e))

@app.post("/tick")
def send_incident_update(background_tasks: BackgroundTasks):
    logging.info("Received tick request with payload")
    
    background_tasks.add_task(monitor_task)
    
    return JSONResponse(content={"status": "accepted", "message": "Incident update is being processed"})

@app.get("/integration")
def get_integration():
    """Return integration details from JSON file"""
    try:
        with open("integration.json", "r") as file:
            integration_data = json.load(file)
        
        return JSONResponse(content=integration_data)
    
    except Exception as e:
        logging.error("Failed to load integration.json: %s", str(e))
        return JSONResponse(content={"error": "Failed to load integration.json"}, status_code=500)



