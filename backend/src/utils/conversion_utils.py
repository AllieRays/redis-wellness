"""Unit conversion utilities for health data (pure functions)."""


def convert_weight_to_lbs(value_str: str, unit: str | None = None) -> str:
    """
    Convert weight from kg to lbs for US display.

    Args:
        value_str: Weight value as string (e.g., "72.5" or "72.5 kg")
        unit: Optional unit string ("kg", "lb", etc.)

    Returns:
        Formatted string with lbs value (e.g., "159.8 lbs")

    Examples:
        convert_weight_to_lbs("72.5", "kg") → "159.8 lbs"
        convert_weight_to_lbs("72.5 kg") → "159.8 lbs"
        convert_weight_to_lbs("160", "lb") → "160.0 lbs"
        convert_weight_to_lbs("72.5") → "159.8 lbs" (assumes kg)
    """
    try:
        # Extract numeric value
        value_str = str(value_str).strip()

        # Remove unit if present in the value string
        if " kg" in value_str.lower():
            value_str = value_str.lower().replace("kg", "").strip()
            unit = "kg"
        elif " lb" in value_str.lower():
            value_str = value_str.lower().replace("lb", "").replace("lbs", "").strip()
            unit = "lb"

        value = float(value_str)

        # Convert if in kg
        if unit and "kg" in unit.lower():
            lbs_value = value * 2.20462
            return f"{lbs_value:.1f} lbs"
        elif unit and "lb" in unit.lower():
            return f"{value:.1f} lbs"
        else:
            # Assume kg if no unit specified (Apple Health default)
            lbs_value = value * 2.20462
            return f"{lbs_value:.1f} lbs"

    except (ValueError, TypeError):
        return value_str  # Return original if conversion fails


def kg_to_lbs(kg: float) -> float:
    """
    Convert kilograms to pounds.

    Args:
        kg: Weight in kilograms

    Returns:
        Weight in pounds

    Examples:
        kg_to_lbs(72.5) → 159.83
        kg_to_lbs(100) → 220.46
    """
    return kg * 2.20462


def lbs_to_kg(lbs: float) -> float:
    """
    Convert pounds to kilograms.

    Args:
        lbs: Weight in pounds

    Returns:
        Weight in kilograms

    Examples:
        lbs_to_kg(160) → 72.57
        lbs_to_kg(220.46) → 100.0
    """
    return lbs / 2.20462
