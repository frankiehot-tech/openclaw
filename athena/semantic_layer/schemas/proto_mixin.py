from typing import Any


class ProtoConvertible:
    def to_proto(self) -> dict[str, Any]:
        return self.model_dump(mode="python")  # type: ignore[attr-defined]

    @classmethod
    def from_proto(cls, data: dict[str, Any]) -> Any:
        return cls.model_validate(data)  # type: ignore[attr-defined]
