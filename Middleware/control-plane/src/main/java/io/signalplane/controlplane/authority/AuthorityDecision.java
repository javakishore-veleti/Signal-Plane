package io.signalplane.controlplane.authority;

import java.time.Instant;
import java.util.List;

/**
 * Bounded permission to capture. Mirrors schemas/authority-decision.schema.json.
 *
 * expiresAt is non null by construction. An unbounded grant is a defect, not a
 * configuration choice (ADR-0004).
 */
public record AuthorityDecision(
        String decisionId,
        String tenantId,
        String subjectId,
        CaptureMode captureMode,
        boolean granted,
        String basis,
        ApproverRole approver,
        String jurisdiction,
        String policyVersion,
        Instant evaluatedAt,
        Instant expiresAt,
        List<ScheduleWindow> scheduleWindows,
        List<String> excludedDestinations,
        String denialReason
) {
    public AuthorityDecision {
        if (granted && expiresAt == null) {
            throw new IllegalArgumentException("granted decision without expiry");
        }
    }

    public record ScheduleWindow(List<String> days, String start, String end, String timezone) {}
}
