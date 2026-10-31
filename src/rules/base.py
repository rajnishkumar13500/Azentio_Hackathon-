from abc import ABC, abstractmethod
from typing import Optional, Any
from src.schemas import Claim, Policy, RuleResult

class BasePolicyRule(ABC):
    rule_id: str
    rule_name: str
    description: str

    @abstractmethod
    def evaluate(self, claim: Claim, policy: Policy, context: Optional[dict] = None) -> Any:
        """
        Evaluate the rule against the claim and policy.
        Returns a RuleResult or specific evaluation data.
        """
        pass

