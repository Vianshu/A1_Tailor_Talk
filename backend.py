from dotenv import load_dotenv
import os

# backend.py
from fastapi import FastAPI
from pydantic import BaseModel

# from google import genai
# from google.genai import types
import json
from typing import List, Literal, TypedDict, Optional
from datetime import datetime
from google.generativeai import GenerativeModel, configure
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage # Import ToolMessage

# 1. Setting up Gemini Key for google genai API
load_dotenv("keys.env")

configure(api_key=os.getenv("GEMIN_KEY"))
# client = genai.Client(api_key=os.getenv("GEMIN_KEY"))
# --- Define Your Tools (Python Functions) ---


# This function simulates fetching calendar events
# In a real app, this would use the Google Calendar API


import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = None
# The file token.json stores the user's access and refresh tokens, and is
# created automatically when the authorization flow completes for the first
# time.
if os.path.exists("token.json"):
  creds = Credentials.from_authorized_user_file("token.json", SCOPES)
# If there are no (valid) credentials available, let the user log in.
if not creds or not creds.valid:
  if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())
  else:
    flow = InstalledAppFlow.from_client_secrets_file(
        "credentials.json", SCOPES
    )
    creds = flow.run_local_server(port=0)
  # Save the credentials for the next run
  with open("token.json", "w") as token:
    token.write(creds.to_json())
try:
    service = build("calendar", "v3", credentials=creds)
except Exception as e:
    print(f"An error occurred: {e}")
    service = None


def add_calendar_event(summary: str, start_datetime: str, end_datetime: str, location: Optional[str] = None, attendees: Optional[list] = None) -> str:
    """
    Adds a new event to Google Calendar.
    Args:
        summary: Event title.
        start_datetime: ISO datetime string (e.g., 2025-07-03T14:00:00).
        end_datetime: ISO datetime string.
        location: Optional location.
        attendees: Optional list of attendee emails.
    Returns:
        JSON string with success or error info.
    """
    try:
        event_body = {
            'summary': summary,
            'start': {'dateTime': start_datetime, 'timeZone': 'UTC'},
            'end': {'dateTime': end_datetime, 'timeZone': 'UTC'},
        }
        if location:
            event_body['location'] = location
        if attendees:
            event_body['attendees'] = [{'email': email} for email in attendees]

        event = service.events().insert(calendarId='primary', body=event_body).execute()
        return json.dumps({"status": "success", "event_id": event['id'], "message": "Event created successfully."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_calendar_events(start_date: Optional[str] = None, end_date: Optional[str] = None, summary_keyword: Optional[str] = None, attendee_email: Optional[str] = None) -> str:
    """
    Fetches events from Google Calendar.
    Use it to search for events based on date range, summary keyword, or attendee email to delete or modify t
    Args:
        start_date: YYYY-MM-DD (start filter).
        end_date: YYYY-MM-DD (end filter). (optional)
        summary_keyword: Filter by keyword in summary. (optional)
        attendee_email: Filter by attendee email. (optional)
    Returns:
        JSON string with events or error info.
    """
    try:
        time_min = f"{start_date}T00:00:00Z" if start_date else None
        time_max = f"{end_date}T23:59:59Z" if end_date else None

        events_result = service.events().list(
            calendarId='primary',
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])
        filtered_events = []
        for event in events:
            match = True
            if summary_keyword and summary_keyword.lower() not in event.get('summary', '').lower():
                match = False
            if attendee_email and attendee_email.lower() not in [a['email'].lower() for a in event.get('attendees', [])]:
                match = False
            if match:
                filtered_events.append(event)
        print(f"Found {len(filtered_events)} events matching criteria.")
        return json.dumps({"events": filtered_events})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def delete_calendar_event(event_id: str) -> str:
    """
    Deletes an event from Google Calendar by ID.
    Args:
        event_id: The event's unique ID.
    Returns:
        JSON string with success or error info.
    """
    try:
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        return json.dumps({"status": "success", "message": f"Event {event_id} deleted successfully."})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})



get_calendar_events_schema = types.FunctionDeclaration(
    name="get_calendar_events",
    description="Fetches events from Google Calendar.",
    parameters=types.Schema(
        type="object",
        properties={
            "start_date": types.Schema(type="string", description="Start date YYYY-MM-DD."),
            "end_date": types.Schema(type="string", description="End date YYYY-MM-DD."),
            "summary_keyword": types.Schema(type="string", description="Keyword to filter events."),
            "attendee_email": types.Schema(type="string", description="Filter by attendee email."),
        },
    ),
)

delete_calendar_event_schema = types.FunctionDeclaration(
    name="delete_calendar_event",
    description="Deletes a calendar event by ID.",
    parameters=types.Schema(
        type="object",
        properties={
            "event_id": types.Schema(type="string", description="ID of the event to delete."),
        },
        required=["event_id"],
    ),
)

add_calendar_event_schema = types.FunctionDeclaration(
    name="add_calendar_event",
    description="Adds a new event to Google Calendar.",
    parameters=types.Schema(
        type="object",
        properties={
            "summary": types.Schema(type="string", description="Event title."),
            "start_datetime": types.Schema(type="string", description="Start datetime in ISO format."),
            "end_datetime": types.Schema(type="string", description="End datetime in ISO format."),
            "location": types.Schema(type="string", description="Optional location."),
            "attendees": types.Schema(type="array", items=types.Schema(type="string"), description="List of attendee emails."),
        },
        required=["summary", "start_datetime", "end_datetime"],
    ),
)

from datetime import datetime
def get_current_datetime() -> str:
    """
    Gets the current date and time in the specified format.
    Args:
        No arguments.
    Returns:
        A string representing the current date and time in format "%Y-%m-%d %H:%M:%S".
    """
    
    try:
        return json.dumps({"status": "success", "message": f"Today's date and time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


tools = [get_calendar_events,
        delete_calendar_event,
        add_calendar_event,
        get_current_datetime
    ]




# --- LangGraph State Definition ---
class ChatState(TypedDict):
    messages: List[HumanMessage | AIMessage | ToolMessage] # Added ToolMessage

# --- LangGraph Node Functions ---

def call_gemini(state: ChatState) -> dict:
    """
    Calls the Gemini API, potentially using tools.
    """
    print("--- Node: call_gemini ---")
    current_messages = state["messages"]


    # Convert LangChain messages to Gemini's expected format for `contents`
    gemini_messages = []
    for msg in current_messages:
        if isinstance(msg, HumanMessage):
            gemini_messages.append({"role": "user", "parts": [{"text": msg.content}]})
    
        elif isinstance(msg, AIMessage) and msg.tool_calls:
            # exactly one branch for tool calls
            gemini_messages.append({
                "role": "model",
                "parts": [
                    {"function_call": {"name": tc["name"], "args": tc["args"]}}
                    for tc in msg.tool_calls
                ]
            })
    
        elif isinstance(msg, AIMessage):
            gemini_messages.append({"role": "model", "parts": [{"text": msg.content}]})
    
        elif isinstance(msg, ToolMessage):
            gemini_messages.append({
                "role": "model",
                "parts": [{
                    "function_response": {
                        "name": msg.name,
                        "response": json.loads(msg.content)
                    }
                }]
            })

            # gemini_messages.append({
            #         "role": "model",
            #         "parts": [{
            #         "function_response": {
            #             "name": msg.name,
            #             "response": json.loads(msg.content) if isinstance(msg.content, str) else msg.content
            #         }
            #     }]
            # })
    # x=1
    # while x: 
    try:
        model = GenerativeModel("gemini-2.5-flash", tools=tools)
        # chat = model.start_chat(history=gemini_messages[:-1])
        # Convert any LangChain messages to Gemini's expected dict format
        history_dicts = [
            {
                "role": m["role"],
                "parts": [
                    {"text": p.text} if hasattr(p, "text") else p
                    for p in m["parts"]
                ],
            }
            for m in gemini_messages[:-1]
        ]
        chat = model.start_chat(history=history_dicts)
        response = chat.send_message(gemini_messages[-1]["parts"])
        gemini_response_parts = response.parts
        print("Gemini Raw Response Parts:", gemini_response_parts)
        if gemini_response_parts and gemini_response_parts[0].function_call:
            fc = gemini_response_parts[0].function_call
            return {"messages": state["messages"] + [
                AIMessage(
                    content="",
                    tool_calls=[{"id": fc.id, "name": fc.name, "args": fc.args}]
                )
            ]}
        else:
            return {"messages": state["messages"] + [AIMessage(content=response.text)]}
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        x=int(input("Press 1 to continue or 0 to stop: "))
        print(chat)
        # print(response)
        # print(gemini_response_parts)
        # if(x==0):
        return {"messages": state["messages"] + [AIMessage(content=f"Error: {e}. Please try again.")]}


def execute_tool(state: ChatState) -> dict:
    """
    Executes the tool call requested by Gemini.
    """
    print("--- Node: execute_tool ---")
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # Assuming only one tool call for simplicity; parallel tool calls are possible
        tool_call = last_message.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        # Dynamically call the function based on its name
        if tool_name == "get_calendar_events":
            tool_result = get_calendar_events(**tool_args)
        elif tool_name == "delete_calendar_event":
            tool_result = delete_calendar_event(**tool_args)
        elif tool_name == "add_calendar_event":
            tool_result = add_calendar_event(**tool_args)
        elif tool_name == "get_current_datetime":
            tool_result = get_current_datetime(**tool_args)
        else:
            tool_result = json.dumps({"error": f"Unknown tool: {tool_name}"})
        
        # Return a ToolMessage with the result. LangGraph will update the state.
        print("tool call ---> ",tool_call)
        print("prinnnnttttt ---> ",tool_call.get("id","tool_call_0"))
        return {"messages": state["messages"] + [
            ToolMessage(
                name=tool_name,
                content=tool_result,
                tool_call_id=tool_call.get("id", "tool_call_0")
            )
        ]}
    else:
        # This node should only be reached if there's a tool call to execute
        print("Error: execute_tool called without a valid tool_call in the last message.")
        return {"messages": state["messages"] + [AIMessage(content="Internal error: No tool call to execute.")]}


# --- Graph Definition ---
graph = StateGraph(ChatState)

graph.add_node("call_gemini", call_gemini)
graph.add_node("execute_tool", execute_tool)

graph.set_entry_point("call_gemini")

# Define conditional edges from "call_gemini"
# After Gemini's response, check if it's a tool call or a regular text response.
graph.add_conditional_edges(
    "call_gemini",
    # This lambda function checks the last message in the state
    lambda state: "tool_call" if isinstance(state["messages"][-1], AIMessage) and state["messages"][-1].tool_calls else "text_response",
    {
        "tool_call": "execute_tool", # If Gemini wants to call a tool, go to execute_tool node
        "text_response": END,       # If Gemini provides a direct text response, end the turn
    }
)

# After executing a tool, always loop back to call_gemini to let it process the tool's result
# and generate a final user-facing response.
graph.add_edge("execute_tool", "call_gemini")

app = graph.compile()



fast_app = FastAPI()

class ChatRequest(BaseModel):
    text: str


initial_state_get_events = ChatState(messages=[])


@fast_app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    # Replace with your actual logic or AI call
    print("\n--- Running the graph for 'get_calendar_events' ---")
    initial_state_get_events["messages"].append(HumanMessage(content=req.text))
    final_state = app.invoke(initial_state_get_events)
    initial_state_get_events["messages"] = final_state["messages"]
    print("\n--- Final State after 'get_calendar_events' ---")
    print(json.dumps(final_state, indent=2, default=str))
    reply = final_state["messages"][-1].content
    return {"reply": reply}


@fast_app.get("/")
def root_status():
    return {"status": "Backend is running"}
