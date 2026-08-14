package io.signalplane.controlplane;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Control plane: synchronous, low volume. Subject resolution, authority decisions,
 * session lifecycle, adapter registry.
 *
 * It is never on the telemetry path (ADR-0005). A control plane outage stops new
 * sessions from opening; it does not drop signals already in flight.
 */
@SpringBootApplication
public class ControlPlaneApplication {
    public static void main(String[] args) {
        SpringApplication.run(ControlPlaneApplication.class, args);
    }
}
