# Changelog

Notable changes of the `intelion-cloud` SDK. GitHub Releases add an
auto-generated list of merged commits on top of this file.

## 0.7.0 (unreleased)

Pairs with the pricing-plans revision on the server (rental terms). Do not tag
before that server change is in production: the fields below would be empty.

### Auto-renewal under a rental term

- `cloud_servers.update(id, is_auto_renewal=True)` under a running confirmed
  term now fails with `ConflictError` (409), `error_code`
  `AUTO_RENEWAL_CONSENT_REQUIRED`: turning auto-renewal on extends the term and
  needs a signed consent, so it is possible only in the web panel. Before the
  first start under an accepted consent (`term_state == "pending_consent"`) and
  on an ended, not stopped term the code is `AUTO_RENEWAL_NOT_APPLICABLE`.
  Turning it off (`False`) is always accepted; off a term nothing changed.
- `cloud_servers.start(id, is_auto_renewal=...)` under a term ignores the
  argument: the toggle stays as in the signed consent document, the call still
  succeeds. A start during a term renewal fails with `ConflictError`,
  `error_code` `TERM_RENEWAL_IN_PROGRESS`: retry in about a minute.
- `cloud_servers.migrate(id, flavor_id=..., price_plan=...)` to a price plan
  with a term (1, 3, 6 or 12 months) fails with `ConflictError` (409),
  `error_code` `TERM_CONDITIONS_REQUIRED`, unless the term conditions were
  accepted in the web panel for that exact flavor and term. A running server
  already behaved this way; now the same applies to a server that has not been
  started yet, including one whose accepted conditions are for another flavor
  or term (before, the change went through and the 409 came on `start`).
  Nothing is changed on refusal.
- New `APIError.error_code` property and `TermConflictCode` constants to
  branch on these refusals instead of the Russian message.

### Removed and panel-only endpoints

- `PUT /api/v2/cloud-servers/{id}/` is gone and answers 405: use `PATCH`
  (`cloud_servers.update`). The SDK never sent `PUT`, so no code change.
- Signing term documents (term conditions, term renewal, turning auto-renewal
  on under a term, rental termination: the panel endpoints under
  `/lk/cloud-servers/{id}/`) is possible only by the client in the web panel
  session: with an API token these calls answer 403. The SDK has no wrappers
  for them. The termination quote (`GET .../termination-quote/`) still
  accepts a token.

### Launch check

- `ServerStatus.launch_funds_rub_cents`: the client's money the start gate
  compares with `launch_required_rub_cents`. For an individual on a confirmed
  term plan it excludes the overdraft limit and can be negative. A legacy term
  without a signed consent (`term_conditions_accepted_at` is empty) still
  launches on the free balance including the limit. `None` when the server
  cannot be started or on an older server.

### Earlier in this release

- `CloudServer`: rental-term fields (`term_*`, `is_renewal_mandatory`,
  `is_bound_by_term`, `billing_cycle_months`, `pays_term_monthly` and others),
  cold-storage fields (`cold_storage`, `cold_free`, `resume_usage_act` and
  others).
- `User.is_term_business`.
- `UsageAct`: cost and discount fields (`next_charge_rub_cents`,
  `full_period_cost_rub_cents`, `full_planned_cost_rub_cents`,
  `discount_percent`, `promocode_code`, `promocode_discount_value`).
- `ServerStatus`: `launch_required_rub_cents`,
  `is_enough_money_for_full_period`, `remaining_monthly_seconds`.
- `APIError.reason` and `ServerCreateRejectReason` for `POST cloud-servers/`
  refusals.
