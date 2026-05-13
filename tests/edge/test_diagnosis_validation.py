import pytest
from pydantic import ValidationError

from brain.diagnosis import DiagnosisOutput


def test_diagnosis_output_rejects_bad_confidence():
    with pytest.raises(ValidationError):
        DiagnosisOutput(
            failure_class="CODE_BUG",
            confidence=2.0,
            affected_component="sha-app",
            proposed_plan="PLAN_A",
            reasoning="bad confidence",
        )
