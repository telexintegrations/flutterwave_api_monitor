import json
import feedparser
from fastapi import FastAPI,BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import httpx
from fastapi.responses import JSONResponse
from pydantic import BaseModel


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
    
class Setting(BaseModel):
    label: str
    type: str
    required: bool
    default: str


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
            
            return JSONResponse(content={
                "title": incident_title,
                "date": incident_date,
                "details": incident_description,
                "link": incident_link
            }) 
        
        return JSONResponse(content={"error": "No incidents found in RSS feed"}, status_code=404) 
    except Exception as e:
        return JSONResponse({"error": f"Failed to fetch RSS feed: {str(e)}"},status_code=500) 


@app.get("/integration")
def get_integration_json(background_tasks:BackgroundTasks):
    """Serve the integration settings JSON"""
    try:
        with open("integration.json", "r") as file:
            integration_json = json.load(file)
        
        # Extract return_url from the JSON file
        settings = integration_json.get("data", {}).get("settings", [])
        return_url = next((s["default"] for s in settings if s["label"] == "return_url"), None)
        channel_id = next((s["default"] for s in settings if s["label"] == "channel_id"), "default_telex_channel")

        
        if return_url:
            payload = MonitorPayload(return_url=return_url, channel_id=channel_id)
            background_tasks.add_task(monitor_task, payload)
        return integration_json
    except Exception as e:
        return {"error": f"Failed to load integration settings: {str(e)}"}


async def monitor_task(payload: MonitorPayload):
    """Background task to fetch RSS feed and post to return_url"""
    rss_data = fetch_rss_feed().body.decode()

    data = {
        "message": "Flutterwave Incident Update",
        "status": "success" if "error" not in rss_data else "failed",
        "incident": json.loads(rss_data),
        "channel_id":payload.channel_id
        
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(payload.return_url, json=data)
            response.raise_for_status()
        except Exception as e:
            print(f"Error posting data: {e}")
            
            
@app.post("/tick")
def send_incident_update(payload: MonitorPayload, background_tasks: BackgroundTasks):
    """Trigger the RSS fetch in the background"""
    background_tasks.add_task(monitor_task, payload)
    return JSONResponse(content={"status": "accepted", "message": "Incident update is being processed"})
