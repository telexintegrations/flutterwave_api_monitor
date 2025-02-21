import json
import feedparser
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure Logging
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
        
        logging.warning("No incidents found in RSS feed")
        return JSONResponse(content={"error": "No incidents found in RSS feed"}, status_code=404)
    
    except Exception as e:
        logging.error("Failed to fetch RSS feed: %s", str(e))
        return JSONResponse({"error": f"Failed to fetch RSS feed: {str(e)}"}, status_code=500) 

async def monitor_task(payload: MonitorPayload):
    """Background task to fetch RSS feed and post to return_url"""
    try:
        rss_data = fetch_rss_feed().body.decode()
        incident_data = json.loads(rss_data)

        data = {
            "message": "Flutterwave Incident Update",
            "status": "success" if "error" not in incident_data else "failed",
            "incident": incident_data,
            "channel_id": payload.channel_id
        }

        logging.info("Sending data to Telex: %s", json.dumps(data, indent=2))

        async with httpx.AsyncClient() as client:
            response = await client.post(payload.return_url, json=data)
            response.raise_for_status()
            logging.info("Successfully sent data to Telex, response: %s", response.text)
        
    except Exception as e:
        logging.error("Error posting data to Telex: %s", str(e))

@app.post("/tick")
def send_incident_update(payload: MonitorPayload, background_tasks: BackgroundTasks):
    """Trigger the RSS fetch in the background"""
    logging.info("Received tick request with payload: %s", payload.dict())
    
    background_tasks.add_task(monitor_task, payload)
    
    return JSONResponse(content={"status": "accepted", "message": "Incident update is being processed"})
