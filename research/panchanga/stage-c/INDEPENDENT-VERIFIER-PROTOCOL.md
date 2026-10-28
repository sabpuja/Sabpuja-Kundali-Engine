# Stage C independent verifier protocol

**Template. No verifier has been appointed and no verification has taken place.**

Stage C asks one question for each of 46 records: **what does the official IMD Rashtriya Panchang actually print?** You answer it by reading the government publication yourself and writing down what you see. You are not asked to agree or disagree with anyone else's numbers, and you will not see them until your own record is frozen.

## 1. Who may verify

The verifier must be a distinct human authorized by the Sabpuja owner.

The verifier must **not** be:

- the ChatGPT reviewer who sourced the 46 records (Stage A) and rechecked them (Stage B);
- Claude, or anyone acting as the developer or author of this package;
- another AI agent, script or automated process, whether or not it is presented as a person;
- someone who only approves values supplied by another person without reading the primary publication.

The verifier records, on the [assignment form](VERIFIER-ASSIGNMENT-TEMPLATE.md), their name, affiliation, relevant experience, an attributable identifier, any conflict of interest and a declaration of independence. The owner approves the appointment separately.

**Attributable identity.** Use an identity that belongs to you alone, such as your own GitHub account or a signed email. Earlier reviews in this project were posted from the owner's GitHub account (`ubermensch-site`) on behalf of the ChatGPT reviewer, so an approval from that account cannot by itself show which person performed a check.

## 2. What you may and may not look at before freezing

**Use:**

- the official pages listed in the [source access guide](SOURCE-ACCESS-GUIDE.md);
- this protocol, the assignment form, the [blind sheet](BLIND-VERIFICATION-SHEET.csv) and Part A of the [method checklist](METHOD-FACTS-CHECKLIST.md).

**Do not open until your record is frozen (step 5):**

- [REFERENCE-CROSSWALK.csv](REFERENCE-CROSSWALK.csv) and [METHOD-FACTS-RECONCILIATION.md](METHOD-FACTS-RECONCILIATION.md);
- `research/panchanga/reference-fixtures/imd-rashtriya-panchang-capture-template.json`;
- `research/panchanga/SOURCE-REGISTER.md` section 5;
- `docs/science/SCI-PAN-01-PANCHANGA-METHOD-DECISION-PROPOSAL.md` and `docs/science/WP-B2-PANCHANGA-ENGINEERING-HANDOFF-DRAFT.md`;
- the comments and reviews on PR #51;
- any commercial Panchanga website, app or almanac, and any software calculation (including Swiss Ephemeris).

If you see an expected value by accident, say so in the signoff and in the notes column of the affected rows. Do not hide it. QA decides whether those rows need a different verifier.

## 3. Procedure

### Step 1. Prepare

1. Complete and sign the assignment form, then send it to the owner. Do not start until the owner confirms the appointment.
2. Make a private working copy of `BLIND-VERIFICATION-SHEET.csv`. Do not edit the columns to the left of `V01`.
3. Note the exact date and time (UTC) when you begin.

### Step 2. Read the method pages (Part A)

Open the explanation page and the names page (see the source guide). Fill Part A of the method checklist from what the pages say. Quote short phrases exactly. Where the page does not answer a question, write `NOT STATED`. Do not fill gaps from your own knowledge.

### Step 3. Transcribe each record

For each of the 46 rows:

1. Open the URL in `source_url`. Write the URL you actually opened in `V03`.
2. Find the daily row for the Gregorian date in `gregorian_date`. The source guide explains how to tell it apart from the Saka date. Write the date row exactly as printed, Gregorian and Saka, in `V04`.
3. Find the entry described in `row_locator`. For example, "ending entry 2 of 3 for Karana" means the second Karana ending printed for that date, counting in the order printed.
4. Record, exactly as printed and without correcting spelling or format:
   - `V05`: the name (for sunrise and sunset, write `n/a`);
   - `V06`: any Paksha, month or other context printed with it, or `none`;
   - `V07`: the printed time, including any prefix such as `h.`, separators and AM/PM;
   - `V08`: the printed precision (for example whole minute).
5. `V09`: your own interpretation of the local date and time in IST, in the form `YYYY-MM-DDTHH:MM+05:30`. If the printed hour is 24 or more, apply the rule IMD states for such times (you record that rule as M-CAL-01 in Part A) and give the resulting civil date. If IMD does not state a rule, write `RULE NOT STATED` and set the outcome to `DATE_OR_TIME_AMBIGUOUS`.
6. `V10`: anything ambiguous, such as unclear separators, a missing AM/PM, a name that is cut off, or a different notation from neighbouring rows.
7. `V11`: if the row prints more endings of this element than the locator expects, or fewer, write what else is printed.
8. `V01`, `V02`: whether the source was accessible (`YES`, `NO` or `PARTIAL`) and when you read it (UTC).
9. `V12`: one blind outcome (section 4). `V13`: your identifier. `V14`: notes.

Record exactly what you see. A row you could not read is a valid result. Never fill a field from memory, inference, another website or another person.

### Step 4. Source problems

- If the official site or page does not load, record `SOURCE_UNAVAILABLE` with the date, time and what happened (for example a timeout or an error code).
- Do not use proxies, caches, archives, mirrors, scrapers or any method that gets around an access restriction. Do not substitute a commercial Panchanga.
- If the page loads but the row or entry cannot be found, record `REVIEW_INCOMPLETE` and describe what you saw.
- A downloaded PDF from the same official domain is acceptable if you record its URL and the edition it states.

### Step 5. Freeze

When all 46 rows and Part A are complete:

1. Save the completed sheet as `BLIND-VERIFICATION-SHEET.completed.csv` and Part A as `METHOD-FACTS-CHECKLIST.completed.md`.
2. Compute the SHA-256 of each file (for example `sha256sum` on Linux, `shasum -a 256` on macOS, or `Get-FileHash -Algorithm SHA256` in Windows PowerShell).
3. Send both files and both checksums to the owner and QA through an attributable channel before reconciliation starts. From this point, the files are never edited. A correction is a new, separately checksummed file with a written reason.

### Step 6. Reconciliation (after freeze)

Reconciliation is done by the QA reviewer, or by someone the owner designates, with the verifier if the owner wishes. It compares the frozen transcription with [REFERENCE-CROSSWALK.csv](REFERENCE-CROSSWALK.csv) and [METHOD-FACTS-RECONCILIATION.md](METHOD-FACTS-RECONCILIATION.md):

| Column | Rule |
|---|---|
| `R01` name | Exact string as printed. A spelling difference between the two transcriptions is a difference |
| `R02` context | Exact string as printed |
| `R03` printed time | Same hour and minute. If only the notation differs (for example `h.` 24-hour form against AM/PM), record it as a notation difference |
| `R04` date row | Same Gregorian date row |
| `R05` extended-hour interpretation | The verifier's `V09` equals the crosswalk's `candidate_interpreted_ist_datetime` |
| `R06` outcome | One reconciliation outcome (section 4) |
| `R07` | Discrepancy id, if any |
| `R08` to `R10` | Who reconciled, when, and the frozen sheet's SHA-256 |

**There is no numerical tolerance in Stage C.** It checks a transcription against a printed page, so any difference is recorded. The comparison tolerances in PAN-D15 belong to Stage D and later engineering, not here.

### Step 7. Discrepancies

Every row whose outcome is not `MATCHED_PRIMARY_SOURCE` gets an entry in [DISCREPANCY-REGISTER.csv](DISCREPANCY-REGISTER.csv) (section 5). The original candidate in the capture template is **not edited**. A correction, if one is justified, is proposed in a separate change, reviewed by QA and approved by the owner.

### Step 8. Sign

Complete the [signoff](STAGE-C-SIGNOFF-TEMPLATE.md) with the counts, checksums and attestations. A signature without the frozen row-level files is not accepted. An approving GitHub review can help attribute the signoff, but it does not prove that the source was read.

## 4. Outcome codes

Blind outcomes, which the verifier writes in `V12` before freezing:

| Code | Meaning |
|---|---|
| `TRANSCRIBED` | The entry was found and recorded |
| `SOURCE_UNAVAILABLE` | The official page or document could not be accessed |
| `DATE_OR_TIME_AMBIGUOUS` | The entry was found, but its date or time cannot be read unambiguously |
| `SOURCE_METHOD_UNCLEAR` | The entry was found, but what it represents (station, time scale, convention) is unclear from the source |
| `REVIEW_INCOMPLETE` | The row or entry could not be located, or the check was not finished |

Reconciliation outcomes, written in `R06` after freezing. These are proposed outcomes for this package, not existing approvals:

| Code | Meaning |
|---|---|
| `MATCHED_PRIMARY_SOURCE` | Name, context, printed time, date row and interpretation all match |
| `SOURCE_DISAGREEMENT` | The independent transcription differs from the candidate in any compared field |
| `SOURCE_UNAVAILABLE` | Carried over from the blind outcome |
| `DATE_OR_TIME_AMBIGUOUS` | Carried over, or the interpretation of the date differs |
| `SOURCE_METHOD_UNCLEAR` | Carried over |
| `REVIEW_INCOMPLETE` | Carried over, or reconciliation could not be completed |

## 5. Discrepancy severity

| Severity | Meaning | Examples |
|---|---|---|
| S1 | The value would be wrong if used | Different time, different name, different date row, different next-day interpretation |
| S2 | The value cannot be confirmed | Source unavailable, entry not found, ambiguous date or time |
| S3 | The value matches but its meaning is unclear | Station, time scale or convention not stated |
| S4 | Presentation only | Spelling variant or notation difference with the same value |

Each entry needs: candidate ID, original Sabpuja transcription, independent transcription, source and exact locator, description, severity and effect, reviewer identity, proposed resolution, final status, and the QA and owner dispositions where required.

## 6. Method checklist

[METHOD-FACTS-CHECKLIST.md](METHOD-FACTS-CHECKLIST.md) covers sunrise and sunset, ayanamsa, times after midnight, Karana indexing, and the Yoga, Nakshatra and Karana names. These items are **not** part of the 46-record count. Record what IMD says explicitly, separately from questions the publication does not answer.

## 7. Source rights

Record only individual factual fields. Do not copy whole pages or tables, and do not attach screenshots or PDFs to the repository. Record the rights notice you see in [SOURCE-RIGHTS-CHECKLIST.md](SOURCE-RIGHTS-CHECKLIST.md) section A. Do not draw legal conclusions.
