# Stage D readiness checklist

**No gate below is complete. No record has reached Stage C or Stage D.**

Stage C establishes what the source publishes. Stage D decides whether an independently verified fact may be used as an engineering reference value. Stage D needs Stage C, and more. Only Stage D records may enter an approved engineering golden-reference set (SOURCE-REGISTER section 5).

## Per-record gates

| Gate | Requirement | Status |
|---|---|---|
| D-1 | Stage C evidence accepted by QA and the owner for this record ([STAGE-C-QA-ACCEPTANCE.md](STAGE-C-QA-ACCEPTANCE.md)) | NOT STARTED |
| D-2 | Date and time notation verified, including IMD's own rule for times of 24 hours or more | NOT STARTED |
| D-3 | Location applicability confirmed: geocentric endings, or the Central Station for sunrise and sunset, never a city | NOT STARTED |
| D-4 | Source rights reviewed and the permitted use recorded ([SOURCE-RIGHTS-CHECKLIST.md](SOURCE-RIGHTS-CHECKLIST.md)) | NOT STARTED |
| D-5 | Scientific-method compatibility assessed for the element (below) | NOT STARTED |
| D-6 | Acceptance tolerance approved for the element (PAN-D15) | NOT STARTED |
| D-7 | Independent engineering QA of the record's use | NOT STARTED |
| D-8 | Required owner decisions completed | NOT STARTED |

## Method compatibility by element (gate D-5)

| Element | What must be established | Owner decisions involved | Status |
|---|---|---|---|
| Tithi | Ayanamsa-free; geocentric and IST confirmed; IMD rounding rule known | PAN-D06, D08, D09, D15, D18 | NOT STARTED |
| Karana | As Tithi, plus the 60-position indexing supported by the source, including fixed-Karana positions and verified Sakuni and Chatuspada rows | PAN-D07, D16 | NOT STARTED |
| Nakshatra | IMD's ayanamsa definition captured verbatim and shown compatible with SCI-01a within a stated budget (SCI-PAN-01 section 3.1). A verified IMD time does not by itself become a Swiss calculation oracle if the conventions differ | PAN-D01, D15, D16 | NOT STARTED |
| Yoga | As Nakshatra, with the ayanamsa counted twice | PAN-D01, D15, D16 | NOT STARTED |
| Sunrise and sunset | IMD convention verified from the source; a sunrise convention adopted; values used only for the Central Station | PAN-D03, D04, D11, D17 | NOT STARTED |

## Programme gates

| Gate | Status |
|---|---|
| PAN-D01 to PAN-D20 decided | PENDING (all 20) |
| WP-B2 readiness | BLOCKED |
| OD-09 fixed engine base | Not decided in this package |
| SCI-01a change | None proposed |
| Production | NO-GO |
