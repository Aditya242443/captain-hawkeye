"""
Standalone unit tests for ANPR validation logic (regex validation, positional correction, majority voting).
Requires only Python standard library.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.anpr.validation import (
    is_valid_standard,
    is_valid_bh,
    is_valid_relaxed,
    validate_plate,
    correct_positional_characters,
    majority_vote,
)

def test_standard_plates():
    valid_plates = ["DL01AB1234", "MH12A1234", "KA05MJ9999", "HR26DQ5555", "UP32AZ0001", "TN09B1234"]
    for plate in valid_plates:
        assert is_valid_standard(plate), f"Failed for {plate}"
        is_val, fmt = validate_plate(plate)
        assert is_val and fmt == "standard", f"Validation failed for {plate}"
    print("[PASS] Standard plates validation tests passed.")

def test_bh_series_plates():
    valid_bh = ["22BH1234AA", "21BH9876A", "24BH0001Z", "23BH5432XY"]
    for plate in valid_bh:
        assert is_valid_bh(plate), f"Failed for {plate}"
        is_val, fmt = validate_plate(plate)
        assert is_val and fmt == "bh_series", f"Validation failed for {plate}"
    print("[PASS] Bharat (BH) series validation tests passed.")

def test_relaxed_plates():
    relaxed = ["DL01ABC1234", "MH02A1", "KA01B12", "HR01CD123"]
    for plate in relaxed:
        assert is_valid_relaxed(plate), f"Failed for {plate}"
        is_val, _ = validate_plate(plate)
        assert is_val, f"Validation failed for {plate}"
    print("[PASS] Relaxed format validation tests passed.")

def test_invalid_plates():
    invalid = ["1234", "DL", "INVALIDPLATE12345", "1234DL5678", "D!01AB1234", "", "ZZZZZZZZZZ"]
    for plate in invalid:
        assert not is_valid_standard(plate), f"Should be invalid: {plate}"
        assert not is_valid_bh(plate), f"Should be invalid: {plate}"
    print("[PASS] Invalid plates rejection tests passed.")

def test_positional_corrections():
    # O -> 0 in digit position
    assert correct_positional_characters("DLOIAB1234") == "DL01AB1234"
    # 8 -> B in letter position
    assert correct_positional_characters("DL01A81234") == "DL01AB1234"
    # 6 -> G in letter position
    assert correct_positional_characters("DL01A61234") == "DL01AG1234"
    # I -> 1, Z -> 2 in digit positions
    assert correct_positional_characters("MHIZAA5678") == "MH12AA5678"
    # S -> 5 in digit position
    assert correct_positional_characters("DLS1AB1234") == "DL51AB1234"
    # BH-series: O -> 0, I -> 1 in digit positions
    assert correct_positional_characters("O1BHI234AA") == "01BH1234AA"
    # Unchanged
    assert correct_positional_characters("DL01AB1234") == "DL01AB1234"
    print("[PASS] Positional character correction tests passed.")

def test_majority_voting():
    candidates = [
        ("DL01AB1234", 0.95),
        ("DLO1AB1234", 0.85),  # Corrects to DL01AB1234
        ("DL01AB1234", 0.90),
        ("MH12AA5678", 0.70),
    ]
    chosen, conf = majority_vote(candidates)
    assert chosen == "DL01AB1234", f"Expected DL01AB1234, got {chosen}"
    assert conf > 0.85

    tie_candidates = [
        ("DL01AB1234", 0.75),
        ("MH12AA5678", 0.95),
    ]
    chosen_tie, conf_tie = majority_vote(tie_candidates)
    assert chosen_tie == "MH12AA5678", f"Expected MH12AA5678, got {chosen_tie}"
    assert conf_tie == 0.95
    print("[PASS] Multi-frame majority voting tests passed.")

if __name__ == "__main__":
    test_standard_plates()
    test_bh_series_plates()
    test_relaxed_plates()
    test_invalid_plates()
    test_positional_corrections()
    test_majority_voting()
    print("\nALL ANPR VALIDATION & CORRECTION TESTS PASSED SUCCESSFULLY!")
