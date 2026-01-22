from sqlalchemy.inspection import inspect


def model_to_dict(model):
    if model is None:
        return None
    return {col.key: getattr(model, col.key) for col in inspect(model).mapper.column_attrs}


def model_list_to_dict(items):
    return [model_to_dict(item) for item in items]


def update_dict_from_schema(schema):
    if hasattr(schema, "model_dump"):
        return schema.model_dump(exclude_unset=True)
    return schema.dict(exclude_unset=True)
