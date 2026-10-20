import re

from django.core.exceptions import ValidationError


# Colombian company NIT: nine digits followed by the verification digit.
NIT_PATTERN = re.compile(r"^(?P<number>\d{9})-(?P<check_digit>\d)$")

# DIAN verification weights for a nine-digit NIT.
NIT_WEIGHTS = (41, 37, 29, 23, 19, 17, 13, 7, 3)


def calculate_nit_check_digit(nit_number: str) -> int:
    """Calculate the verification digit for a nine-digit Colombian NIT."""
    if not re.fullmatch(r"\d{9}", nit_number):
        raise ValueError("The NIT number must contain exactly nine digits.")

    weighted_sum = sum(
        int(digit) * weight
        for digit, weight in zip(nit_number, NIT_WEIGHTS, strict=True)
    )
    remainder = weighted_sum % 11

    return remainder if remainder in (0, 1) else 11 - remainder


def validate_colombian_nit(value: str) -> str:
    """Validate the format and verification digit of a Colombian NIT."""
    match = NIT_PATTERN.fullmatch(value)

    if match is None:
        raise ValidationError(
            "Enter a valid NIT in the format 900123456-8.",
            code="invalid_nit_format",
        )

    nit_number = match.group("number")
    supplied_digit = int(match.group("check_digit"))
    expected_digit = calculate_nit_check_digit(nit_number)

    if supplied_digit != expected_digit:
        raise ValidationError(
            "The NIT verification digit is invalid.",
            code="invalid_nit_check_digit",
        )

    return value