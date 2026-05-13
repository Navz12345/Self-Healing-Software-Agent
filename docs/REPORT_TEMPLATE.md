# Assignment 3 Report

## 1. Methodology

- Student model choice and justification
- Primary student: Phi-3.5 Mini Instruct
- Fallback student: Qwen3-8B only if the primary path is blocked
- Alpaca dataset source and filtering steps
- Teacher-generated JSON dataset construction pipeline
- Teacher and judge: Llama 3.3 70B Instruct on UTSA
- UTSA HPC training setup and QLoRA hyperparameters
- Judge model choice and evaluation protocol

## 2. Experiments

### Three-checkpoint comparison

| Checkpoint | Alpaca Judge Win Rate | ROUGE-L / BERTScore | JSON Validity | Schema Compliance | Exact Match |
| --- | --- | --- | --- | --- | --- |
| Checkpoint 0 | TBD | TBD | TBD | TBD | TBD |
| Checkpoint 1 | TBD | TBD | TBD | TBD | TBD |
| Checkpoint 2 | TBD | TBD | TBD | TBD | TBD |

### Alpaca evaluation

- Held-out prompt source
- Judge comparisons: 0 vs 1, 1 vs 2, 0 vs 2
- Automatic metrics and output-length analysis

### JSON evaluation

- Validity, schema compliance, exact match, field-level F1
- Common error taxonomy

### Forgetting analysis

- Absolute score changes from checkpoint 1 to checkpoint 2
- Per-category regressions and improvements

### Ablation

- Pick at least one required ablation and summarize the retention tradeoff

## 3. Analysis

- Qualitative examples
- Failure cases
- Interpretation of forgetting versus retention

## 4. Prompt Engineering

- Teacher prompt evolution
- Judge prompt evolution
- What changed after failures were observed

## Appendix: Full Prompts

- Teacher generation prompt
- Judge prompt
- Inference prompt
