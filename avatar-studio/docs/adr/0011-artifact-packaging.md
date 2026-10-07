# 0011 — Packaging for hosts that only serve text and media

**Status**: accepted

**Context.** The app is published as a static page inside a viewer that serves only text, images, media and fonts, blocks page-initiated downloads and scripts outside an allowlist.

**Decision.** The build uses stable file names and `tools/pack-artifact.mjs` emits an HTML fragment (CSS inline, one module script) plus the data as base64 text; the loader switches to base64 through a page flag. Files the app generates (screenshot, JSON) open in an in-page window so they can be saved or copied; storage is always wrapped in try/catch.

**Consequences.** The same source serves a normal host (binary gzip data) and the viewer (base64, +33% size). The look is deliberately a single dark theme, so the 3D stage and the panels agree.
