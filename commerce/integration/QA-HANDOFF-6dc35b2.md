# KUN-RC-COM-001B: independent QA handoff for the commerce candidate

**Candidate:** PR #85 `kun-rc-com-001` @ `6dc35b244bbd76754fe528937d4119721cfc5348`, parent
`9d563a906add3acf7601c9a5c6afa9e2671b17d2`, on PR #86 `kun-rc-ess-001` @
`970a23753c9464f7d6e3071e2b76c015892ac153`. Both PRs are draft and unmerged. This handoff file and the
`integration/` templates are on a separate stacked branch (`kun-rc-com-001b-shopify-qa`), so the candidate SHA
is unchanged. Developer evidence only: ChatGPT reruns the critical scenarios before accepting.

## 1. Environment

```
Python 3.13.18  PyMuPDF 1.26.7  pyswisseph 2.10.3.2  reportlab 4.4.9  tzdata 2026.5  uharfbuzz 0.57.0
ephemeris (pinned, src/sabpuja_kundali/ephemeris-manifest.json):
  1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7  semo_18.se1
  ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66  sepl_18.se1
```
Obtain and verify the data as in `data/ephemeris/README.md` (`sha256sum` must equal the manifest).

**Accepted independent swetest configuration** (engine-level, unchanged by commerce): official
`https://github.com/aloistr/swisseph` at `c69c14adb7a0f94829586ffd92cd422aacb21e86` (the commit that supplies the pinned files), Swiss `2.10.03`, built with
`make swetest`, receipt keys as in `tests/swiss_conformance/README.md`. Reference receipt from KUN-SCI-GOLD-001:
`swetest_sha256 400661cdd27d1b3d55766de9a657d5a22bf232308468c2db2bea435152ae5abd`. Frozen tolerances (SCI-05):
`engine_vs_swetest` 1e-8°, `binding_vs_swetest` 1e-9°, Lagna formula 1e-9° (SCI-04). Commerce does not change
any engine, report or Panchanga file: `git diff 970a237..6dc35b2 --name-only` lists only `commerce/`, and
`tests.panchanga.identity_v10 --check` passes. I did not rebuild swetest in this round (building external
source was not permitted in this session). To rerun it:

```sh
python -m tests.swiss_conformance.run --swetest /path/to/swetest --receipt /path/to/receipt.json \
  --ephe /path/to/ephe --report-dir reports          # needs a clean committed tree
```

## 2. Commands (exact)

```sh
git fetch origin kun-rc-com-001 && git worktree add --detach /tmp/qa-6dc 6dc35b244bbd76754fe528937d4119721cfc5348
cd /tmp/qa-6dc && git status --short                 # must be empty
E=/path/to/verified/ephe
# Commerce, pinned data: 144 tests, OK, 0 skipped
PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=$E \
  python -m unittest discover -s commerce/tests -v
# Commerce, no data: 144 tests, OK (skipped=10, engine-backed only)
PYTHONPATH=src:prototype:.:commerce:commerce/tests python -m unittest discover -s commerce/tests
# Regression: report 299 OK (skipped=2), prototype 190 OK, identity PASS
PYTHONPATH=src:prototype:.:report/phase1/tests:report/phase1/tools:report/phase1 SABPUJA_TEST_EPHE_PATH=$E \
  python -m unittest discover -s report/phase1/tests
PYTHONPATH=src:prototype:prototype/tests SABPUJA_TEST_EPHE_PATH=$E python -m unittest discover -s prototype/tests
python -m tests.panchanga.identity_v10 --check
# One class or test
PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=$E \
  python -m unittest test_generate.SendRace -v
```
A wrong `SABPUJA_TEST_EPHE_PATH` makes 4 end-to-end tests fail with 503 (fail-closed), not skip; check the path.

## 3. Critical scenarios → tests

| Scenario | Tests |
|---|---|
| Refund **before** send (after render) | `test_generate.SendRace.test_refund_after_render_before_send_withholds_pdf`, `test_over_http_refund_before_write`, `test_cancel_after_render_before_send_withholds_pdf`, `test_generate.Quota.test_refund_during_render_blocks_delivery` |
| Refund **during** send | `SendRace.test_refund_while_sending_is_not_counted` |
| Revoked delivery cannot be recorded | `SendRace.test_commit_after_revoke_is_refused_at_store_level`, `test_double_commit_counts_once` |
| Incomplete delivery and retry | `SendRace.test_mid_stream_disconnect_released_and_retry_counts_once`, `Quota.test_failed_send_does_not_count`, `test_recovery.Restart.test_crash_mid_render_releases_after_stale_window`, `Quota.test_abandoned_reservation_recovers` |
| Session ends mid-flight | `SendRace.test_logout_after_render_before_send_withholds_pdf`, `test_webhooks.Orders.test_cancel_revokes_and_ends_sessions` |
| Refund/cancel before `orders/paid` | `test_webhooks.Orders.test_refund_before_paid_webhook_blocks_activation`, `test_cancel_before_paid_blocks_activation`, `test_order_recovery.Recovery.test_tombstone_beats_recovery` |
| Failed GraphQL verification | `test_verifier.GraphQL.test_unusable_answers_fail_closed` (500, 429, errors, bad JSON, partial answer, 401), `test_unreachable_fails_closed`, `test_generate.Access.test_live_check_unavailable_fails_closed`, `test_required_verification_without_verifier_fails_closed`, `test_config.Load.test_verification_cannot_be_on_without_token` |
| Shopify no longer allows the line | `test_verifier.GraphQL.test_refunded_line_zero_quantity_cancelled_unpaid_test_missing`, `test_end_to_end_with_fake_shopify`, `Access.test_reconciliation_revokes_what_shopify_no_longer_allows`, `test_reconciliation_detects_variant_change`, `test_partially_refunded_order_keeps_unrefunded_line` |
| Missing customer e-mail | `test_webhooks.Orders.test_missing_email_creates_unclaimable_entitlement`, `Recovery.test_paid_without_email_is_recovered_and_claimable`, `test_still_without_email_keeps_the_exception` |
| Malformed webhook | `test_webhooks.Signature.test_invalid_json_with_valid_signature_is_kept_as_exception`, `Orders.test_malformed_ids_do_not_create`, `Recovery.test_malformed_webhook_order_is_recovered_by_id` |
| Recovery safety | `Recovery.test_refunded_cancelled_unpaid_and_wrong_lines_create_nothing`, `test_partial_refund_recovers_only_the_unrefunded_line`, `test_idempotent_and_never_overwrites_an_existing_email`, `test_deadlines_run_from_the_order_time`, `test_past_claim_window_is_not_recreated`, `test_unusable_answers_fail_closed`, `test_query_reads_email_and_nothing_else_personal` |
| Claim window and horizon | `test_verifier.Horizon.*`, `Quota.test_unclaimed_entitlement_expires`, `test_window_30_days_from_first_delivery`, `test_config.Load.test_windows_must_fit_order_read_horizon` |
| OTP limits | `test_claim.Codes.*` (13: expiry, single use, 5-try lock, cooldown, daily cap, per-client rate, window reset, trusted proxy only), `Enumeration.test_same_response_for_match_mismatch_and_unknown`, `test_mail_failure_is_not_visible` |
| Bounded mail worker | `test_verifier.MailWorker.test_sustained_claims_use_one_worker_and_bounded_queue` (300 claims, one thread, queue ≤ 5) |
| Webhook authenticity | `test_webhooks.Signature.*` (10) |
| Quota policy 1 + 3 / 30 days | `Quota.test_initial_plus_three_then_refused`, `test_policy_is_configurable`, `Orders.test_quantity_multiplies_generations` |
| English only, Essentials only | `test_generate.EnglishOnly.*`, `EssentialsGate.*`, `test_end_to_end.Pipeline.test_hindi_refused_before_engine`, `test_english_fourteen_pages_searchable_no_devanagari`, `Isolation.test_paid_path_only_uses_essentials` |
| Wording switch OFF by default | `test_end_to_end.ReleaseGate.test_refuses_until_wording_released` |
| Privacy at rest and in logs | `test_privacy.AtRest.*` (database + WAL scan for birth data, PDF, e-mail, code, token; schema allow-list; logs; secure_delete; purge; pepper), `Recovery.test_no_email_in_store_exceptions_or_logs`, `Orders.test_exception_can_be_resolved_and_holds_no_pii` |
| Rollback switch, restart | `test_recovery.Restart.*` |

Full list of the 144 test ids: `test-names.txt` in the evidence folder.

## 4. Evidence

Project files `kun-rc-com-001b/evidence/` (and `kun-rc-com-001/evidence-r3/` for the regression suites on the
same SHA):

| File | Content |
|---|---|
| `commerce-pinned-clean-6dc35b2.log` | 144 tests, OK, 0 skipped, from a fresh detached worktree with an empty `git status` |
| `test-names.txt` | the 144 test ids |
| `graphql-validate-admin-2026-10.txt`, `...-2027-01.txt` | schema validation PASS |
| `supported-versions-schema.json` | Shopify's supported-version list used for the version finding |
| `SHA256SUMS` | hashes of the above |

## 5. Findings for QA to decide (not changed; the candidate is frozen)

1. **Low:** `config.Settings.admin_api_version` defaults to `"2025-10"`, which Shopify no longer lists as a
   supported Admin API version. The QA config sets `2026-10` explicitly. Proposed one-line fix: default
   `"2026-10"` plus the matching path assertion in `test_verifier.GraphQL.test_paid_order_lines`.

## 6. Rollback

Unpublish the product (stops sales), uninstall the app or remove the webhook subscriptions, stop the
`commerce` container. Nothing is consumed while stopped; paid-but-unfulfilled orders are fulfilled after
restart (`--recover-order`, `--reconcile-once`) or refunded. The database holds no birth data or PDFs. No engine,
report or preview file is changed by the commerce package, so nothing else needs rolling back. In code: revert
PR #85 alone; PR #86 is independent.
