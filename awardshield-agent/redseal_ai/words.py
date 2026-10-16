"""words.py - an amount written in words -> a number (Indian and international usage). Pure Python.

    words_to_number("Rupees Sixty Six only per kilometre")              -> 66.0
    words_to_number("Rupees Sixty Four and Fifty paise per kilometre")  -> 64.5
    words_to_number("Rupees One Crore Twenty Lakh")                     -> 12000000.0

Used by the prover to VERIFY a figure-vs-words challenge without trusting the model's reading.
"""

import re

UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
         "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
         "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "lakhs": 100_000, "lac": 100_000,
          "crore": 10_000_000, "crores": 10_000_000, "million": 1_000_000, "billion": 1_000_000_000}
SUBUNIT = ("paise", "paisa", "cents", "cent")


def _integer(tokens: list[str]) -> int | None:
    total, current, seen = 0, 0, False
    for t in tokens:
        if t in UNITS:
            current += UNITS[t]
        elif t in TENS:
            current += TENS[t]
        elif t == "hundred":
            current = (current or 1) * 100
        elif t in SCALES:
            total += (current or 1) * SCALES[t]
            current = 0
        else:
            continue
        seen = True
    return total + current if seen else None


def words_to_number(text: str) -> float | None:
    """The amount in `text`, or None when no number word is found. A sub-unit (paise / cents) is the part
    after the LAST 'and' that ends with the sub-unit word: '<main> and <n> paise'."""
    t = re.sub(r"[^a-z ]+", " ", text.lower())
    t = re.sub(r"\b(rupees?|rs|inr|only|per|kilomet(re|er)s?|km|a)\b", " ", t)
    words = t.split()
    sub = next((i for i, w in enumerate(words) if w in SUBUNIT), None)
    if sub is not None and "and" in words[:sub]:
        cut = sub - 1 - words[:sub][::-1].index("and")
        main, frac = words[:cut], words[cut + 1:sub]
    else:
        main, frac = (words[:sub] if sub is not None else words), []
    main = [w for w in main if w != "and"]
    whole = _integer(main)
    if whole is None:
        return None
    cents = _integer(frac) if frac else 0
    return round(whole + (cents or 0) / 100, 2)
