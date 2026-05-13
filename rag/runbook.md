## CODE_BUG

A CODE_BUG is a defect in application logic that causes runtime errors inside the target service. The strongest evidence is a recent spike in application error logs paired with a health endpoint that still responds. Common patterns include ZeroDivisionError when a denominator is unexpectedly zero, KeyError when a dictionary key is missing, and type conversion failures at runtime. Diagnosis steps: review the failing endpoint, inspect the stack trace for the exact function and line, and check recent commits that touched the failing module. Resolution: generate the smallest patch that fixes the exact operation, validate it in the sandbox service, then promote it to production only after the health check and tests pass. For this MVP, divide-by-zero in app/payments.py maps to PLAN_A.

## INFRA_CRASH

An INFRA_CRASH occurs when the service process or container terminates unexpectedly. The strongest evidence is a health endpoint that cannot be reached or returns a non-200 status while application logs do not show a matching Python exception from business logic. Common causes include the container being stopped, out-of-memory termination, disk exhaustion, or a failed process supervisor. Resolution: do not attempt code repair first. Restart the Docker container, wait for the health endpoint to return status ok, and notify operators if restart fails after repeated attempts. For this MVP, a stopped sha-app container maps to PLAN_C.

## AMBIGUOUS

When error rate is elevated but log errors are absent or inconsistent, the incident is ambiguous. This pattern occurs with intermittent failures, network partitions, upstream dependency degradation, or partial service timeouts. Do not apply automated fixes when confidence is below the threshold. Escalate to a human with raw signal values, recent commits, retrieved context, and the last few minutes of logs attached. The human should investigate upstream dependency health, configuration drift, and recent external changes before any automated repair is attempted. For this MVP, mixed intermittent failures should produce confidence below 0.60.

## SCHEMA_VIOLATION

A SCHEMA_VIOLATION occurs when a database schema change breaks one or more services that depend on that schema. The strongest evidence is database connection errors or query failures in the application logs such as column not found, constraint violation, or type mismatch, combined with a schema change detected by the Schema Drone. The error is consistent across requests and reproducible. Resolution: do not attempt code repair first. Identify the most recent database migration and evaluate whether rolling it back is safe. Run the rollback in the sandbox environment and confirm affected services reconnect successfully before applying to production. For this MVP, schema violations should be escalated to human review unless a direct rollback is safe.

## CONFIG_DRIFT

A CONFIG_DRIFT occurs when a configuration file or environment variable change degrades system behavior across multiple services simultaneously. The strongest evidence is a configuration file change correlated with fleet-wide health degradation that started at the same moment the config was pushed. Individual services may appear healthy in isolation while the fleet-level behavior has changed. Resolution: identify the most recent configuration push, compare it to the last known good configuration, and revert the change. Do not attempt code repair -- the application code is correct. For this MVP, config drift should trigger a config rollback via the DevOps agent.
