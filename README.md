# kokoro

A custom, self-owned container image for the Kokoro-82M Wyoming-protocol TTS service used by Home Assistant — built from the pinned `nordwestt/kokoro-wyoming` NVIDIA CUDA base image.

## What this is

- **The custom image**: `ghcr.io/ageisen2000/kokoro` (built and pushed by the `cd` workflow on every push to `main`).
- **Baseline**: `nordwestt/kokoro-wyoming:cuda-1.0.2` (pinned by digest), the image the homelab already deploys — it bakes in the Kokoro-82M model, its voices, and the NVIDIA CUDA runtime.
- **Our own layer** (small, auditable): OCI image labels, `EXPOSE 10210`, and a TCP-port `HEALTHCHECK`. No source code is copied into this image; nothing is added beyond the base. This is a wrapper image, not a fork.

Why wrap instead of fork: the upstream repo — the only serious published CUDA variant of the Wyoming-protocol Kokoro serving stack — carries no license file, so we deliberately do **not** copy or redistribute its source code. We depend on its published image, track it, and own our own build on top.

## Provenance

| | |
|---|---|
| Base image | [`nordwestt/kokoro-wyoming`](https://hub.docker.com/r/nordwestt/kokoro-wyoming) |
| Base tag/digest | `cuda-1.0.2` / `sha256:128f9779cd7311382d2c51f1b54d6c50a37a44f831399ed3144cf919348ed961` |
| Upstream repo | [nordwestt/kokoro-wyoming](https://github.com/nordwestt/kokoro-wyoming) (23★, ~29.5k pulls, MIT/non-licensed, used for this homelab) |
| Model | Kokoro-82M (`kokoro-v1.0.onnx` + `voices-v1.0.bin`), baked into the base image |

The base image license / source: upstream ships no license file; the baked model is derived from [hexgrad/Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) (public weights, public `VOICES.md`). This wrapper adds no source. Keep this README updated when the base changes.

## Building locally

```bash
docker build -t ghcr.io/ageisen2000/kokoro:local .
docker run --rm --gpus all ghcr.io/ageisen2000/kokoro:local --uri tcp://0.0.0.0:10210
```

No test or publish step is required for local iteration — the base image is published. GPU is only required at runtime for inference; the image builds and imports fine without one.

## CI / CD

- **`ci` (pull requests + pushes to `main`)** —
  - `gitleaks`: scans the full git history for secrets (no secrets are ever checked in).
  - `docker build` + runtime import smoke check (`import kokoro_onnx, wyoming`).
- **`cd` (pushes to `main`)** — logs into GHCR with `${{ secrets.GITHUB_TOKEN }}` (built-in, no personal credentials) and builds + pushes `ghcr.io/ageisen2000/kokoro:latest` and `:<full-sha>` (immutable per-push tag) to ghcr.

Both workflows use only the default `GITHUB_TOKEN` — **no secrets are checked in or required**. Anything a fork/fork-sync would want for secrets does not belong here.

## Upstream updates (dependabot)

Dependabot (enabled; `.github/dependabot.yml`) keeps this image current:

- **Docker**: bumps the pinned base image digest/tag in the `FROM` line (e.g. `cuda-1.0.2` → a newer CUDA tag) when the upstream publishes new releases.
- **github-actions**: bumps workflow actions (checkout, build-push, login-action).

Each of these lands as a PR against `main` — the PR itself is the gate for applying base-image changes (including upstream changes), not an automatic deploy.

## No secrets

- GitHub Actions: `GITHUB_TOKEN` is built-in and scoped to the repo; nothing else is used.
- Do not commit `.env`, credentials, or keys (gitignored: `.env`, `*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `.keystore`).
- The `ci` workflow's gitleaks step fails the build if a secret is found in any commit history — the repo is never allowed to contain one.

## Using this in the homelab

The Flux.ClusterAdmin `ai` app (`applications/ai/kokoro.yaml`) currently deploys the upstream image directly. To deploy this custom one, drop this image into that deployment (pinned by digest, same annotation conventions — e.g. `ghcr.io/ageisen2000/kokoro@sha256:<digest>`) and reconcile the `ai` Kustomization. That's a deliberate change to the homelab repo, not part of this one — update it on merge, not before.
