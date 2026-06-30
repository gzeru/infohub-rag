def clean(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None

    return value