"""
Weight unit conversion utilities

Provides functions to convert between kg and lbs for display and aggregation.
All weights are stored in their original unit with a unit indicator.
Conversions happen at display/reporting time based on user preference.
"""
from typing import Optional
from app.models.workout import WeightUnit


# Conversion factor: 1 kg = 2.20462 lbs
KG_TO_LBS = 2.20462
LBS_TO_KG = 1 / KG_TO_LBS


def kg_to_lbs(kg: float) -> float:
    """Convert kilograms to pounds"""
    return kg * KG_TO_LBS


def lbs_to_kg(lbs: float) -> float:
    """Convert pounds to kilograms"""
    return lbs * LBS_TO_KG


def convert_weight(
    weight: float,
    from_unit: WeightUnit,
    to_unit: WeightUnit
) -> float:
    """
    Convert weight from one unit to another.
    
    Args:
        weight: The weight value to convert
        from_unit: The source unit (kg or lbs)
        to_unit: The target unit (kg or lbs)
    
    Returns:
        The converted weight value
    """
    if from_unit == to_unit:
        return weight
    
    if from_unit == WeightUnit.KG and to_unit == WeightUnit.LBS:
        return kg_to_lbs(weight)
    elif from_unit == WeightUnit.LBS and to_unit == WeightUnit.KG:
        return lbs_to_kg(weight)
    else:
        raise ValueError(f"Unknown unit conversion: {from_unit} -> {to_unit}")


def normalize_to_kg(weight: float, unit: WeightUnit) -> float:
    """
    Normalize a weight to kilograms for consistent aggregation.
    
    Use this when aggregating weights across exercises that may use different units.
    
    Args:
        weight: The weight value
        unit: The unit the weight is stored in
    
    Returns:
        The weight in kilograms
    """
    return convert_weight(weight, unit, WeightUnit.KG)


def normalize_to_lbs(weight: float, unit: WeightUnit) -> float:
    """
    Normalize a weight to pounds for consistent aggregation.
    
    Use this when aggregating weights across exercises that may use different units.
    
    Args:
        weight: The weight value
        unit: The unit the weight is stored in
    
    Returns:
        The weight in pounds
    """
    return convert_weight(weight, unit, WeightUnit.LBS)


def format_weight(
    weight: Optional[float],
    unit: WeightUnit,
    display_unit: Optional[WeightUnit] = None,
    precision: int = 1
) -> str:
    """
    Format a weight for display, optionally converting to user's preferred unit.
    
    Args:
        weight: The weight value (or None)
        unit: The unit the weight is stored in
        display_unit: The unit to display in (defaults to stored unit if None)
        precision: Decimal places to show
    
    Returns:
        Formatted string like "100.0 kg" or "220.5 lbs"
    """
    if weight is None:
        return "—"
    
    if display_unit and display_unit != unit:
        weight = convert_weight(weight, unit, display_unit)
        unit = display_unit
    
    return f"{weight:.{precision}f} {unit.value}"
