import re

from django.core.exceptions import ValidationError


def normalize_phone_number(value):
    value = re.sub(r"[\s()-]", "", value)

    if value.startswith("0"):
        value = "+254" + value[1:]
    elif value.startswith("254"):
        value = "+" + value

    if not re.fullmatch(r"\+[1-9]\d{7,14}", value):
        raise ValidationError(
            "Enter a valid international phone number, e.g. +254741082524."
        )

    return value
