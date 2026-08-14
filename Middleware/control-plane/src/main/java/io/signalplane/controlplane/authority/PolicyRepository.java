package io.signalplane.controlplane.authority;

import java.util.List;
import java.util.Optional;

public interface PolicyRepository {
    Optional<String> jurisdictionOfSubject(String tenantId, String subjectId);
    Optional<JurisdictionPolicy> forJurisdiction(String jurisdiction);
    boolean approvalOnRecord(String tenantId, String subjectId, CaptureMode mode, ApproverRole approver);
    List<AuthorityDecision.ScheduleWindow> scheduleWindows(String tenantId, String subjectId);
    String currentPolicyVersion();
}
