package io.signalplane.controlplane.authority;

import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/v1/authority")
public class AuthorityController {

    private final AuthorityGate gate;

    public AuthorityController(AuthorityGate gate) {
        this.gate = gate;
    }

    public record DecisionRequest(String tenant_id, String subject_id, String capture_mode) {}

    @PostMapping("/decisions")
    public ResponseEntity<AuthorityDecision> decide(@RequestBody DecisionRequest req) {
        CaptureMode mode = CaptureMode.valueOf(req.capture_mode().toUpperCase());
        AuthorityDecision decision = gate.evaluate(req.tenant_id(), req.subject_id(), mode);
        // A denial is a well formed answer, not an error. Returning 200 with
        // granted=false keeps callers from treating denial as a transient failure
        // and retrying their way around the gate.
        return ResponseEntity.ok(decision);
    }
}
