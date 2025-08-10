from typing import Any

from django.db import models


class DeserializationError(ValueError):
    pass


class SerializationError(ValueError):
    pass


class Arguments:
    HASH_KEY = "__rq_hash__"
    MODEL_KEY = "__rq_model__"

    @classmethod
    def serialize_args_and_kwargs(cls, args, kwargs) -> dict[str, Any]:
        return {
            "args": cls.serialize(args) if args else [],
            "kwargs": cls.serialize([kwargs]) if kwargs else {},
        }

    @classmethod
    def deserialize_args_and_kwargs(cls, data: dict[str, Any]) -> tuple[list, dict]:
        return (
            cls.deserialize(data["args"]) if data["args"] else [],
            cls.deserialize(data["kwargs"])[0] if data["kwargs"] else {},
        )

    @classmethod
    def serialize(cls, arguments):
        return [cls.serialize_argument(arg) for arg in arguments]

    @classmethod
    def deserialize(cls, arguments):
        try:
            return [cls.deserialize_argument(arg) for arg in arguments]
        except Exception as e:
            raise DeserializationError(f"Error deserializing arguments: {e}") from e

    @classmethod
    def serialize_argument(cls, argument):
        if isinstance(argument, (int, float, bool, str, type(None))):
            return argument
        elif isinstance(argument, (list, tuple)):
            return [cls.serialize_argument(item) for item in argument]
        elif isinstance(argument, dict):
            return {
                cls.HASH_KEY: {
                    key: cls.serialize_argument(value)
                    for key, value in argument.items()
                }
            }
        elif isinstance(argument, models.Model):
            return {
                cls.MODEL_KEY: {
                    "app_label": argument._meta.app_label,
                    "model": argument._meta.model_name,
                    "pk": argument.pk,
                }
            }

        raise SerializationError(f"Cannot serialize argument of type {type(argument)}")

    @classmethod
    def deserialize_argument(cls, argument):
        if isinstance(argument, (int, float, bool, str, type(None))):
            return argument
        elif isinstance(argument, list):
            return [cls.deserialize_argument(item) for item in argument]
        elif isinstance(argument, dict):
            if cls.HASH_KEY in argument:
                return {
                    key: cls.deserialize_argument(value)
                    for key, value in argument[cls.HASH_KEY].items()
                }
            elif cls.MODEL_KEY in argument:
                return cls._deserialize_model(argument[cls.MODEL_KEY])

        raise DeserializationError(
            f"Cannot deserialize argument of type {type(argument)}"
        )

    @classmethod
    def _deserialize_model(cls, model_data):
        from django.contrib.contenttypes.models import ContentType

        app_label = model_data["app_label"]
        model_name = model_data["model"]
        pk = model_data["pk"]
        content_type = ContentType.objects.get(app_label=app_label, model=model_name)
        return content_type.get_object_for_this_type(pk=pk)
