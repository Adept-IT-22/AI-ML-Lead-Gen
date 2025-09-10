from typing import List, TypedDict

class EventData(TypedDict):
    type: str #should always be "event"
    source: str #e.g. eventbrite
    title: List[str] #e.g. ["AI & The Future", "All About AI"]
    link: List[str]
    event_date: List[str]
    country: List[str]
    city: List[str]
    event_id: List[str]
    event_summary: List[str]
    event_is_online: List[str]
    event_organizer_id: List[str]
    tags: List[List[str]]

fetched_event_data = {
    "type": "event",
    "source": "",
    "title": [],
    "link": [],
    "event_date": [],
    "country": [],
    "city": [],
    "event_id": [],
    "event_summary": [],
    "event_is_online": [],
    "event_organizer_id": [],
    "tags": []
}