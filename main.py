import json
import feedparser
from fastapi import FastAPI

app = FastAPI()

RSS_FEED_URL = "https://status.flutterwave.com/history.rss"


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
            
            return {
                "title": incident_title,
                "date": incident_date,
                "details": incident_description,
                "link": incident_link
            }
        
        return {"error": "No incidents found in RSS feed"}
    except Exception as e:
        return {"error": f"Failed to fetch RSS feed: {str(e)}"}


@app.get("/integration")
def get_integration_json():
    """Serve the integration settings JSON"""
    try:
        with open("integration.json", "r") as file:
            integration_json = json.load(file)
        return integration_json
    except Exception as e:
        return {"error": f"Failed to load integration settings: {str(e)}"}
