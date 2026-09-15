"""M4 dry-run policy sandbox."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from frostglass.detection.engine import DetectionEngine
from frostglass.detection.models import DetectionContext
from frostglass.masking.engine import BlockedContentError, MaskingEngine
from frostglass.masking.models import MaskingContext, MaskingMode
from frostglass.policy.engine import PolicyEngine

router = APIRouter(prefix="/admin/policy", tags=["policy"])


class PolicyTestRequest(BaseModel):
    """The dashboard sandbox request. It cannot select a provider."""

    text: str = Field(min_length=1)
    user: str = "policy-test-user"
    team: str = "policy-test-team"
    model: str = "policy-test-model"


def configure(
    detection_engine: DetectionEngine,
    policy_engine: PolicyEngine,
    masking_engine: MaskingEngine,
    tenant_salt: str,
) -> None:
    @router.post("/test")
    async def test_policy(request: PolicyTestRequest) -> dict[str, Any]:
        findings = detection_engine.detect(
            request.text, DetectionContext(tenant_id=request.team, tenant_salt=tenant_salt)
        )
        evaluations = policy_engine.evaluate(findings, request.user, request.team, request.model)
        modes = {
            item.finding.entity_type: MaskingMode(item.decision.action) for item in evaluations
        }
        context = MaskingContext(request.team, "policy-test", "policy-test")
        try:
            masked_text = masking_engine.mask(request.text, findings, context, modes).text
        except BlockedContentError:
            masked_text = None
        return {
            "policy_version": policy_engine.version,
            "findings": [
                {
                    "entity_type": item.finding.entity_type,
                    "confidence": item.finding.confidence,
                    "detector": item.finding.detector,
                    "span": [item.finding.start, item.finding.end],
                    "action": item.decision.action,
                    "rule_id": item.decision.rule_id,
                    "reason": item.decision.reason,
                }
                for item in evaluations
            ],
            "masked_text": masked_text,
        }
