import re
import logging
from typing import List, Tuple, Optional, Dict
from collections import Counter

logger = logging.getLogger(__name__)

# Standard Indian License Plate Regexes
REGEX_STANDARD = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}$")
REGEX_RELAXED = re.compile(r"^[A-Z]{2}\d{2}[A-Z]{1,3}\d{1,4}$")
REGEX_BH_SERIES = re.compile(r"^\d{2}BH\d{4}[A-Z]{1,2}$")

# Positional Character Confusions Mappings
# Digit -> Letter (when a letter is expected at a given position)
DIGIT_TO_LETTER = {
    "0": "O",
    "1": "I",
    "2": "Z",
    "5": "S",
    "8": "B",
    "6": "G",
}

# Letter -> Digit (when a digit is expected at a given position)
LETTER_TO_DIGIT = {
    "O": "0",
    "I": "1",
    "Z": "2",
    "S": "5",
    "B": "8",
    "G": "6",
}


def is_valid_standard(plate_text: str) -> bool:
    """Checks if plate_text strictly matches standard Indian format (e.g. DL01AB1234, MH12A1234)."""
    return bool(REGEX_STANDARD.match(plate_text))


def is_valid_bh(plate_text: str) -> bool:
    """Checks if plate_text strictly matches Bharat series format (e.g. 22BH1234AA, 21BH1234A)."""
    return bool(REGEX_BH_SERIES.match(plate_text))


def is_valid_relaxed(plate_text: str) -> bool:
    """Checks if plate_text matches relaxed Indian plate format."""
    return bool(REGEX_RELAXED.match(plate_text))


def validate_plate(plate_text: str) -> Tuple[bool, str]:
    """
    Validates plate against Indian number plate formats.
    Returns:
    - (is_valid: bool, format_type: str)
      where format_type is 'standard', 'bh_series', 'relaxed', or 'invalid'
    """
    if not plate_text:
        return False, "invalid"

    clean_text = plate_text.strip().upper()

    if is_valid_standard(clean_text):
        return True, "standard"
    if is_valid_bh(clean_text):
        return True, "bh_series"
    if is_valid_relaxed(clean_text):
        return True, "relaxed"

    return False, "invalid"


def apply_pattern_correction(text: str, pattern: str) -> str:
    """
    Applies character confusion correction according to a template mask.
    Pattern characters:
    'L': expects uppercase letter
    'D': expects digit
    Any other character: expects exact character (e.g. 'B', 'H')
    """
    if len(text) != len(pattern):
        return text

    corrected = []
    for char, expected_type in zip(text, pattern):
        if expected_type == "L":
            # Must be a letter; convert if in confusion table
            corrected.append(DIGIT_TO_LETTER.get(char, char))
        elif expected_type == "D":
            # Must be a digit; convert if in confusion table
            corrected.append(LETTER_TO_DIGIT.get(char, char))
        else:
            # Expected specific literal character (e.g. 'B' or 'H')
            if char in DIGIT_TO_LETTER and DIGIT_TO_LETTER[char] == expected_type:
                corrected.append(expected_type)
            else:
                corrected.append(char)

    return "".join(corrected)


def correct_positional_characters(plate_text: str) -> str:
    """
    Applies positional OCR character corrections (O↔0, I↔1, Z↔2, S↔5, B↔8, G↔6)
    only in the direction that matches the expected character type at each position.

    Tries standard Indian formats and BH series templates.
    """
    if not plate_text:
        return ""

    raw = plate_text.strip().upper()

    # If already strictly valid, return as-is
    is_valid, _ = validate_plate(raw)
    if is_valid:
        return raw

    # Candidate template masks based on length:
    # Standard:
    #   Length 10: 'LLDDLLDDDD' (e.g., DL01AB1234)
    #   Length 9:  'LLDDLDDDD'  (e.g., DL01A1234)
    #   Length 11: 'LLDDLLLDDDD' (e.g., DL01ABC1234)
    # BH-Series:
    #   Length 10: 'DDBHDDDDLL' (e.g., 22BH1234AA)
    #   Length 9:  'DDBHDDDDL'  (e.g., 22BH1234A)

    length = len(raw)
    candidate_masks: List[str] = []

    if length == 10:
        # Check if 3rd and 4th characters are 'BH' or likely 'BH' (e.g. '8H', 'BH')
        middle_two = raw[2:4]
        if middle_two in ["BH", "8H", "6H", "88"]:
            candidate_masks.append("DDBHDDDDLL")
        candidate_masks.append("LLDDLLDDDD")
        candidate_masks.append("DDBHDDDDLL")
    elif length == 9:
        middle_two = raw[2:4]
        if middle_two in ["BH", "8H", "6H"]:
            candidate_masks.append("DDBHDDDDL")
        candidate_masks.append("LLDDLDDDD")
        candidate_masks.append("DDBHDDDDL")
    elif length == 11:
        candidate_masks.append("LLDDLLLDDDD")

    # Try applying candidate masks and return first valid match
    for mask in candidate_masks:
        corrected = apply_pattern_correction(raw, mask)
        is_valid, _ = validate_plate(corrected)
        if is_valid:
            return corrected

    # If no strict match, fallback to general prefix/suffix correction
    # Format: 2 letters at start, then digits, then letters, then digits
    if length >= 8:
        general_chars = list(raw)
        # First 2 positions are almost always letters (unless BH series starting with 2 digits)
        if not raw[2:4].startswith("BH"):
            general_chars[0] = DIGIT_TO_LETTER.get(general_chars[0], general_chars[0])
            general_chars[1] = DIGIT_TO_LETTER.get(general_chars[1], general_chars[1])
            # Positions 2 and 3 are digits
            if len(general_chars) > 3:
                general_chars[2] = LETTER_TO_DIGIT.get(general_chars[2], general_chars[2])
                general_chars[3] = LETTER_TO_DIGIT.get(general_chars[3], general_chars[3])
            # Last 4 positions are usually digits
            for i in range(max(4, len(general_chars) - 4), len(general_chars)):
                general_chars[i] = LETTER_TO_DIGIT.get(general_chars[i], general_chars[i])

            fallback_corrected = "".join(general_chars)
            is_valid, _ = validate_plate(fallback_corrected)
            if is_valid:
                return fallback_corrected

    return raw


def majority_vote(
    candidates: List[Tuple[str, float]],
    min_confidence: float = 0.3,
) -> Tuple[str, float]:
    """
    Given 2-3 OCR results (with their confidences) for the same vehicle track:
    1. Runs character correction + validation on each candidate.
    2. Groups candidates and calculates frequency & weighted confidence.
    3. Returns the plate string that appears most often (majority vote),
       or the highest-confidence one if all differ.

    Parameters:
    - candidates: List of (ocr_text, confidence) tuples

    Returns:
    - Tuple of (final_plate_text, final_confidence)
    """
    if not candidates:
        return "", 0.0

    valid_candidates: List[Tuple[str, float, bool]] = []

    for raw_text, conf in candidates:
        if not raw_text or conf < min_confidence:
            continue
        cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_text).upper()
        corrected = correct_positional_characters(cleaned)
        is_valid, _ = validate_plate(corrected)
        valid_candidates.append((corrected, conf, is_valid))

    if not valid_candidates:
        # Fallback to highest confidence raw candidate
        best_raw = max(candidates, key=lambda x: x[1])
        cleaned = re.sub(r"[^A-Za-z0-9]", "", best_raw[0]).upper()
        return correct_positional_characters(cleaned), best_raw[1]

    # Prioritize candidates that passed validation
    strictly_valid = [c for c in valid_candidates if c[2]]
    pool = strictly_valid if strictly_valid else valid_candidates

    # Count occurrences
    counts = Counter(item[0] for item in pool)
    max_count = max(counts.values())
    top_candidates = [plate for plate, count in counts.items() if count == max_count]

    if len(top_candidates) == 1:
        chosen_plate = top_candidates[0]
        # Average confidence for the winning plate
        matched_confs = [c[1] for c in pool if c[0] == chosen_plate]
        avg_conf = float(sum(matched_confs) / len(matched_confs))
        return chosen_plate, avg_conf

    # Tie-breaking: Choose the one with the highest maximum confidence
    best_candidate = max(
        [c for c in pool if c[0] in top_candidates],
        key=lambda x: x[1],
    )
    return best_candidate[0], best_candidate[1]
