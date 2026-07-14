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
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

# Load the .env that sits next to this file, regardless of the working
# directory the MCP client launches us from. override=True so the .env is the
# source of truth even if a stale/empty value was injected into the environment.
load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

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


# ---------------------------------------------------------------------------
# Users, workflows & campaigns
# ---------------------------------------------------------------------------


@mcp.tool
def list_users() -> dict:
    """List the users (team members) of the location."""
    return _request("GET", "/users/", params={"locationId": _location_id()})


@mcp.tool
def list_workflows() -> dict:
    """List the location's workflows (automations). Workflow IDs are needed to
    add or remove contacts from a workflow."""
    return _request("GET", "/workflows/", params={"locationId": _location_id()})


@mcp.tool
def add_contact_to_workflow(
    contact_id: str, workflow_id: str, event_start_time: str | None = None
) -> dict:
    """Add a contact to a workflow (starts the automation for them).

    Args:
        contact_id: The contact to enroll.
        workflow_id: The workflow to enroll them in (see list_workflows).
        event_start_time: Optional start time in ISO 8601 with offset
            (e.g. 2026-07-15T10:00:00-05:00).
    """
    return _request(
        "POST",
        f"/contacts/{contact_id}/workflow/{workflow_id}",
        json={"eventStartTime": event_start_time},
    )


@mcp.tool
def remove_contact_from_workflow(contact_id: str, workflow_id: str) -> dict:
    """Remove a contact from a workflow (stops the automation for them)."""
    return _request("DELETE", f"/contacts/{contact_id}/workflow/{workflow_id}")


@mcp.tool
def list_campaigns(status: str | None = None) -> dict:
    """List the location's campaigns. Optionally filter by status
    ("published" or "draft")."""
    return _request(
        "GET", "/campaigns/", params={"locationId": _location_id(), "status": status}
    )


@mcp.tool
def add_contact_to_campaign(contact_id: str, campaign_id: str) -> dict:
    """Add a contact to a campaign."""
    return _request("POST", f"/contacts/{contact_id}/campaigns/{campaign_id}")


@mcp.tool
def remove_contact_from_campaign(contact_id: str, campaign_id: str) -> dict:
    """Remove a contact from a campaign."""
    return _request("DELETE", f"/contacts/{contact_id}/campaigns/{campaign_id}")


# ---------------------------------------------------------------------------
# Forms & surveys
# ---------------------------------------------------------------------------


@mcp.tool
def list_forms(limit: int = 20, skip: int = 0) -> dict:
    """List the location's forms."""
    return _request(
        "GET",
        "/forms/",
        params={"locationId": _location_id(), "limit": limit, "skip": skip},
    )


@mcp.tool
def list_form_submissions(
    form_id: str | None = None,
    query: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
    page: int = 1,
) -> dict:
    """List form submissions in the location.

    Args:
        form_id: Filter to one form.
        query: Free-text filter on contact name, email, or phone.
        start_at: Range start date (YYYY-MM-DD).
        end_at: Range end date (YYYY-MM-DD).
        limit: Results per page.
        page: Page number.
    """
    return _request(
        "GET",
        "/forms/submissions",
        params={
            "locationId": _location_id(),
            "formId": form_id,
            "q": query,
            "startAt": start_at,
            "endAt": end_at,
            "limit": limit,
            "page": page,
        },
    )


@mcp.tool
def list_surveys(limit: int = 20, skip: int = 0) -> dict:
    """List the location's surveys."""
    return _request(
        "GET",
        "/surveys/",
        params={"locationId": _location_id(), "limit": limit, "skip": skip},
    )


@mcp.tool
def list_survey_submissions(
    survey_id: str | None = None, limit: int = 20, page: int = 1
) -> dict:
    """List survey submissions in the location, optionally filtered to one
    survey."""
    return _request(
        "GET",
        "/surveys/submissions",
        params={
            "locationId": _location_id(),
            "surveyId": survey_id,
            "limit": limit,
            "page": page,
        },
    )


# ---------------------------------------------------------------------------
# Funnels, trigger links & media
# ---------------------------------------------------------------------------


@mcp.tool
def list_funnels(limit: int = 20, offset: int = 0) -> dict:
    """List the location's funnels."""
    return _request(
        "GET",
        "/funnels/funnel/list",
        params={"locationId": _location_id(), "limit": limit, "offset": offset},
    )


@mcp.tool
def list_funnel_pages(funnel_id: str, limit: int = 20, offset: int = 0) -> dict:
    """List the pages of a funnel."""
    return _request(
        "GET",
        "/funnels/page",
        params={
            "locationId": _location_id(),
            "funnelId": funnel_id,
            "limit": limit,
            "offset": offset,
        },
    )


@mcp.tool
def list_trigger_links() -> dict:
    """List the location's trigger links."""
    return _request("GET", "/links/", params={"locationId": _location_id()})


@mcp.tool
def create_trigger_link(name: str, redirect_to: str) -> dict:
    """Create a trigger link that redirects to the given URL."""
    return _request(
        "POST",
        "/links/",
        json={
            "locationId": _location_id(),
            "name": name,
            "redirectTo": redirect_to,
        },
    )


@mcp.tool
def list_media_files(
    limit: int = 20,
    offset: int = 0,
    query: str | None = None,
) -> dict:
    """List files in the location's media library."""
    return _request(
        "GET",
        "/medias/files",
        params={
            "altType": "location",
            "altId": _location_id(),
            "sortBy": "createdAt",
            "sortOrder": "desc",
            "limit": limit,
            "offset": offset,
            "query": query,
        },
    )


# ---------------------------------------------------------------------------
# Custom values & businesses
# ---------------------------------------------------------------------------


@mcp.tool
def list_custom_values() -> dict:
    """List the location's custom values (merge-field style key/value pairs
    usable across the account)."""
    return _request("GET", f"/locations/{_location_id()}/customValues")


@mcp.tool
def create_custom_value(name: str, value: str) -> dict:
    """Create a custom value in the location."""
    return _request(
        "POST",
        f"/locations/{_location_id()}/customValues",
        json={"name": name, "value": value},
    )


@mcp.tool
def update_custom_value(custom_value_id: str, name: str, value: str) -> dict:
    """Update an existing custom value by ID."""
    return _request(
        "PUT",
        f"/locations/{_location_id()}/customValues/{custom_value_id}",
        json={"name": name, "value": value},
    )


@mcp.tool
def list_businesses() -> dict:
    """List businesses (companies) in the location."""
    return _request("GET", "/businesses/", params={"locationId": _location_id()})


# ---------------------------------------------------------------------------
# Products, invoices & payments
# ---------------------------------------------------------------------------


@mcp.tool
def list_products(limit: int = 20, offset: int = 0, query: str | None = None) -> dict:
    """List the location's products."""
    return _request(
        "GET",
        "/products/",
        params={
            "locationId": _location_id(),
            "limit": limit,
            "offset": offset,
            "search": query,
        },
    )


@mcp.tool
def get_product(product_id: str) -> dict:
    """Get a product by ID, including its details."""
    return _request(
        "GET", f"/products/{product_id}", params={"locationId": _location_id()}
    )


@mcp.tool
def list_product_prices(product_id: str, limit: int = 20, offset: int = 0) -> dict:
    """List the prices attached to a product."""
    return _request(
        "GET",
        f"/products/{product_id}/price",
        params={"locationId": _location_id(), "limit": limit, "offset": offset},
    )


@mcp.tool
def list_invoices(
    status: str | None = None, limit: int = 20, offset: int = 0
) -> dict:
    """List the location's invoices. Optionally filter by status (e.g.
    "draft", "sent", "paid", "void", "partially_paid")."""
    return _request(
        "GET",
        "/invoices/",
        params={
            "altId": _location_id(),
            "altType": "location",
            "status": status,
            "limit": limit,
            "offset": offset,
        },
    )


@mcp.tool
def get_invoice(invoice_id: str) -> dict:
    """Get an invoice by ID."""
    return _request(
        "GET",
        f"/invoices/{invoice_id}",
        params={"altId": _location_id(), "altType": "location"},
    )


@mcp.tool
def list_payment_orders(limit: int = 20, offset: int = 0) -> dict:
    """List payment orders in the location."""
    return _request(
        "GET",
        "/payments/orders",
        params={
            "altId": _location_id(),
            "altType": "location",
            "limit": limit,
            "offset": offset,
        },
    )


@mcp.tool
def list_payment_transactions(limit: int = 20, offset: int = 0) -> dict:
    """List payment transactions in the location."""
    return _request(
        "GET",
        "/payments/transactions",
        params={
            "altId": _location_id(),
            "altType": "location",
            "limit": limit,
            "offset": offset,
        },
    )


@mcp.tool
def list_payment_subscriptions(limit: int = 20, offset: int = 0) -> dict:
    """List payment subscriptions in the location."""
    return _request(
        "GET",
        "/payments/subscriptions",
        params={
            "altId": _location_id(),
            "altType": "location",
            "limit": limit,
            "offset": offset,
        },
    )


# ---------------------------------------------------------------------------
# Extra calendar & contact helpers
# ---------------------------------------------------------------------------


@mcp.tool
def list_calendar_groups() -> dict:
    """List the location's calendar groups."""
    return _request(
        "GET", "/calendars/groups", params={"locationId": _location_id()}
    )


@mcp.tool
def list_contact_appointments(contact_id: str) -> dict:
    """List all appointments booked for a contact."""
    return _request("GET", f"/contacts/{contact_id}/appointments")


# ---------------------------------------------------------------------------
# Social Planner (social media posting)
# ---------------------------------------------------------------------------


@mcp.tool
def list_social_accounts() -> dict:
    """List the social media accounts and groups connected to the location's
    Social Planner (Facebook, Instagram, LinkedIn, X/Twitter, TikTok, Google
    Business Profile, etc.). Account IDs are needed to create posts."""
    return _request(
        "GET", f"/social-media-posting/{_location_id()}/accounts"
    )


@mcp.tool
def list_social_posts(
    post_type: str = "all",
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 10,
    skip: int = 0,
) -> dict:
    """List Social Planner posts in a date range.

    Args:
        post_type: Filter: "all", "recent", "upcoming", "draft", "failed",
            "in_review", "notes", "in_progress", or "deleted".
        from_date: Range start in ISO 8601 (e.g. 2026-07-01T00:00:00Z).
            Defaults to 30 days ago.
        to_date: Range end in ISO 8601. Defaults to 30 days from now.
        limit: Results per page.
        skip: Results to skip (pagination).
    """
    from datetime import datetime, timedelta, timezone as tz

    now = datetime.now(tz.utc)
    fmt = "%Y-%m-%dT%H:%M:%S.000Z"
    return _request(
        "POST",
        f"/social-media-posting/{_location_id()}/posts/list",
        json={
            "type": post_type,
            "accounts": "",
            "skip": str(skip),
            "limit": str(limit),
            "fromDate": from_date or (now - timedelta(days=30)).strftime(fmt),
            "toDate": to_date or (now + timedelta(days=30)).strftime(fmt),
            "includeUsers": "true",
        },
    )


@mcp.tool
def get_social_post(post_id: str) -> dict:
    """Get a single Social Planner post by ID."""
    return _request(
        "GET", f"/social-media-posting/{_location_id()}/posts/{post_id}"
    )


@mcp.tool
def create_social_post(
    account_ids: list[str],
    summary: str,
    status: str = "draft",
    schedule_date: str | None = None,
    media_urls: list[str] | None = None,
    follow_up_comment: str | None = None,
) -> dict:
    """Create a Social Planner post on one or more connected accounts. This
    can publish real posts — confirm content before calling.

    Args:
        account_ids: Social account IDs to post to (see list_social_accounts).
        summary: The post text/caption.
        status: "draft" (safe default), "scheduled" (requires schedule_date),
            or "published" (posts immediately).
        schedule_date: When to publish, ISO 8601 (e.g. 2026-07-15T10:00:00Z).
            Required when status is "scheduled".
        media_urls: Public URLs of images/videos to attach.
        follow_up_comment: Optional first comment to add after publishing.
    """
    body: dict[str, Any] = {
        "accountIds": account_ids,
        "summary": summary,
        "status": status,
        "type": "post",
        "userId": None,
        "scheduleDate": schedule_date,
        "followUpComment": follow_up_comment,
    }
    if media_urls:
        body["media"] = [{"url": url} for url in media_urls]
    return _request(
        "POST", f"/social-media-posting/{_location_id()}/posts", json=body
    )


@mcp.tool
def delete_social_post(post_id: str) -> dict:
    """Delete a Social Planner post by ID."""
    return _request(
        "DELETE", f"/social-media-posting/{_location_id()}/posts/{post_id}"
    )


# ---------------------------------------------------------------------------
# Universal escape hatch — any GHL API v2 endpoint
# ---------------------------------------------------------------------------


@mcp.tool
def ghl_api_request(
    method: str,
    path: str,
    query_params: dict | None = None,
    body: dict | None = None,
    api_version: str = DEFAULT_API_VERSION,
) -> dict:
    """Call ANY GoHighLevel API v2 endpoint directly. Use this for any GHL
    action that doesn't have a dedicated tool — it can reach every endpoint
    the Private Integration Token's scopes allow (blogs, courses, social
    planner, email templates, snapshots, estimates, etc.). API reference:
    https://highlevel.stoplight.io/docs/integrations

    Args:
        method: HTTP method: "GET", "POST", "PUT", "PATCH", or "DELETE".
        path: Endpoint path starting with "/", e.g. "/contacts/" or
            "/social-media-posting/{locationId}/posts/list". The literal
            placeholder "{locationId}" is replaced with the configured
            location ID.
        query_params: Query string parameters. Many GHL list endpoints
            require "locationId" (or "altId" + "altType": "location") — the
            configured location ID is auto-filled for the common
            "locationId"/"altId" keys if you pass the literal value
            "{locationId}".
        body: JSON request body for POST/PUT/PATCH.
        api_version: The dated Version header. Default "2021-07-28";
            conversation endpoints need "2021-04-15".
    """
    location_id = _location_id()
    path = path.replace("{locationId}", location_id)

    def _fill(d: dict | None) -> dict | None:
        if not d:
            return d
        return {
            k: (location_id if v == "{locationId}" else v) for k, v in d.items()
        }

    return _request(
        method.upper(),
        path,
        params=_fill(query_params),
        json=_fill(body),
        api_version=api_version,
    )


if __name__ == "__main__":
    mcp.run()
