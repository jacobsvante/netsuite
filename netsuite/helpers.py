import zeep.helpers


def to_builtin(obj, *, target_cls=dict):
    """
    Turn zeep XML object into python built-in data structures

    Args:
        target_cls (Type[dict]):
            Which type of dictionary type will be used for objects.
            As this project's minimum Python version officially supported is
            3.6 we can rely on the native sorted order of the standard `dict`
            class as a default.
    """
    return zeep.helpers.serialize_object(obj, target_cls=target_cls)
