---
name: powerbi-export
description: >
  Download the InsideDesk PMS Snapshot Monitoring report from Power BI as an Excel file.
  Use this skill whenever Sean asks to "export Power BI", "download the BI report",
  "get the latest PMS data", "refresh the OOS report data", or similar. Also invoke
  automatically as Step 0 when running the pms-oos-report skill if no Excel file has
  been attached yet. Produces a date-stamped .xlsx in the project folder ready for
  the pms-oos-report skill.
---

# Power BI Export Skill

This skill automates downloading the **CS Datafeed** table from the InsideDesk PMS
Snapshot Monitoring report in Power BI. The output is an `.xlsx` file saved to the
project folder, suitable for immediate use as input to the `pms-oos-report` skill.

---

## Report details

- **Report name:** PMS Snapshot Monitoring
- **Page:** CS Datafeed
- **Share link:** https://app.powerbi.com/links/HSlKZeAzoD?ctid=2afcdfbb-da91-4f43-91ca-c8ba7d1f4abc&pbi_source=linkShare
- **Direct URL:** https://app.powerbi.com/groups/me/reports/b0709aef-3b36-4360-ba41-aca3d78bdf10/ReportSection3331744257e6e3452745?ctid=2afcdfbb-da91-4f43-91ca-c8ba7d1f4abc&experience=power-bi
- **Full column reference:** `docs/power-bi-pms-snapshot-report.md`

---

## Step 1 — Navigate to the report

Use the Claude in Chrome browser extension. Navigate directly to the report page:

```
https://app.powerbi.com/groups/me/reports/b0709aef-3b36-4360-ba41-aca3d78bdf10/ReportSection3331744257e6e3452745?ctid=2afcdfbb-da91-4f43-91ca-c8ba7d1f4abc&experience=power-bi
```

Wait up to 10 seconds for the report to fully load. The page is ready when the
**CS Datafeed** table is visible with row data and the facility count (e.g. "1,342")
appears in the bottom-left card. If the report prompts for sign-in, Sean will need
to authenticate manually — surface this to him and wait.

Take a screenshot to confirm the data is loaded before proceeding.

---

## Step 2 — Open the visual context menu

The export is accessed through the **CS Datafeed table visual's context menu**, not
the top-level Export button in the toolbar (which only exports the whole page as
PowerPoint or PDF).

1. Hover the mouse over the CS Datafeed table (center of the visual, roughly the
   middle of the data area).
2. A small icon toolbar will appear in the **top-right corner of the visual**.
3. Click the **"…" (More options)** button — it is the rightmost icon in that toolbar.
4. A dropdown menu appears with these options (among others):
   - Share
   - Add alert
   - Add a comment
   - Explore this data (preview)
   - **Export data** ← click this
   - Show as a table
   - Spotlight
   - Get insights
   - Sort options

Click **Export data**.

---

## Step 3 — Configure the export dialog

A dialog titled **"Which data do you want to export?"** will appear with three options:

| Option | Description | Action |
|---|---|---|
| **Data with current layout** | All rows as displayed in the table, without formatting | ✅ Select this |
| Summarized data | Aggregated/summary values only | ✗ Do not use |
| Underlying data | Disabled by report author | ✗ Not available |

**"Data with current layout"** should already be selected by default (radio button
filled). If it is not, click it to select it.

Confirm the **File format** dropdown shows:
```
.xlsx (Excel 150,000-row max)
```
Leave this as-is. Do not change it.

---

## Step 4 — Click Export and capture the file

After Sean confirms, click the **Export** button in the dialog.

Power BI will generate the file and trigger a browser download. The file will land in
Sean's default browser Downloads folder:

```
~/Downloads/
```

The filename Power BI assigns is typically something like:
```
CS Datafeed.xlsx
```
or a variation. After the download completes, use a bash command to find the
most recently modified `.xlsx` file in `~/Downloads/`:

```bash
ls -t ~/Downloads/*.xlsx | head -1
```

---

## Step 5 — Move and rename the file

Move the downloaded file to the project folder with a date-stamped name so it's
ready for the `pms-oos-report` skill and doesn't get overwritten on the next run:

```bash
TODAY=$(date +%Y-%m-%d)
PROJ="/Users/sean/CODE/insidedesk-claude-plugin/Insidedesk Claude Plugin"
SRC=$(ls -t ~/Downloads/*.xlsx | head -1)
DEST="$PROJ/PMS_Sync_Status_Report_${TODAY}.xlsx"
cp "$SRC" "$DEST"
echo "Saved to: $DEST"
```

Verify the file is non-empty (> 10 KB) before confirming success:

```bash
du -k "$DEST"
```

---

## Step 6 — Respond to Sean

After the file is saved, report back in chat:

1. Confirm the file was downloaded and where it was saved.
2. Provide a `computer://` link to the file:
   ```
   computer:///Users/sean/CODE/insidedesk-claude-plugin/Insidedesk Claude Plugin/PMS_Sync_Status_Report_YYYY-MM-DD.xlsx
   ```
3. Note the **data refresh timestamp** shown in the Power BI report header (e.g.
   "Data updated 5/11/26") so Sean knows how fresh the data is.
4. If Sean has not already asked to run the OOS report, offer:
   > "Want me to run the PMS OOS report now using this file?"

---

## Error handling

| Situation | Action |
|---|---|
| Report won't load / login required | Surface to Sean, ask him to sign in, then retry |
| "…" toolbar doesn't appear on hover | Try clicking directly on a table cell first to focus the visual, then hover near the top-right corner |
| Export dialog shows "Underlying data" as the only unlocked option | Select it instead — the column structure is the same |
| Download doesn't appear in ~/Downloads | Ask Sean to check his browser's download location setting and confirm where the file landed |
| File is < 10 KB | Likely an error or empty export — surface to Sean and offer to retry |

---

## Integration with pms-oos-report skill

After this skill completes, the downloaded file at:
```
/Users/sean/CODE/insidedesk-claude-plugin/Insidedesk Claude Plugin/PMS_Sync_Status_Report_YYYY-MM-DD.xlsx
```
can be passed directly to the `pms-oos-report` skill. The pms-oos-report skill
expects a sheet named `Export` with the columns documented in
`docs/power-bi-pms-snapshot-report.md`.

If running both skills in sequence, there is no need to ask Sean to attach the file
manually — reference the path directly.

---

## Step 7 — Log the run

After Step 6, call the **`skill-logger`** skill with the following payload:

| Field | Value |
|---|---|
| `skill_name` | `powerbi-export` |
| `status` | `success` if the file was saved and is non-empty · `partial` if the file downloaded but could not be verified · `error` if the export failed entirely |
| `summary` | 1–3 sentences: report name exported, destination file path, and file size in KB. |
| `inputs` | `{ "report_name": "PMS Snapshot Monitoring" }` |
| `outputs` | `{ "excel_path": "<PMS_Sync_Status_Report_YYYY-MM-DD.xlsx>", "file_size_kb": N }` |
| `errors` | Any steps that failed (empty dict if none) |
| `metadata` | `{}` |

Call skill-logger even on failure — the log should capture what went wrong.
