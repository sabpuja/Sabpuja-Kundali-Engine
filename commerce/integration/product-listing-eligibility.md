# Janam Kundali Essentials: pre-purchase eligibility text (DRAFT, QA store only)

KUN-COM-UX-CLAIM-001, from the ChatGPT review of PR #90 (gate 1). This is English draft copy for the **QA product
listing** on `sabpuja-qa`. It is not for the live store: the final live wording needs owner approval. It states
exactly what the claim page and the engine accept, so nobody buys a report they cannot receive. The city list is
generated from `prototype/kundali_prototype/places.json` (the `in-` entries the paid route serves) and is kept in step
by `tests/test_claim_ux.py`.

---

**Before you buy: what this report needs**

- **Birthplace:** this pilot report can be prepared only for people born in one of these cities:
  New Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, Jaipur, Lucknow, Varanasi, Guwahati.
  If your birthplace is not listed, please do not buy yet. We never substitute a nearby city, because the chart
  would be wrong.
- **Birth date:** from 1 January 1970 to 31 December 2100.
- **Birth time:** the exact local time of birth (for example from the birth certificate). We never assume a time.
- **Language:** the report is in English only (14-page PDF). यह रिपोर्ट केवल अंग्रेज़ी में है।
- **Delivery:** after purchase, use the "Prepare your Janam Kundali" button on the order page or in your
  confirmation e-mail. You can prepare it within 30 days, and after your first download you can prepare up to 3
  corrected versions within 30 days. Your birth details are used once and are not stored.
