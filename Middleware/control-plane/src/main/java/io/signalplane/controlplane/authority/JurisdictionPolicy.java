package io.signalplane.controlplane.authority;

import java.time.Duration;
import java.util.List;
import java.util.Set;

/**
 * The governing rule follows the subject's location, not the tenant's headquarters.
 * A tenant based in one country with staff in another is the normal case, not an
 * edge case, and getting this backwards is the most expensive kind of mistake here.
 */
public record JurisdictionPolicy(
        String jurisdiction,
        String policyVersion,
        Set<CaptureMode> permittedModes,
        ApproverRole approverOverride,
        String basis,
        Duration maxDecisionLifetime,
        List<String> alwaysExcludedDestinations
) {
    public boolean permits(CaptureMode mode) {
        return permittedModes.contains(mode);
    }

    public ApproverRole approverFor(CaptureMode mode) {
        return approverOverride != null ? approverOverride : mode.defaultApprover();
    }
}
