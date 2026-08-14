# ADR-0005: The control plane stays off the telemetry hot path

**Status:** Accepted
**Date:** 2026-08-14

## Context
A single monitored endpoint emits continuous, bursty activity: focus changes, process starts, file operations, periodic captures. Volume per subject is orders of magnitude above the control interactions (session start, coverage discovery, policy resolution).

A centralized connector that both orchestrates control operations and aggregates telemetry synchronously becomes the bottleneck and couples two workloads with opposite profiles.

## Decision
Split the planes.

- **Control plane** (synchronous, low volume): subject resolution, authority decisions, session lifecycle, adapter registry, policy. Request/response.
- **Data plane** (asynchronous, high volume): adapter to bus to store. Never traverses the control plane.

Adapters resolve authority and subject identity once per session and cache the result for the session's bounded lifetime.

## Consequences
- Easier: scaling the two independently; control plane outage degrades new session starts but does not drop in flight telemetry.
- Harder: cached decisions can go stale within their window; expiry must be short enough that a revocation takes effect in an acceptable time.
- Revisit if: revocation latency requirements drop below the session cache window.
