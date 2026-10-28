# Stage C source access guide

The only acceptable sources for Stage C are the official pages of the Positional Astronomy Centre (PAC), India Meteorological Department, Government of India, on `packolkata.imd.gov.in`, or an official PDF edition from the same domain.

## 1. Official pages

| Role | URL | Used for |
|---|---|---|
| Methodology | <https://packolkata.imd.gov.in/panchang/en/explanation> | Method checklist Part A: sunrise and sunset, station, time standard, ayanamsa, notation for times after midnight, Karana description |
| Official names | <https://packolkata.imd.gov.in/panchang/ta/tithi-nakshatra> | Method checklist Part A: Yoga, Nakshatra and Karana names and order |
| Spring records | <https://packolkata.imd.gov.in/panchang/bn/chaitra> | `SC-01` to `SC-15` (2026-03-22, 2026-03-23) |
| Monsoon records | <https://packolkata.imd.gov.in/panchang/bn/ashadha> | `SC-16` to `SC-31` (2026-07-14, 2026-07-17) |
| Autumn records | <https://packolkata.imd.gov.in/panchang/bn/kartika> | `SC-32` to `SC-46` (2026-10-26, 2026-10-28) |

The daily pages sit under a `/bn/` path and the names page under `/ta/`. These are the URLs at which the records were originally found, and their body text was reported to be in English. If a page shows a different language, record the language in `V14` and transcribe what is printed. Do not switch to another language route without noting the URL you used in `V03`.

## 2. Finding the right row

The monthly pages are organised by the **Saka (Indian national) calendar**. Each daily row carries both a Saka date and a Gregorian date.

1. Use the Gregorian date in `gregorian_date`. That is the record's key.
2. The blind sheet also gives a Saka date in `saka_date_locator_aid`. It was **derived by Claude** from the Indian national calendar to help you find the row. It is not evidence. If the page pairs the Gregorian date with a different Saka date, record what is printed and note the difference.
3. The Saka month of the page (Chaitra, Ashadha, Kartika) is a civil month. The lunar month named alongside a Tithi or Paksha may be different. Transcribe the lunar month as printed in `V06`. Do not treat a different lunar month name as an error.
4. A daily row may list several endings of the same element (for example two Karanas). `row_locator` gives the position counted in the order printed. If the count printed differs from the locator, record what is printed in `V11`.
5. Times printed as 24 hours or more belong to the row on which they are printed. Do not move them to the next row. Record them exactly as printed in `V07`, then interpret them in `V09` using IMD's own rule.

## 3. Station

- Sunrise and sunset in the daily pages are expected to apply to a single station that IMD defines on the explanation page. Record its name and coordinates as printed in Part A (M-SUN-05 and M-SUN-06). Do not compare them with any city.
- For Tithi, Nakshatra, Yoga and Karana endings, record in Part A (M-GEN-02) whether IMD states that they are station-independent.

## 4. If a source cannot be reached

- Record `SOURCE_UNAVAILABLE` with the date, time (UTC), URL and what happened.
- Try again on another day if you can, and record each attempt.
- Do not use proxies, VPNs to bypass a block, caches, web archives, mirrors, search-engine snippets, scrapers or any other way around an access restriction. Search-engine text is not acceptable for Stage C, even from the official domain.
- Do not substitute commercial Panchanga websites, apps, printed almanacs or software calculations.
- Never write a value you did not read on the official source.

## 5. Evidence handling

- Record individual factual fields only.
- You may keep private screenshots or saved copies as personal working evidence, and QA may ask to see them, but they are **not** committed to the repository and are not reproduced in this package.
- Record the edition or version the page shows (for example the Saka year and any edition or update date) in Part A (M-GEN-01) and in the signoff.
- Record any rights or copyright notice you see in [SOURCE-RIGHTS-CHECKLIST.md](SOURCE-RIGHTS-CHECKLIST.md) section A.
