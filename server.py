"""GoHighLevel API v2 MCP server.

A local MCP server (FastMCP) that wraps the GoHighLevel API v2
(https://highlevel.stoplight.io/docs/integrations). It authenticates with a
Private Integration Token (PIT) and scopes requests to a single sub-account
(location).

Required environment variables:
    GHL_PIT          Private Integration Token (Settings > Private Integrations)
    GHL_LOCATION_ID  The sub-account / location ID the server operates on
"""

import os
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

BASE_URL = "https://services.leadconnectorhq.com"

# GHL v2 pins endpoint groups to dated API versions via the `Version` header.
DEFAULT_API_VERSION = "2021-07-28"
CONVERSATIONS_API_VERSION = "2021-04-15"

mcp = FastMCP(
    "gohighlevel",
    instructions=(
        "Tools for the GoHighLevel (GHL) API v2, scoped to a single location "
        "(sub-account). Covers contacts, tags, tasks, notes, conversations, "
        "opportunities, pipelines, calendars, and appointments."
    ),
)


def _pit() -> str:
    token = os.environ.get("GHL_PIT")
    if not token:
        raise RuntimeError(
            "GHL_PIT environment variable is not set. Create a Private "
            "Integration Token in GHL under Settings > Private Integrations."
        )
    return token


def _location_id() -> str:
    location_id = os.environ.get("GHL_LOCATION_ID")
    if not location_id:
        raise RuntimeError(
            "GHL_LOCATION_ID environment variable is not set. Find it in GHL "
            "under Settings > Business Profile."
        )
    return location_id


def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json: dict[str, Any] | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {_pit()}",
        "Version": api_version,
        "Accept": "application/json",
    }
    if params:
        params = {k: v for k, v in params.items() if v is not None}
    if json:
        json = {k: v for k, v in json.items() if v is not None}
    with httpx.Client(base_url=BASE_URL, headers=headers, timeout=30.0) as client:
        response = client.request(method, path, params=params, json=json)
    if response.is_error:
        raise RuntimeError(
            f"GHL API error {response.status_code} on {method} {path}: "
            f"{response.text}"
        )
    if not response.content:
        return {"success": True}
    return response.json()


# ---------------------------------------------------------------------------
# Location
# ---------------------------------------------------------------------------


@mcp.tool
def get_location() -> dict:
    """Get details of the configured GHL location (sub-account): name,
    address, timezone, business info, and settings."""
    return _request("GET", f"/locations/{_location_id()}")


@mcp.tool
def list_tags() -> dict:
    """List all contact tags defined in the location."""
    return _request("GET", f"/locations/{_location_id()}/tags")


@mcp.tool
def list_custom_fields() -> dict:
    """List the location's custom field definitions (useful for reading or
    setting customFields on contacts and opportunities)."""
    return _request("GET", f"/locations/{_location_id()}/customFields")


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------


@mcp.tool
def search_contacts(query: str | None = None, limit: int = 20) -> dict:
    """Search contacts in the location.

    Args:
        query: Free-text search across name, email, and phone. Omit to list
            the most recent contacts.
        limit: Maximum number of contacts to return (1-100).
    """
    return _request(
        "GET",
        "/contacts/",
        params={"locationId": _location_id(), "query": query, "limit": limit},
    )


@mcp.tool
def get_contact(contact_id: str) -> dict:
    """Get a single contact by ID, including tags, custom fields, and
    attribution."""
    return _request("GET", f"/contacts/{contact_id}")


@mcp.tool
def create_contact(
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    tags: list[str] | None = None,
    source: str | None = None,
    custom_fields: list[dict] | None = None,
) -> dict:
    """Create a contact in the location.

    Args:
        first_name: Contact first name.
        last_name: Contact last name.
        email: Email address.
        phone: Phone number in E.164 format (e.g. +15551234567).
        tags: Tags to apply on creation.
        source: Attribution source label (e.g. "claude-mcp").
        custom_fields: Custom field values, each like
            {"id": "<fieldId>", "value": "..."}.
    """
    return _request(
        "POST",
        "/contacts/",
        json={
            "locationId": _location_id(),
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "phone": phone,
            "tags": tags,
            "source": source,
            "customFields": custom_fields,
        },
    )


@mcp.tool
def update_contact(
    contact_id: str,
    first_name: str | None = None,
    last_name: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    tags: list[str] | None = None,
    custom_fields: list[dict] | None = None,
) -> dict:
    """Update fields on an existing contact. Only the provided fields are
    changed. Note: `tags` replaces the contact's full tag list — use
    add_contact_tags / remove_contact_tags for incremental changes."""
    return _request(
        "PUT",
        f"/contacts/{contact_id}",
        json={
            "firstName": first_name,
            "lastName": last_name,
            "email": email,
            "phone": phone,
            "tags": tags,
            "customFields": custom_fields,
        },
    )


@mcp.tool
def delete_contact(contact_id: str) -> dict:
    """Permanently delete a contact by ID. This cannot be undone."""
    return _request("DELETE", f"/contacts/{contact_id}")


@mcp.tool
def add_contact_tags(contact_id: str, tags: list[str]) -> dict:
    """Add tags to a contact (existing tags are kept)."""
    return _request("POST", f"/contacts/{contact_id}/tags", json={"tags": tags})


@mcp.tool
def remove_contact_tags(contact_id: str, tags: list[str]) -> dict:
    """Remove specific tags from a contact."""
    return _request("DELETE", f"/contacts/{contact_id}/tags", json={"tags": tags})


@mcp.tool
def list_contact_tasks(contact_id: str) -> dict:
    """List tasks attached to a contact."""
    return _request("GET", f"/contacts/{contact_id}/tasks")


@mcp.tool
def create_contact_task(
    contact_id: str,
    title: str,
    due_date: str,
    body: str | None = None,
    assigned_to: str | None = None,
) -> dict:
    """Create a task on a contact.

    Args:
        contact_id: The contact to attach the task to.
        title: Task title.
        due_date: Due date/time in ISO 8601 (e.g. 2026-07-15T10:00:00Z).
        body: Optional task description.
        assigned_to: Optional user ID to assign the task to.
    """
    return _request(
        "POST",
        f"/contacts/{contact_id}/tasks",
        json={
            "title": title,
            "dueDate": due_date,
            "body": body,
            "assignedTo": assigned_to,
            "completed": False,
        },
    )


@mcp.tool
def list_contact_notes(contact_id: str) -> dict:
    """List notes on a contact."""
    return _request("GET", f"/contacts/{contact_id}/notes")


@mcp.tool
def create_contact_note(contact_id: str, body: str) -> dict:
    """Add a note to a contact."""
    return _request("POST", f"/contacts/{contact_id}/notes", json={"body": body})


# ---------------------------------------------------------------------------
# Conversations & messaging
# ---------------------------------------------------------------------------


@mcp.tool
def search_conversations(
    contact_id: str | None = None,
    query: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> dict:
    """Search conversations in the location.

    Args:
        contact_id: Filter to a single contact's conversations.
        query: Free-text search.
        status: Filter by status: "all", "read", "unread", or "starred".
        limit: Maximum results to return.
    """
    return _request(
        "GET",
        "/conversations/search",
        params={
            "locationId": _location_id(),
            "contactId": contact_id,
            "query": query,
            "status": status,
            "limit": limit,
        },
        api_version=CONVERSATIONS_API_VERSION,
    )


@mcp.tool
def get_conversation_messages(conversation_id: str, limit: int = 20) -> dict:
    """Get the messages in a conversation, newest first."""
    return _request(
        "GET",
        f"/conversations/{conversation_id}/messages",
        params={"limit": limit},
        api_version=CONVERSATIONS_API_VERSION,
    )


@mcp.tool
def send_message(
    contact_id: str,
    message_type: str,
    message: str,
    subject: str | None = None,
) -> dict:
    """Send an outbound message to a contact. This sends a real message —
    confirm content before calling.

    Args:
        contact_id: The recipient contact ID.
        message_type: Channel to send on: "SMS", "Email", "WhatsApp", "IG",
            "FB", or "Live_Chat".
        message: The message body (used as HTML body for Email).
        subject: Email subject (only used when message_type is "Email").
    """
    body: dict[str, Any] = {
        "type": message_type,
        "contactId": contact_id,
        "message": message,
    }
    if message_type == "Email":
        body["html"] = message
        body["subject"] = subject
    return _request(
        "POST",
        "/conversations/messages",
        json=body,
        api_version=CONVERSATIONS_API_VERSION,
    )


# ---------------------------------------------------------------------------
# Opportunities & pipelines
# ---------------------------------------------------------------------------


@mcp.tool
def list_pipelines() -> dict:
    """List the location's opportunity pipelines and their stages (stage IDs
    are needed to create or move opportunities)."""
    return _request(
        "GET", "/opportunities/pipelines", params={"locationId": _location_id()}
    )


@mcp.tool
def search_opportunities(
    pipeline_id: str | None = None,
    contact_id: str | None = None,
    status: str | None = None,
    query: str | None = None,
    limit: int = 20,
) -> dict:
    """Search opportunities in the location.

    Args:
        pipeline_id: Filter by pipeline.
        contact_id: Filter by contact.
        status: Filter by status: "open", "won", "lost", or "abandoned".
        query: Free-text search on opportunity name.
        limit: Maximum results to return.
    """
    return _request(
        "GET",
        "/opportunities/search",
        params={
            "location_id": _location_id(),
            "pipeline_id": pipeline_id,
            "contact_id": contact_id,
            "status": status,
            "q": query,
            "limit": limit,
        },
    )


@mcp.tool
def get_opportunity(opportunity_id: str) -> dict:
    """Get a single opportunity by ID."""
    return _request("GET", f"/opportunities/{opportunity_id}")


@mcp.tool
def create_opportunity(
    name: str,
    pipeline_id: str,
    stage_id: str,
    contact_id: str,
    monetary_value: float | None = None,
    status: str = "open",
) -> dict:
    """Create an opportunity in a pipeline.

    Args:
        name: Opportunity name.
        pipeline_id: Target pipeline ID (see list_pipelines).
        stage_id: Target stage ID within the pipeline.
        contact_id: The contact the opportunity belongs to.
        monetary_value: Deal value.
        status: "open", "won", "lost", or "abandoned".
    """
    return _request(
        "POST",
        "/opportunities/",
        json={
            "locationId": _location_id(),
            "name": name,
            "pipelineId": pipeline_id,
            "pipelineStageId": stage_id,
            "contactId": contact_id,
            "monetaryValue": monetary_value,
            "status": status,
        },
    )


@mcp.tool
def update_opportunity(
    opportunity_id: str,
    name: str | None = None,
    stage_id: str | None = None,
    monetary_value: float | None = None,
    status: str | None = None,
) -> dict:
    """Update an opportunity: rename it, move it to another stage, change its
    value, or set its status ("open", "won", "lost", "abandoned")."""
    return _request(
        "PUT",
        f"/opportunities/{opportunity_id}",
        json={
            "name": name,
            "pipelineStageId": stage_id,
            "monetaryValue": monetary_value,
            "status": status,
        },
    )


# ---------------------------------------------------------------------------
# Calendars & appointments
# ---------------------------------------------------------------------------


@mcp.tool
def list_calendars() -> dict:
    """List the location's calendars."""
    return _request("GET", "/calendars/", params={"locationId": _location_id()})


@mcp.tool
def get_free_slots(
    calendar_id: str,
    start_date_ms: int,
    end_date_ms: int,
    timezone: str | None = None,
) -> dict:
    """Get open booking slots on a calendar.

    Args:
        calendar_id: The calendar to query.
        start_date_ms: Range start as epoch milliseconds.
        end_date_ms: Range end as epoch milliseconds.
        timezone: IANA timezone for the returned slots (e.g. America/Chicago).
    """
    return _request(
        "GET",
        f"/calendars/{calendar_id}/free-slots",
        params={
            "startDate": start_date_ms,
            "endDate": end_date_ms,
            "timezone": timezone,
        },
    )


@mcp.tool
def list_calendar_events(
    start_time: str,
    end_time: str,
    calendar_id: str | None = None,
) -> dict:
    """List booked events/appointments in a time range.

    Args:
        start_time: Range start in ISO 8601 (e.g. 2026-07-11T00:00:00Z).
        end_time: Range end in ISO 8601.
        calendar_id: Optionally restrict to one calendar.
    """
    return _request(
        "GET",
        "/calendars/events",
        params={
            "locationId": _location_id(),
            "startTime": start_time,
            "endTime": end_time,
            "calendarId": calendar_id,
        },
    )


@mcp.tool
def create_appointment(
    calendar_id: str,
    contact_id: str,
    start_time: str,
    end_time: str | None = None,
    title: str | None = None,
) -> dict:
    """Book an appointment on a calendar for a contact.

    Args:
        calendar_id: The calendar to book on.
        contact_id: The contact the appointment is for.
        start_time: Start in ISO 8601 with offset
            (e.g. 2026-07-15T10:00:00-05:00).
        end_time: End in ISO 8601; omit to use the calendar's slot duration.
        title: Appointment title.
    """
    return _request(
        "POST",
        "/calendars/events/appointments",
        json={
            "calendarId": calendar_id,
            "locationId": _location_id(),
            "contactId": contact_id,
            "startTime": start_time,
            "endTime": end_time,
            "title": title,
        },
    )


if __name__ == "__main__":
    mcp.run()
