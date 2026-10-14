"""
FlowPilot FactGuard Adversarial Verification Suite
Exhaustively tests adversarial edge cases across negations, contractions,
numeric accuracy, currency, dates, commitments, and spoken self-corrections.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.writing_intelligence import WritingIntelligence, FactGuard

def test_factguard_adversarial():
    print("=" * 75)
    print("       FLOWPILOT FACTGUARD ADVERSARIAL INTEGRITY AUDIT")
    print("=" * 75)

    wi = WritingIntelligence()
    test_cases = [
        # 1. Contraction Negations
        {
            "id": "FG-01",
            "name": "Contraction Negation (didn't / without)",
            "raw": "We didn't approve the pull request without security review",
            "expect_safe": True,
            "must_contain": ["didn't", "without"]
        },
        # 2. Strong Negations (never / cannot)
        {
            "id": "FG-02",
            "name": "Absolute Negations (never / cannot)",
            "raw": "You must never deploy to production on Friday and cannot bypass tests",
            "expect_safe": True,
            "must_contain": ["never", "cannot"]
        },
        # 3. Numeric & Currency Precision
        {
            "id": "FG-03",
            "name": "Numeric & Currency Precision ($15,000 vs $150,000)",
            "raw": "The initial deposit is $15,000 and total commitment is $150,000",
            "expect_safe": True,
            "must_contain": ["15,000", "150,000"]
        },
        # 4. Spoken Numeric Self-Correction
        {
            "id": "FG-04",
            "name": "Numeric Spoken Self-Correction (5000 -> 6000)",
            "raw": "The project budget is 5000 -- actually 6000 dollars",
            "expect_safe": True,
            "must_contain": ["$6,000"],
            "must_not_contain": ["5000"]
        },
        # 5. Temporal Spoken Self-Correction (Tuesday -> Wednesday)
        {
            "id": "FG-05",
            "name": "Temporal Spoken Self-Correction (Tuesday -> Wednesday)",
            "raw": "Schedule the meeting for Tuesday -- actually, Wednesday at 2 PM",
            "expect_safe": True,
            "must_contain": ["Wednesday"],
            "must_not_contain": ["Tuesday"]
        },
        # 6. Negation Spoken Retraction (Do not -> do)
        {
            "id": "FG-06",
            "name": "Spoken Negation Retraction (do not -> do)",
            "raw": "Please do not proceed -- actually, proceed immediately",
            "expect_safe": True,
            "must_contain": ["proceed"],
            "must_not_contain": ["do not proceed"]
        },
        # 7. Adversarial Dropped Negation Detection (Simulated Hallucination)
        {
            "id": "FG-07",
            "name": "Adversarial Dropped Negation Guard",
            "raw": "We cannot sign the contract without legal review",
            "simulated_polished": "We sign the contract with legal review.",
            "is_direct_guard_test": True,
            "expect_fallback": True
        },
        # 8. Adversarial Numeric Alteration Detection (Simulated Hallucination)
        {
            "id": "FG-08",
            "name": "Adversarial Numeric Mutation Guard ($500,000 -> $50,000)",
            "raw": "Purchase order approved for $500,000",
            "simulated_polished": "Purchase order approved for $50,000.",
            "is_direct_guard_test": True,
            "expect_fallback": True
        },
        # 9. Adversarial Date Mutation Guard (Friday -> Monday)
        {
            "id": "FG-09",
            "name": "Adversarial Missing Number ($25,000 dropped)",
            "raw": "The invoice balance is $25,000 due immediately",
            "simulated_polished": "The invoice balance is due immediately.",
            "is_direct_guard_test": True,
            "expect_fallback": True
        },
        # 10. Complex Multiple Negations & Fractions
        {
            "id": "FG-10",
            "name": "Multiple Negations & Percentages (25% / neither / nor)",
            "raw": "Neither the 25% discount nor the free shipping applies without promo code",
            "expect_safe": True,
            "must_contain": ["Neither", "25%", "nor", "without"]
        }
    ]

    all_passed = True
    for tc in test_cases:
        cid = tc["id"]
        cname = tc["name"]
        raw = tc["raw"]

        if tc.get("is_direct_guard_test"):
            # Direct validation test against simulated bad polisher
            sim_pol = tc["simulated_polished"]
            final_text, is_safe, warnings = FactGuard.validate_and_guard(raw, sim_pol)
            passed = (is_safe is False and len(warnings) > 0 and final_text == raw)
            status = "PASS" if passed else "FAIL"
            print(f"\n[{cid}] {cname}: {status}")
            print(f"    Raw:       '{raw}'")
            print(f"    Simulated: '{sim_pol}'")
            print(f"    Guarded:   '{final_text}' (Safe={is_safe}, Fallback={not is_safe})")
            if not passed:
                all_passed = False
        else:
            # Full WritingIntelligence polish pipeline test
            res = wi.polish(raw, mode="polished", style="professional")
            final_text = res["text"]
            passed = True
            for mc in tc.get("must_contain", []):
                if mc.lower() not in final_text.lower():
                    passed = False
                    print(f"    FAIL: Missing expected token '{mc}'")
            for mnc in tc.get("must_not_contain", []):
                if mnc.lower() in final_text.lower():
                    passed = False
                    print(f"    FAIL: Found superseded token '{mnc}'")

            status = "PASS" if passed else "FAIL"
            print(f"\n[{cid}] {cname}: {status}")
            print(f"    Raw:     '{raw}'")
            print(f"    Polished:'{final_text}'")
            if not passed:
                all_passed = False

    print("\n" + "=" * 75)
    print(f"OVERALL FACTGUARD AUDIT RESULT: {'ALL TESTS PASSED' if all_passed else 'FAILURES DETECTED'}")
    print("=" * 75)
    return all_passed

if __name__ == "__main__":
    success = test_factguard_adversarial()
    sys.exit(0 if success else 1)
