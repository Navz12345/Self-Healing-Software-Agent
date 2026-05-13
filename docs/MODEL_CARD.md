# Model Card

## Intended Use

This MVP demonstrates autonomous incident response for a controlled FastAPI service. It is intended for coursework, demos, and local experimentation.

## Limitations

The repair scope is intentionally narrow. The code repair path targets `app/payments.py`, and the DevOps path targets the `sha-app` container.

## Risks

Automated code changes can be unsafe outside a sandbox. This implementation validates before promotion and escalates low-confidence incidents.

## Out-of-Scope

Production deployment, secrets management, broad multi-service repair, and irreversible infrastructure actions are out of scope.
