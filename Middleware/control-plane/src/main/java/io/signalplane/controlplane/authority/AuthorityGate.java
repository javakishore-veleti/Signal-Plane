package io.signalplane.controlplane.authority;

import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

/**
 * Issues the decision that must precede any capture session (ADR-0004).
 *
 * Deny is the default. Every branch that cannot positively establish authority
 * returns a denial with a reason, because a denial nobody can explain is
 * operationally indistinguishable from a bug and gets worked around.
 */
@Service
public class AuthorityGate {

    private final PolicyRepository policies;
    private final Clock clock;

    public AuthorityGate(PolicyRepository policies, Clock clock) {
        this.policies = policies;
        this.clock = clock;
    }

    public AuthorityDecision evaluate(String tenantId, String subjectId, CaptureMode mode) {
        Instant now = clock.instant();

        var jurisdiction = policies.jurisdictionOfSubject(tenantId, subjectId);
        if (jurisdiction.isEmpty()) {
            return deny(tenantId, subjectId, mode, now,
                    "subject jurisdiction unresolved; cannot determine governing rule");
        }

        var policy = policies.forJurisdiction(jurisdiction.get());
        if (policy.isEmpty()) {
            return deny(tenantId, subjectId, mode, now,
                    "no policy on file for jurisdiction " + jurisdiction.get());
        }

        JurisdictionPolicy p = policy.get();
        if (!p.permits(mode)) {
            return deny(tenantId, subjectId, mode, now,
                    "capture mode " + mode + " not permitted in " + p.jurisdiction());
        }

        ApproverRole approver = p.approverFor(mode);
        if (!policies.approvalOnRecord(tenantId, subjectId, mode, approver)) {
            return deny(tenantId, subjectId, mode, now,
                    "no approval on record from " + approver + " for mode " + mode);
        }

        return new AuthorityDecision(
                UUID.randomUUID().toString(),
                tenantId,
                subjectId,
                mode,
                true,
                p.basis(),
                approver,
                p.jurisdiction(),
                p.policyVersion(),
                now,
                now.plus(p.maxDecisionLifetime()),
                policies.scheduleWindows(tenantId, subjectId),
                p.alwaysExcludedDestinations(),
                null
        );
    }

    private AuthorityDecision deny(String tenantId, String subjectId, CaptureMode mode,
                                   Instant now, String reason) {
        return new AuthorityDecision(
                UUID.randomUUID().toString(), tenantId, subjectId, mode, false,
                null, null, null, policies.currentPolicyVersion(), now, null,
                List.of(), List.of(), reason);
    }
}
