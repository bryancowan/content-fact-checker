# Hosting Options

This app is a [Streamlit](https://streamlit.io/) web app. That framework choice narrows down what kinds of hosting will actually work — this doc explains why, and lays out the realistic options if you've cloned this repo and want to put it somewhere other than your own laptop.

## What this app needs from a host

- **A persistent, long-running Python process.** `streamlit run web_app.py` starts a process that keeps running indefinitely — it is not a stateless script invoked per-request like PHP/CGI, and it is not a static site.
- **WebSocket support.** Streamlit keeps an open WebSocket connection per browser tab to push UI updates (progress bars, live results) back to the client. A host that only proxies plain HTTP request/response won't work.
- **Outbound internet access with no strict execution-time cap.** The app calls out to LLM/search APIs (Cerebras, Parallel) while a page is loading; a single fact-check can take upwards of a minute due to free-tier rate limits. Hosts that kill scripts after a short timeout (common on traditional shared hosting) will cut requests off mid-flight.
- **No database, no background workers.** State lives in the browser session's memory only. This simplifies hosting considerably — there's nothing stateful to provision or migrate.
- Python 3.13 (3.10+ likely works too — see the main [README](../../README.md)).

## Options that work

### Managed Python/container PaaS (recommended)

Platforms designed to run a long-lived web process are the best fit, since they match what Streamlit needs out of the box. Examples: [Render](https://render.com/), [Railway](https://railway.app/), [Fly.io](https://fly.io/), [Google Cloud Run](https://cloud.google.com/run), [Heroku](https://www.heroku.com/).

This repo ships a `render.yaml` you can use as a template:

```yaml
services:
  - type: web
    name: content-fact-checker
    runtime: python
    pythonVersion: "3.13"
    buildCommand: pip install -r requirements.txt
    startCommand: streamlit run web_app.py --server.headless true --server.address 0.0.0.0 --server.port $PORT
```

The pattern is the same on most of these platforms: point them at the repo, set `CEREBRAS_API_KEY` / `PARALLEL_API_KEY` as environment variables/secrets, and use the `streamlit run ... --server.port $PORT` start command shown above (swap `$PORT` for whatever env var the platform injects).

Paid tiers on these platforms (commonly $5–$25/mo for a small instance) generally keep the app "always on" with no cold start. Free tiers exist on most of them too, but come with a tradeoff — see below.

### Streamlit Community Cloud (free)

[Streamlit Community Cloud](https://streamlit.io/cloud) is a free hosting option built specifically for Streamlit apps, and this app already supports it out of the box — it reads secrets via `st.secrets` (falls back to `.env` locally) and supports an optional `APP_PASSWORD` secret to gate access behind a login screen.

The catch: free-tier apps go to sleep after **12 hours with no traffic**. The next visitor doesn't even get an automatic restart — they see a "this app has gone to sleep" screen and have to click a button to wake it, then wait through a cold start. Fine for a personal demo or low-traffic project; not great if you want consistently fast first loads for visitors.

### Virtual/cloud servers (VPS)

A VPS or cloud VM — [DigitalOcean](https://www.digitalocean.com/), [Linode](https://www.linode.com/), [AWS Lightsail](https://aws.amazon.com/lightsail/), or a VPS product from a traditional web host like HostGator, Bluehost, etc. — gives root access and can run `streamlit run` directly behind a process manager (systemd, supervisor) and a reverse proxy (nginx, Caddy) for TLS.

This works technically, but you're taking on the operational work a PaaS normally handles for you: OS patching, process supervision, TLS certificate renewal, and monitoring. It also tends to cost more per month than the equivalent small-instance tier on a managed PaaS, since VPS plans are usually sized (and priced) for running multiple services, not one small app.

## Options that don't work

### Traditional shared/cPanel web hosting

Standard "shared hosting" plans (the kind most web hosts sell for WordPress-style sites, often bundled with cPanel) generally **cannot run this app**, even though many of them advertise Python support:

- Shared hosting Python support (e.g., cPanel's "Setup Python App") is built around Passenger/WSGI — short-lived request/response processes, the model Flask or Django apps use. Streamlit doesn't fit that model; it needs one long-lived process holding open WebSocket connections.
- Shared hosting plans commonly cap CPU usage (e.g., ~25% per account), execution time per script (often ~30 seconds), and the number of simultaneous processes (often ~25). A fact-check request that legitimately takes over a minute, sitting behind an open WebSocket, runs straight into those limits.
- There's typically no way to bind to an arbitrary port or keep a background daemon running the way Streamlit requires.

If your only available hosting is a shared/cPanel plan, this app won't run there without switching frameworks (e.g., rewriting the UI in Flask/Django and dropping the WebSocket-based live progress updates) — at that point it's a different app, not a hosting change.

### Static site hosts

Hosts like GitHub Pages, Netlify, or Vercel's static hosting are built for pre-built static assets or serverless functions with short execution limits — neither fits a persistent Streamlit process with server-side LLM calls.

## Summary

| Hosting type | Works? | Notes |
|---|---|---|
| Managed PaaS (Render, Railway, Fly.io, etc.), paid tier | Yes | Best fit; always-on, minimal setup |
| Managed PaaS, free tier | Yes, with caveat | Cold start after a period of inactivity |
| Streamlit Community Cloud | Yes, with caveat | Free; sleeps after 12h idle, manual wake-up click + cold start |
| VPS / cloud server | Yes | Full control, but you own OS/process/TLS maintenance; often pricier than a small PaaS instance |
| Shared/cPanel hosting | **No** | Can't sustain a persistent WebSocket process; CPU/time/process limits will break it |
| Static site hosts | **No** | No support for a persistent server-side process |
