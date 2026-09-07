# 2026-09-07 — Parallel Search API returned intermittent 401s

**Status:** resolved (provider incident)
**Window:** 14:52:50 – 15:19:24 CT, 2026-09-07
**Cause:** Parallel service incident — not this codebase, not the API key
**Official incident:** https://status.parallel.ai/incidents/01M1YPWEG0591HFNGSX2MM2RV2

## The lesson, if you only read one section

**Check https://status.parallel.ai and https://status.cerebras.ai before debugging a
third-party API failure.** This incident cost roughly an hour of bisecting headers,
request bodies, SDK internals, and connection pooling. The status page had the answer
the whole time, and checking it is free.

That misdirection was actively encouraged by the error message, which was wrong (see
below) — but the status page would still have short-circuited all of it.

## What it looked like

Roughly half of all Search API calls failed with HTTP 401, using a valid, freshly
regenerated key on an account with credits. **Identical requests repeated
back-to-back alternated between success and failure.**

```json
{"code":16,"message":"No API key provided (C.0)"}
```

The message was misleading: the key *was* present and correctly formatted. Code 16 is
gRPC `UNAUTHENTICATED`.

Reproduction used at the time (reads the key from `.env` without printing it):

```bash
K=$(grep '^PARALLEL_API_KEY=' .env | cut -d= -f2-)
for i in $(seq 1 12); do
  curl -s -o /dev/null -w "%{http_code} " \
    -X POST https://api.parallel.ai/v1/search \
    -H "x-api-key: $K" -H "Content-Type: application/json" \
    -d '{"objective":"t","search_queries":["Eiffel Tower height"],"mode":"advanced"}'
done; echo
# 401 401 401 401 401 401 200 200 401 401 401 401   → 2/12 succeeded
```

Impact: one fact-check makes ~7 Parallel calls, so the verdict half of the pipeline
failed essentially always. Claim extraction (Cerebras) was unaffected.

## How we knew it wasn't us

A control pair distinguished the failure from a bad credential:

| Request | Parallel response |
|---|---|
| No `x-api-key` header at all | `401: No API key provided (C.0)` |
| Deliberately invalid key | `401: Invalid API key (C.3)` |

During the incident, requests **that did send a valid header** received the
missing-key `C.0` response — meaning Parallel was dropping the credential upstream
rather than rejecting it. That, plus the published incident, locates the fault in
Parallel's request path.

Also ruled out at the time: key corruption (40 chars, no whitespace or quotes), a
stale key, shell env shadowing `.env`, the wrong auth header (`x-api-key` is correct;
`Authorization: Bearer` also failed), an SDK bug (raw curl reproduced it identically),
and request shape (bare and full bodies both succeeded *and* failed across repeats).

`search.py` and `get_parallel_client()` were never at fault and were not modified.

## If this recurs

1. **Check both status pages first** — https://status.parallel.ai and
   https://status.cerebras.ai.
2. Capture the response body and the `x-request-id` header (`curl -D -`) before
   changing anything.
3. Compare against the control pair above: a `C.3` "Invalid API key" means the
   credential really is bad; `C.0` while sending a header points at the provider.
4. Note that successful calls appear in Parallel's dashboard Run History with IDs
   matching `x-request-id`; failed 401s did not appear at all.

**Do not add retry-on-401 to the app.** Retrying authentication failures is wrong in
general and would mask genuine credential problems. The `parallel-web` SDK retries
408/409/429/5xx but deliberately not 401.

Remember that config is read and clients are cached **at import time**, so a process
restart is required after changing any key.

## Caveat on the test suite

All unit tests are offline by design (`tests/conftest.py` stubs both SDKs), so they
passed green throughout this incident. **The suite cannot catch a provider outage or a
credential problem** — confirming those requires live calls.
