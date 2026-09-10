from dataclasses import dataclass, field

import numpy as np


@dataclass
class SettlementLedger:
    original: np.ndarray
    interpretation: str = 'A'
    events: list = field(default_factory=list)

    def __post_init__(self):
        if self.interpretation not in ('A', 'B'):
            raise ValueError('Unknown settlement interpretation')
        self.original = np.asarray(self.original, dtype=float).copy()
        self.contract = self.original.copy()

    def revise(self, new_contract, effective_from, issue_time):
        new_contract = np.asarray(new_contract, dtype=float)
        if len(new_contract) != len(self.contract) or np.min(new_contract) < -1e-7:
            raise ValueError('Invalid revised contract')
        if not np.allclose(new_contract[:effective_from], self.contract[:effective_from], atol=1e-7, rtol=0):
            raise ValueError('Executed contract cannot be revised')
        delta = new_contract-self.contract
        if np.max(abs(delta)) <= 1e-7:
            return False
        self.events.append({'issue_time': str(issue_time), 'effective_from': effective_from,
                            'increase': np.maximum(delta, 0), 'decrease': np.maximum(-delta, 0)})
        self.contract = np.maximum(new_contract, 0).copy()
        return True

    def settle(self, price, emergency):
        price = np.asarray(price, dtype=float)
        increases = sum((e['increase'] for e in self.events), np.zeros_like(price))
        decreases = sum((e['decrease'] for e in self.events), np.zeros_like(price))
        if not np.allclose(self.contract, self.original+increases-decreases, atol=1e-6, rtol=0):
            raise AssertionError('Contract event reconciliation failed')
        fee_increase = 1.5*price*increases
        penalty_decrease = .5*price*decreases
        refund = price*decreases if self.interpretation == 'B' else np.zeros_like(price)
        ordinary = price*self.original
        emergency_fee = 5*price*np.asarray(emergency)
        return {'original_fee': ordinary, 'increase_fee': fee_increase,
                'decrease_penalty': penalty_decrease, 'refund': refund,
                'emergency_fee': emergency_fee,
                'total_fee': ordinary+fee_increase+penalty_decrease-refund+emergency_fee,
                'contract_increase': increases, 'contract_decrease': decreases}
