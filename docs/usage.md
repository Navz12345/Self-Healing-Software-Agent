# Usage

## US-01

Run `python inject_failure.py --type divide_by_zero` and inspect Docker logs for the repair trace.

## US-02

Run `python inject_failure.py --type infra_crash` and inspect Docker logs for restart confirmation.

## US-03

Run the divide-by-zero scenario a second time and inspect logs for `FMG_FAST_PATH_FIRED` and `GPT4O_SKIPPED`.

## US-04

Run `python inject_failure.py --type ambiguous` and inspect logs for `ESCALATION_REQUIRED`.

## US-05

Trigger a code bug and inspect logs for `RAG_RETRIEVED`.
