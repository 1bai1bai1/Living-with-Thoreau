"""What a scene may ask the browser to show, checked strictly.

The same idea as the reference project's widgets: a scene (today authored,
later possibly chosen by the model) names a component and a few ids, the
server validates the request against these schemas, and widgets.py fills in
the real data. The browser renders from a fixed component registry.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter, field_validator


class MaterialCardSpec(BaseModel):
    """What a few materials cost, every way of getting them."""

    component: Literal["material_card"]
    materials: list[str] = Field(min_length=1, max_length=4)

    @field_validator("materials")
    @classmethod
    def _known(cls, ids: list[str]) -> list[str]:
        from .world import MATERIALS

        unknown = [i for i in ids if i not in MATERIALS]
        if unknown:
            raise ValueError(f"unknown materials: {unknown}")
        return ids


class TripPlannerSpec(BaseModel):
    """Plan one walk into Concord: which stops, what to buy."""

    component: Literal["trip_planner"]


class BlueprintSpec(BaseModel):
    """The house, stage by stage, and what each stage still needs."""

    component: Literal["blueprint"]


class LedgerSpec(BaseModel):
    """Every dollar and hour spent, beside Thoreau's own figures."""

    component: Literal["ledger"]


class ChoicesSpec(BaseModel):
    """Suggested next moves, shown as chips by the text box. Tapping one
    sends it as if the player had typed it."""

    component: Literal["choices"]
    options: list[Annotated[str, Field(min_length=1, max_length=80)]] = Field(min_length=2, max_length=4)


WidgetSpec = Annotated[
    ChoicesSpec | MaterialCardSpec | TripPlannerSpec | BlueprintSpec | LedgerSpec,
    Field(discriminator="component"),
]
WIDGET_ADAPTER: TypeAdapter[WidgetSpec] = TypeAdapter(WidgetSpec)
