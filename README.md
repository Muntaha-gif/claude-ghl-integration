# GoHighLevel MCP Server

A local MCP server (Python, [FastMCP](https://gofastmcp.com)) that wraps the
[GoHighLevel API v2](https://highlevel.stoplight.io/docs/integrations). It
authenticates with a **Private Integration Token** and scopes every request to
a single sub-account (location).

## Tools

| Area | Tools |
|---|---|
| Location | `get_location`, `list_tags`, `list_custom_fields`, `list_custom_values`, `create_custom_value`, `update_custom_value`, `list_businesses` |
| Contacts | `search_contacts`, `get_contact`, `create_contact`, `update_contact`, `delete_contact`, `add_contact_tags`, `remove_contact_tags` |
| Tasks & notes | `list_contact_tasks`, `create_contact_task`, `list_contact_notes`, `create_contact_note` |
| Conversations | `search_conversations`, `get_conversation_messages`, `send_message` (SMS, Email, WhatsApp, IG, FB, Live Chat) |
| Opportunities | `list_pipelines`, `search_opportunities`, `get_opportunity`, `create_opportunity`, `update_opportunity` |
| Calendars | `list_calendars`, `list_calendar_groups`, `get_free_slots`, `list_calendar_events`, `create_appointment`, `list_contact_appointments` |
| Users & automations | `list_users`, `list_workflows`, `add_contact_to_workflow`, `remove_contact_from_workflow`, `list_campaigns`, `add_contact_to_campaign`, `remove_contact_from_campaign` |
| Forms & surveys | `list_forms`, `list_form_submissions`, `list_surveys`, `list_survey_submissions` |
| Funnels & links | `list_funnels`, `list_funnel_pages`, `list_trigger_links`, `create_trigger_link`, `list_media_files` |
| Products & payments | `list_products`, `get_product`, `list_product_prices`, `list_invoices`, `get_invoice`, `list_payment_orders`, `list_payment_transactions`, `list_payment_subscriptions` |
| Social Planner | `list_social_accounts`, `list_social_posts`, `get_social_post`, `create_social_post` (draft/scheduled/published), `delete_social_post` |
| **Everything else** | `ghl_api_request` — a universal tool that can call **any** GHL API v2 endpoint your PIT scopes allow (blogs, courses, social planner, email templates, estimates, snapshots, …) |

## 1. Get your GHL credentials

1. **Private Integration Token (`GHL_PIT`)** — in your GHL sub-account go to
   **Settings → Private Integrations → Create new integration**. Grant the
   scopes you want the server to use (contacts, conversations,
   conversations/message, opportunities, locations, locations/tags,
   locations/customFields, calendars, calendars/events). Copy the token — it
   starts with `pit-`.
2. **Location ID (`GHL_LOCATION_ID`)** — in the same sub-account go to
   **Settings → Business Profile**, or copy it from the URL:
   `app.gohighlevel.com/v2/location/<LOCATION_ID>/...`

## 2. Install

```bash
git clone https://github.com/Muntaha-gif/claude-ghl-integration.git
cd claude-ghl-integration
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create your env file:

```bash
cp .env.example .env
# then edit .env and paste in your real GHL_PIT and GHL_LOCATION_ID
```

The server loads `.env` automatically (via `python-dotenv`), so environment
variables passed by the MCP client and a local `.env` file both work.

Never commit `.env` — it's already in `.gitignore`.

## 3. Register with Claude

### Claude Code (CLI)

From the repo directory:

```bash
claude mcp add gohighlevel \
  --env GHL_PIT=pit-xxxxxxxx \
  --env GHL_LOCATION_ID=your_location_id \
  -- /absolute/path/to/claude-ghl-integration/.venv/bin/python \
     /absolute/path/to/claude-ghl-integration/server.py
```

(If you filled in `.env`, you can omit the two `--env` flags.)

Add `--scope project` to share the registration with your team via a checked-in
`.mcp.json`, or `--scope user` to make it available in all your projects.
Verify with:

```bash
claude mcp list
```

Then in a Claude Code session, ask things like *"search GHL for contacts named
Smith"* or *"list my pipelines"*.

### Claude Desktop

Edit your config file:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gohighlevel": {
      "command": "/absolute/path/to/claude-ghl-integration/.venv/bin/python",
      "args": ["/absolute/path/to/claude-ghl-integration/server.py"],
      "env": {
        "GHL_PIT": "pit-xxxxxxxx",
        "GHL_LOCATION_ID": "your_location_id"
      }
    }
  }
}
```

On Windows the `command` is
`C:\\path\\to\\claude-ghl-integration\\.venv\\Scripts\\python.exe`.
Restart Claude Desktop; the tools appear under the 🔌 connectors menu.

## 4. Test it standalone (optional)

```bash
python server.py            # starts on stdio; Ctrl+C to stop
fastmcp dev server.py       # opens the MCP Inspector UI for interactive testing
```

## Notes

- Base URL is `https://services.leadconnectorhq.com`; the server sends the
  required `Version` header (`2021-07-28`, and `2021-04-15` for conversation
  endpoints).
- `send_message` sends real SMS/emails and `delete_contact` is irreversible —
  Claude will ask before using them, but scope your PIT to only what you need.
- API errors are surfaced to Claude verbatim (status code + response body), so
  scope/permission problems are easy to diagnose.
