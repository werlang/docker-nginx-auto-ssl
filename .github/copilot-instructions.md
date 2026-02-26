# Copilot Instructions for nginx-auto-ssl

## Project purpose and architecture
- This image wraps OpenResty + `lua-resty-auto-ssl` to auto-issue and renew TLS certs, then reverse-proxy traffic to upstream apps.
- Runtime flow spans multiple files:
  1. `Dockerfile` installs dependencies and copies `nginx.conf` + `snippets/*` into `/usr/local/openresty/nginx/conf/`.
  2. `entrypoint.py` mutates config templates based on env vars and generates `/etc/nginx/conf.d/*.conf` from `SITES`.
  3. OpenResty starts with `nginx.conf`, includes `resty-http.conf`, and loads generated `conf.d` server blocks.
- Cert lifecycle is handled by Lua hooks in `snippets/resty-http.conf` (init + hook server on `127.0.0.1:8999`) and `snippets/resty-server-https.conf` (`ssl_certificate_by_lua_block`).

## Critical file map
- `entrypoint.py`: env parsing, template substitution, force-https injection, and process startup.
- `nginx.conf`: top-level includes; HTTP default server + `include /etc/nginx/conf.d/*.conf;`.
- `snippets/server-proxy.conf`: template used for each `SITES` entry (`$SERVER_NAME`, `$SERVER_ENDPOINT`).
- `snippets/resty-http.conf`: OpenResty/Lua auto-ssl bootstrap and optional Redis adapter wiring.
- `snippets/resty-server-http.conf` + `snippets/force-https.conf`: ACME challenge and optional HTTP->HTTPS redirect.

## Project-specific conventions
- Keep env-variable names and string semantics exact (for example, `FORCE_HTTPS` only appends redirect include when value is exactly `"true"`).
- `SITES` supports either semicolon-separated or multiline values; each item must be `domain=endpoint`.
- Endpoint normalization in `entrypoint.py` strips URL scheme (`http://`) before writing `$SERVER_ENDPOINT`.
- If `SITES` is empty and `/etc/nginx/conf.d` is empty, fallback config is copied from `server-default.conf`.
- If changing template placeholders in `snippets/server-proxy.conf`, update `entrypoint.py` replacement logic in the same change.

## Build and run workflows
- Local image build: `docker build -t nginx-auto-ssl .`
- Multi-arch publish flow (project-maintained): `./build-docker.sh <tag>` (uses `docker buildx` for `linux/amd64,linux/arm64`).
- Local run (from README pattern):
  - `docker run -d --name nginx-auto-ssl -p 80:80 -p 443:443 -e ALLOWED_DOMAINS="example.com" -e SITES="example.com=app:80" -v ssl-data:/etc/resty-auto-ssl pswerlang/nginx-auto-ssl`
- Primary runtime verification: `docker logs nginx-auto-ssl` and inspect generated files in `/etc/nginx/conf.d`.

## Integration points and dependencies
- Base image: `openresty/openresty:alpine-fat`.
- ACME provider is configured via `LETSENCRYPT_URL` (production by default; staging supported).
- Certificate storage supports `file` (default volume `/etc/resty-auto-ssl`) or `redis` (`REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_KEY_PREFIX`).
- TLS parameters are centralized in `snippets/ssl.conf`; avoid duplicating TLS settings elsewhere.

## Agent guidance for edits
- For behavior changes, prefer minimal edits across `entrypoint.py` + affected snippet template(s) rather than broad nginx rewrites.
- Preserve include contracts (`resty-http.conf`, `resty-server-http.conf`, `resty-server-https.conf`) because README examples and custom user configs depend on them.
- When modifying env-driven behavior, update README examples/options if user-facing behavior changes.
