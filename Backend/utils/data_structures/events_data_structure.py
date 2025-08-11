from typing import List, TypedDict

class EventData(TypedDict):
    type: str #should always be "event"
    source: str #e.g. eventbrite
    event_title: List[str] #e.g. ["AI & The Future", "All About AI"]
    event_link: List[str]
    event_date: List[str]
    event_country: List[str]
    event_city: List[str]
    event_id: List[str]
    event_summary: List[str]
    event_is_online: List[str]
    event_tags: List[List[str]]

fetched_event_data = {
    "type": "event",
    "source": "",
    "event_title": [],
    "event_link": [],
    "event_date": [],
    "event_country": [],
    "event_city": [],
    "event_id": [],
    "event_summary": [],
    "event_is_online": [],
    "event_tags": []
}