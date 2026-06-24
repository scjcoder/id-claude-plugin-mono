# Decision Memo Examples

Reference these when Sean asks for a completed memo example or when calibrating structure.

---

## Example 1: Process Change Decision

```markdown
---
**Decision ID**: DM-001
**Title**: Switch from Manual to Automated DOS Update Processing
**Date**: 2025-03-01
**Decision Maker(s)**: Sean Johnson

---

## Decision Summary
Decided to automate the DOS update process using a script-based criteria engine to replace manual review, reducing processing time and human error.

---

## Current Backend Development Process
DOS updates are currently reviewed manually against a spreadsheet. Staff check each record against Action Needed flags and apply updates one at a time. This process is time-consuming and inconsistently applied across team members.

---

## Implementation Steps
1. Finalize criteria logic in the automation script (Action Needed rules, Office Closed handling, PMS Snap thresholds)
2. Test script against current dataset in staging environment
3. Review output with team leads before live deployment
4. Deploy to production and monitor for first two processing cycles
5. Document any exceptions or edge cases for ongoing maintenance

---

## Future Considerations
- Build a reporting layer to flag records that fall outside normal criteria ranges
- Evaluate whether the script can be scheduled to run automatically on a set cadence
- Revisit "Contact Client DOS" threshold (currently >7 days) after 60 days of production data

---

**Status**: Approved
```

---

## Example 2: Communication Policy Decision

```markdown
---
**Decision ID**: DM-002
**Title**: Standardize First-Contact Client Email Format
**Date**: 2025-03-15
**Decision Maker(s)**: Sean Johnson

---

## Decision Summary
Established a standard format for all first-contact client emails: no office-specific names, no resolution timelines, single clear ask per message.

---

## Current Backend Development Process
Client emails were drafted ad hoc with no consistent structure, leading to inconsistent tone and missing information. Some emails included premature timelines that couldn't be met.

---

## Implementation Steps
1. Document standard email rules and distribute to team
2. Create approved templates for common scenarios (issue notification, follow-up, info request)
3. Review all outbound client emails against the standard for the first 30 days

---

## Future Considerations
- Add a secondary template set for escalation emails
- Consider a peer review step for high-stakes client communications

---

**Status**: In Progress
```
