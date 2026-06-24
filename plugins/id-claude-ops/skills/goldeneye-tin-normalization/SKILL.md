---
name: goldeneye-tin-normalization
description: >
  Normalize a pasted list of Tax Identification Numbers (TINs) for entry into GoldenEye's Expected
  Tax IDs field. Strips all non-digit characters, removes duplicates, and outputs a comma-space
  separated string in a code block ready to paste. Use when Sean pastes TINs and asks to normalize
  them for GoldenEye, or says "normalize TINs", "format TINs for GoldenEye", "prep the TIN list",
  or similar.
---

# GoldenEye TIN Normalization

---

## Instructions

### Step 1 — Parse the input

Look at the pasted TIN list and determine the format:

- **Clearly delimited** (tokens separated by newlines, commas, semicolons, or whitespace): split on those delimiters, strip all non-digit characters from each token, discard empty strings.
- **Mashed together** (one long string of digits and hyphens with no clear token separators): strip all non-digit characters from the entire string, then split into 9-character chunks.

### Step 2 — Deduplicate

Remove duplicate TINs, keeping the first occurrence. Do not validate length or format — GoldenEye requires all TINs exactly as received, including malformed ones. Removing a "bad" TIN can cause valid claims to be dropped.

### Step 3 — Output

Produce the final list as a single line, comma-space separated, inside a code block:

```
123456789, 987654321, 456789123
```

Also state the count: "X TINs (Y duplicates removed)" — or omit the duplicate note if none were found.

---

### Step 4 — Log the run

Call the **`skill-logger`** skill with:

| Field | Value |
|---|---|
| `skill_name` | `goldeneye-tin-normalization` |
| `status` | `success` |
| `summary` | 1 sentence: number of TINs normalized and duplicates removed. |
| `inputs` | `tin_count_raw={N}` |
| `outputs` | `tin_count_normalized={N}` · `duplicates_removed={N}` |
| `errors` | Any failures (empty if none) |
