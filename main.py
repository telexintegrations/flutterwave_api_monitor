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

RSS_FEED_URL = "https://status.flutterwave.com/history.rss"

class MonitorPayload(BaseModel):
    return_url: str
    channel_id: str
    
@app.get("/")
def fetch_rss_feed():
    """Fetch and parse the Flutterwave RSS feed"""
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        
        if feed.entries and len(feed.entries) > 0:
            latest_entry = feed.entries[0]
            incident_title = latest_entry.title
            incident_link = latest_entry.link
            incident_date = latest_entry.published
            incident_description = latest_entry.description
            
            logging.info("Fetched latest incident: %s", incident_title)

            return JSONResponse(content={
                "title": incident_title,
                "date": incident_date,
                "details": incident_description,
                "link": incident_link
            }) 
        
        logging.warning("No incident reports found.")
        return JSONResponse(content={"error": "No incident reports found."}, status_code=404)
    
    except Exception as e:
        logging.error("Failed to fetch RSS feed: %s", str(e))
        return JSONResponse(content={"error": f"Failed to fetch RSS feed: {str(e)}"}, status_code=500)
    

def monitor_task():
    try:
        rss_data = fetch_rss_feed().body.decode()
        incident_data = json.loads(rss_data)

        data = {
            "message": f"Flutterwave Incident Update \n {incident_data}",
            "status": "success",
            "event_name":"Payment update",
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



