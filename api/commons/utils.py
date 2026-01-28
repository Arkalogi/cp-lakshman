from sqlalchemy.inspection import inspect


def model_to_dict(model):
    if model is None:
        return None
    return {
        col.key: getattr(model, col.key) for col in inspect(model).mapper.column_attrs
    }


def model_list_to_dict(items):
    return [model_to_dict(item) for item in items]


def update_dict_from_schema(schema):
    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=True)
    return schema.dict(exclude_unset=True)


def generate_trading_symbol(
    exchange: str,
    underlying: str,
    instrument_type: str,
    expiry: str,
    strike: float = 0.0,
    option_type: str = "",
) -> str:
    if instrument_type == "EQ":
        return f"{exchange}-{underlying}"
    elif instrument_type == "FUT":
        return f"{exchange}-{underlying}-{expiry}"
    elif instrument_type == "OPT":
        strike_str = f"{strike:.1f}".rstrip("0").rstrip(".")
        return f"{exchange}-{underlying}-{expiry}-{strike_str}-{option_type}"
    else:
        raise ValueError(f"Invalid instrument type: {instrument_type}")
