# kokoro

A self-owned Kokoro-82M Wyoming-protocol TTS container image for the Home Assistant homelab.

Built from the official `python:3.12-slim` base — not from any third-party container image. We bake the model and voices in, install the Python dependencies ourselves, and ship our own server code.

## What this is

- **The image**: `ghcr.io/ageisen2000/kokoro` (built and pushed by the `cd` workflow on every push to `main`).
- **Baseline**: official `python:3.12-slim` + the public Kokoro-82M model files (SHA-256 checksum-verified `ADD`) + public Python packages (`wyoming==1.11.0`, `numpy>=2.0.2`, `kokoro-onnx[gpu]==0.4.5`) + `src/`.
- **Our code**: `src/main.py` — a fresh, self-owned implementation of the Wyoming protocol (`Describe` / `Synthesize`) over TCP or Unix socket. It is not a copy of any upstream code.

## Provenance

| | |
|---|---|
| Base | `python:3.12-slim` (official, maintained by Docker) |
| Model | Kokoro-82M (`kokoro-v1.0.onnx` + `voices-v1.0.bin`) — public weights from [thewh1teagle/kokoro-onnx](https://github.com/thewh1teagle/kokoro-onnx), pinned by checksum |
| Dependencies | `wyoming` (rhasspy/wyoming), `numpy`, [`kokoro-onnx`](https://pypi.org/project/kokoro-onnx/) (public) |

## Building locally

```bash
docker build -t ghcr.io/ageisen2000/kokoro:local .
docker run --rm --gpus all ghcr.io/ageisen2000/kokoro:local
```

The image builds and imports without a GPU; GPU is only used at inference time.

## CI / CD

- **`ci` (pull requests + pushes to `main`)** —
  - `gitleaks`: scans the full git history for secrets (no secrets are ever checked in).
  - `docker build` + runtime import smoke check (`import kokoro_onnx, wyoming`).
- **`cd` (pushes to `main`)** — logs into GHCR with `${{ secrets.GITHUB_TOKEN }}` (built-in, no personal credentials) and builds + pushes `ghcr.io/ageisen2000/kokoro:latest` and `:<full-sha>` to ghcr.

Both workflows use only the default `GITHUB_TOKEN` — **no secrets are checked in or required**.

## Upstream updates (dependabot)

Dependabot (`.github/dependabot.yml`) keeps this current:

- **pip** — `wyoming`, `numpy`, `kokoro-onnx` (and its `[gpu]` extra) as dependency PRs.
- **github-actions** — workflow actions (`checkout`, `build-push-action`, `login-action`).

Each change lands as a PR — that's the gate, not an automatic deploy.

## No secrets

- `GITHUB_TOKEN` is built-in and scoped to the repo; nothing else is used.
- Do not commit `.env`, credentials, or keys (gitignored: `.env`, `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `.keystore`).
- The `ci` workflow's gitleaks step fails the build if a secret is found in any commit history.

## Using this in the homelab

The Flux.ClusterAdmin `ai` app (`applications/ai/kokoro.yaml`) deploys the upstream image. To deploy this one, update that line to pin this image (e.g. `ghcr.io/ageisen2000/kokoro@sha256:<digest>`, keep the `ai:kokoro` imagepolicy comment) and reconcile the `ai` Kustomization. That's a deliberate change to the homelab repo, not part of this one — update it on merge, not before.
