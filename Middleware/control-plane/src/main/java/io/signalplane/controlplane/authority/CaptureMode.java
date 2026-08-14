package io.signalplane.controlplane.authority;

/**
 * Escalating intrusiveness. The mode determines who must approve, which is the
 * single idea this whole gate exists to express: reading corporate system metadata
 * and capturing a personal endpoint screen are not the same act and do not have the
 * same approving party.
 */
public enum CaptureMode {
    PASSIVE_METADATA(ApproverRole.EMPLOYER),
    CONTENT_CAPTURE(ApproverRole.EMPLOYER),
    TRIGGERED_SCREEN(ApproverRole.SUBJECT),
    CONTINUOUS_SCREEN(ApproverRole.SUBJECT),
    LANGUAGE_ANALYSIS(ApproverRole.DATA_PROTECTION_OFFICER);

    private final ApproverRole defaultApprover;

    CaptureMode(ApproverRole defaultApprover) {
        this.defaultApprover = defaultApprover;
    }

    public ApproverRole defaultApprover() {
        return defaultApprover;
    }
}
