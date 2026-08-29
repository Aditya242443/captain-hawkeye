import sys
from pathlib import Path
from datetime import datetime

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.anpr.validation import (
    is_valid_standard,
    is_valid_bh,
    is_valid_relaxed,
    validate_plate,
    correct_positional_characters,
    majority_vote,
)


# =============================================================================
# 1. Indian License Plate Regex Validator Tests
# =============================================================================

def test_valid_standard_plates():
    valid_plates = [
        "DL01AB1234",
        "MH12A1234",
        "KA05MJ9999",
        "HR26DQ5555",
        "UP32AZ0001",
        "TN09B1234",
    ]
    for plate in valid_plates:
        assert is_valid_standard(plate) is True, f"Failed standard validation for {plate}"
        is_val, fmt = validate_plate(plate)
        assert is_val is True
        assert fmt == "standard"


def test_valid_bh_series_plates():
    valid_bh = [
        "22BH1234AA",
        "21BH9876A",
        "24BH0001Z",
        "23BH5432XY",
    ]
    for plate in valid_bh:
        assert is_valid_bh(plate) is True, f"Failed BH series validation for {plate}"
        is_val, fmt = validate_plate(plate)
        assert is_val is True
        assert fmt == "bh_series"


def test_valid_relaxed_plates():
    valid_relaxed = [
        "DL01ABC1234",
        "MH02A1",
        "KA01B12",
        "HR01CD123",
    ]
    for plate in valid_relaxed:
        assert is_valid_relaxed(plate) is True
        is_val, fmt = validate_plate(plate)
        assert is_val is True


def test_invalid_plates():
    invalid_plates = [
        "1234",
        "DL",
        "INVALIDPLATE12345",
        "1234DL5678",
        "D!01AB1234",
        "DL 01 AB 1234",
        "",
        "ZZZZZZZZZZ",
    ]
    for plate in invalid_plates:
        assert is_valid_standard(plate) is False
        assert is_valid_bh(plate) is False


# =============================================================================
# 2. Positional Character Correction Tests
# =============================================================================

def test_correct_letter_o_to_digit_0():
    raw = "DLOIAB1234"
    corrected = correct_positional_characters(raw)
    assert corrected == "DL01AB1234"
    assert is_valid_standard(corrected)


def test_correct_digit_8_to_letter_b():
    raw = "DL01A81234"
    corrected = correct_positional_characters(raw)
    assert corrected == "DL01AB1234"
    assert is_valid_standard(corrected)


def test_correct_digit_6_to_letter_g():
    raw = "DL01A61234"
    corrected = correct_positional_characters(raw)
    assert corrected == "DL01AG1234"
    assert is_valid_standard(corrected)


def test_correct_digit_1_and_2_in_digits():
    raw = "MHIZAA5678"
    corrected = correct_positional_characters(raw)
    assert corrected == "MH12AA5678"
    assert is_valid_standard(corrected)


def test_correct_letter_s_to_digit_5():
    raw = "DLS1AB1234"
    corrected = correct_positional_characters(raw)
    assert corrected == "DL51AB1234"
    assert is_valid_standard(corrected)


def test_correct_bh_series_digits():
    raw = "O1BHI234AA"
    corrected = correct_positional_characters(raw)
    assert corrected == "01BH1234AA"
    assert is_valid_bh(corrected)


def test_already_valid_plate_unchanged():
    valid = "DL01AB1234"
    assert correct_positional_characters(valid) == valid


# =============================================================================
# 3. Multi-Frame Majority Voting Tests
# =============================================================================

def test_majority_agreement():
    candidates = [
        ("DL01AB1234", 0.95),
        ("DLO1AB1234", 0.85),  # Corrects to DL01AB1234
        ("DL01AB1234", 0.90),
        ("MH12AA5678", 0.70),
    ]
    chosen, conf = majority_vote(candidates)
    assert chosen == "DL01AB1234"
    assert conf > 0.80


def test_tie_breaking_by_confidence():
    candidates = [
        ("DL01AB1234", 0.75),
        ("MH12AA5678", 0.95),
    ]
    chosen, conf = majority_vote(candidates)
    assert chosen == "MH12AA5678"
    assert conf == 0.95


def test_empty_candidates():
    chosen, conf = majority_vote([])
    assert chosen == ""
    assert conf == 0.0


# =============================================================================
# Main Execution Runner
# =============================================================================

if __name__ == "__main__":
    test_valid_standard_plates()
    test_valid_bh_series_plates()
    test_valid_relaxed_plates()
    test_invalid_plates()
    test_correct_letter_o_to_digit_0()
    test_correct_digit_8_to_letter_b()
    test_correct_digit_6_to_letter_g()
    test_correct_digit_1_and_2_in_digits()
    test_correct_letter_s_to_digit_5()
    test_correct_bh_series_digits()
    test_already_valid_plate_unchanged()
    test_majority_agreement()
    test_tie_breaking_by_confidence()
    test_empty_candidates()
    print("[PASS] All backend/tests/test_anpr.py unit tests passed successfully!")
