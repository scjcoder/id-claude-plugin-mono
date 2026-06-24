---
name: install-team-summary
description: Weekday morning install team summary — Gmail + HubSpot Installation Team pipeline, delivered as image to Slack
---

**Lookback window:** Check today's day of week. If today is **Monday**, use a **3-day** lookback. All other weekdays use a **2-day** lookback. Apply the correct window to every step below and all output labels.

Run the install team summary for the past N days (N = 3 on Monday, 2 otherwise).

Search Gmail and HubSpot simultaneously:

**Gmail:** Search threads involving install@insidedesk.com using the correct lookback:
- Monday: `newer_than:3d (to:install@insidedesk.com OR cc:install@insidedesk.com OR from:install@insidedesk.com)`
- Other days: `newer_than:2d (to:install@insidedesk.com OR cc:install@insidedesk.com OR from:install@insidedesk.com)`
Capture subject, sender, snippet, and date for each thread.

**HubSpot:** Search tickets with these exact filters (do NOT re-query pipeline IDs — they are hardcoded):
- Pipeline: `66471460` (Installation Team)
- Exclude Closed stage: `129440439`
- Properties: subject, hs_ticket_id, hs_pipeline_stage, hs_lastmodifieddate, createdate, hubspot_owner_id, content
- Sort: hs_lastmodifieddate descending, limit 50
- After fetching, filter in memory to tickets modified within the past N days (3 on Monday, 2 otherwise).

**Stage label map:**
- 133962530 → New
- 129495447 → Sync Issues
- 133774246 → Add Loc / Reactivate
- 159888918 → Escalated
- 133988666 → Support / Investigation
- 244905906 → Remit
- 133962531 → Account Updates

**Cross-reference:** Group results by client name. Parse client from ticket subject using the format `Client - Issue - Detail` (text before first hyphen). Merge Gmail threads and HubSpot tickets for the same client into one row. Gmail threads with no matching ticket get stage "Gmail only."

For each client determine:
- Sync/connection issues: **Sync Issues** stage tickets only, plus Gmail threads indicating a **connection or sync problem** (PMS not connecting, data not flowing, etc.)
- Investigations: **Support / Investigation** stage tickets (e.g. unapproved TIN, tax ID issues, any active investigation)
- Escalated: **Escalated** stage tickets only
- Account updates: **Account Updates** stage tickets, or any thread about BI dashboard access, Power BI access, portal permissions, or report access
- Installs in process: New or Add Loc/Reactivate stage tickets; note location names if available

**Output 1 — Visual widget** using show_widget: HTML table with columns: Client, Flag (badge), Detail, Stage, Ticket (linked). Footer bar: # sync issues · # escalated · # locations in process · # active clients. Header label: `Past N days · Installation Team pipeline + Gmail · {today's date}` (substitute actual N).

**Output 2 — Slack image:** After producing the widget, run the **`get-secret`** skill with name `slack-bot-token` to retrieve the Slack bot token. Store the returned value — it will be passed to `slack-upload.py` in Step 2b. Then generate a PNG of the summary table and post it to Sean's Slack DM. IMPORTANT: Both scripts below MUST be run via `mcp__Desktop_Commander__start_process` — never via the bash sandbox (`mcp__workspace__bash`), which has no outbound network access.

---

**Step 1 — Build the data rows.** From the data you collected, construct a Python list called `rows` where each entry is a tuple:
`(client_name, flag, issue_or_installs, stage_label, ticket_id)`

- `flag` must be exactly one of:
  - `"SYNC ISSUE"` — **Sync Issues** stage tickets only, or Gmail threads indicating a **connection or sync** problem (PMS not connecting, data not flowing). Do NOT use for investigations or access issues.
  - `"INVESTIGATION"` — **Support / Investigation** stage tickets (e.g. unapproved TIN, tax ID mismatch, any active investigation). These are not sync failures.
  - `"ESCALATED"` — **Escalated** stage tickets only.
  - `"UPDATES"` — **Account Updates** stage tickets, **or** any thread about BI dashboard access, Power BI access, portal permissions, or report access requests. Routine workflow items.
  - `"GMAIL ONLY"` — Gmail-only threads with no matching HubSpot ticket.
  - `""` — clean install-in-process rows (New or Add Loc/Reactivate with no flag).
- `issue_or_installs`: for flagged rows use the issue description; for clean rows use location names
- `ticket_id`: use `"#NNNNNNNNNN"` format, or `"—"` for Gmail-only rows. If multiple tickets for one client, use the primary one with a `+` suffix.
- Compute footer stats: `n_sync` (int — SYNC ISSUE rows only), `n_escalated` (int — ESCALATED rows only), `n_investigation` (int — INVESTIGATION rows only), `n_locations` (string e.g. `"7+"`), `n_clients` (int — all active clients)
- Set `lookback_label` to `"Past 3 days"` on Monday or `"Past 2 days"` otherwise.
- Sort `rows` by stage using this order (matches the HubSpot board left-to-right):

```python
STAGE_ORDER = {
    "New": 0,
    "Sync Issues": 1,
    "Add Loc / Reactivate": 2,
    "Support / Investigation": 3,
    "Escalated": 4,
    "Remit": 5,
    "Account Updates": 6,
    "Gmail only": 7,
}
rows.sort(key=lambda r: STAGE_ORDER.get(r[3], 99))
```

---

**Step 2a — Generate the PNG via Desktop Commander.** Substitute your actual `rows`, stats, and today's date. This script only generates the image — upload is handled in Step 2b. Find the correct Python path first: run `which python3` via Desktop Commander and use the result (typically `/usr/local/bin/python3`).

```python
from PIL import Image, ImageDraw, ImageFont
from datetime import date

today = date.today().strftime("%B %-d, %Y")

# --- SUBSTITUTE ACTUAL DATA BELOW ---
rows = [
    # (client, flag, detail, stage, ticket)
    # flag options: "SYNC ISSUE" | "INVESTIGATION" | "ESCALATED" | "UPDATES" | "GMAIL ONLY" | ""
]
n_sync = 0
n_escalated = 0
n_investigation = 0
n_locations = "0"
n_clients = 0
lookback_label = "Past 2 days"
# --- END DATA ---

col_widths=[160,115,415,190,150]; row_h=42; header_h=48; pad_x=24; pad_top=80; footer_h=52
total_w=sum(col_widths)+pad_x*2; total_h=pad_top+header_h+row_h*len(rows)+footer_h+60
BG=(255,255,255); HEADER_BG=(245,244,241); BORDER=(210,208,202); TEXT_DARK=(30,30,28)
TEXT_MID=(90,88,84); TEXT_LIGHT=(140,138,132); ROW_ALT=(250,249,247)
RED_BG=(252,235,235);    RED_TEXT=(163,45,45)
AMBER_BG=(250,238,218);  AMBER_TEXT=(133,79,11)
PURPLE_BG=(242,235,254); PURPLE_TEXT=(90,40,160)
BLUE_BG=(232,240,254);   BLUE_TEXT=(24,95,165)
GREEN_BG=(232,248,237);  GREEN_TEXT=(30,110,60)
GRAY_BG=(241,239,232);   GRAY_TEXT=(95,94,90)
ACCENT=(24,95,165)

img=Image.new("RGB",(total_w,total_h),BG); draw=ImageDraw.Draw(img)
try:
    fb=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",14)
    fr=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",13)
    fs=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",11)
    ft=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",17)
    fsub=ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc",12)
except: fb=fr=fs=ft=fsub=ImageFont.load_default()

draw.text((pad_x,22),"Install Team Summary",font=ft,fill=TEXT_DARK)
draw.text((pad_x,46),f"{lookback_label}  ·  Installation Team pipeline + Gmail  ·  {today}",font=fsub,fill=TEXT_LIGHT)
headers=["Client","Flag","Issue / Installs in Process","Stage","Ticket"]
hx=pad_x; hy=pad_top
draw.rectangle([0,hy,total_w,hy+header_h],fill=HEADER_BG)
draw.line([(0,hy),(total_w,hy)],fill=BORDER,width=1)
draw.line([(0,hy+header_h),(total_w,hy+header_h)],fill=BORDER,width=1)
for h,w in zip(headers,col_widths): draw.text((hx+10,hy+15),h.upper(),font=fs,fill=TEXT_LIGHT); hx+=w

def badge(draw,x,y,text,bg,fg,font):
    tw=int(draw.textlength(text,font=font))
    draw.rounded_rectangle([x,y,x+tw+14,y+20],radius=4,fill=bg)
    draw.text((x+7,y+3),text,font=font,fill=fg)

for ri,row in enumerate(rows):
    ry=pad_top+header_h+ri*row_h
    draw.rectangle([0,ry,total_w,ry+row_h],fill=ROW_ALT if ri%2==0 else BG)
    draw.line([(0,ry+row_h),(total_w,ry+row_h)],fill=BORDER,width=1)
    rx=pad_x; client,flag,detail,stage,ticket=row
    draw.text((rx+10,ry+13),client,font=fb,fill=TEXT_DARK); rx+=col_widths[0]
    if flag=="SYNC ISSUE":      badge(draw,rx+6,ry+11,flag,RED_BG,RED_TEXT,fs)
    elif flag=="ESCALATED":     badge(draw,rx+6,ry+11,flag,AMBER_BG,AMBER_TEXT,fs)
    elif flag=="INVESTIGATION":  badge(draw,rx+6,ry+11,flag,PURPLE_BG,PURPLE_TEXT,fs)
    elif flag=="UPDATES":        badge(draw,rx+6,ry+11,flag,GREEN_BG,GREEN_TEXT,fs)
    elif flag=="GMAIL ONLY":    badge(draw,rx+6,ry+11,flag,GRAY_BG,GRAY_TEXT,fs)
    rx+=col_widths[1]
    d=detail if len(detail)<=52 else detail[:51]+"..."
    draw.text((rx+10,ry+13),d,font=fr,fill=TEXT_MID); rx+=col_widths[2]
    draw.text((rx+10,ry+13),stage,font=fr,fill=TEXT_MID); rx+=col_widths[3]
    draw.text((rx+10,ry+13),ticket,font=fs,fill=ACCENT)

fy=pad_top+header_h+row_h*len(rows)+16
draw.rounded_rectangle([pad_x,fy,total_w-pad_x,fy+44],radius=8,fill=HEADER_BG)
stats=[(str(n_sync),"sync issues"),(str(n_investigation),"investigations"),(str(n_escalated),"escalated"),(n_locations,"in process"),(str(n_clients),"active clients")]
seg_w=(total_w-pad_x*2)//5
for i,(num,label) in enumerate(stats):
    sx=pad_x+i*seg_w+seg_w//2; nw=int(draw.textlength(num,font=fb))
    draw.text((sx-nw//2-20,fy+8),num,font=fb,fill=TEXT_DARK)
    draw.text((sx-nw//2-20+nw+4,fy+10),label,font=fs,fill=TEXT_LIGHT)

img.save("/Users/sean/CODE/id-claude-reporting/install_summary.png","PNG",dpi=(144,144))
print("Image saved: /Users/sean/CODE/id-claude-reporting/install_summary.png")
```

**Step 2b — Upload to Slack via the shared script.** Run via Desktop Commander, substituting the actual `{today}` and `{lookback_label}` values:

```bash
python3 "/Users/sean/CODE/id-claude-reporting/skills/_shared/slack-upload.py" \
  --token   "<slack-bot-token from get-secret>" \
  --file    /Users/sean/CODE/id-claude-reporting/install_summary.png \
  --filename install_summary.png \
  --title   "Install Team Summary · {today}" \
  --comment "*Install Team Summary* · {lookback_label} · {today}"
```

If it prints `ok=True`, the image was delivered. If it fails, note the error — the widget output in the Cowork session is the fallback.

If zero active items are found across both sources, send a short Slack message via the slack_send_message MCP tool to channel `D0B0YUWV1UK` instead: `"*Install Team Summary* · {today} — No active items in the past N days."` (substitute actual N).

---

**Step 3 — Log the run.**

After Step 2b, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `install-team-summary` |
| `status` | `success` if the image was delivered to Slack · `partial` if Gmail or HubSpot returned no data · `error` if the skill failed entirely |
| `summary` | 1–3 sentences: date scanned, lookback window used, number of active clients and any sync issues or escalations surfaced. |
| `inputs` | `{ "date_scanned": "<YYYY-MM-DD>", "lookback_days": N }` |
| `outputs` | `{ "slack_ts": "<ts or null>", "open_tickets_count": N, "emails_found_count": N, "active_clients_count": N }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{ "n_sync": N, "n_escalated": N, "n_investigation": N }` |

Call skill-logger even on failure — the log should capture what went wrong.
