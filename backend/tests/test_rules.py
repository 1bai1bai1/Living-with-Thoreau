import pytest
from pydantic import ValidationError

from app import rules
from app.widget_specs import WIDGET_ADAPTER
from app.world import MATERIALS, THOREAU_HOUSE_TOTAL, THOREAU_TRANSPORT, fmt_money, mills

SHANTY_OFFERS = ["boards:shanty", "nails:salvage"]


def test_money_is_written_like_thoreaus_accounts():
    assert fmt_money(mills(28.125)) == "$28.12½"
    assert fmt_money(mills(4.25)) == "$4.25"
    assert fmt_money(mills(8.035)) == "$8.03½"
    assert fmt_money(-1000) == "-$1.00"
    assert fmt_money(1000, signed=True) == "+$1.00"


def test_materials_add_up_to_thoreaus_house():
    assert sum(m.thoreau_cost for m in MATERIALS.values()) + THOREAU_TRANSPORT == THOREAU_HOUSE_TOTAL


def test_the_shanty_and_its_nails(state):
    with pytest.raises(rules.RuleError, match="needs Collins's shanty"):
        rules.acquire(state, "nails", "salvage", SHANTY_OFFERS)
    step = rules.acquire(state, "boards", "shanty", SHANTY_OFFERS)
    assert state.money == mills(20) - mills(4.25) and state.hours_spent == 8
    assert step.score == 6  # frugality 2x2 + self-reliance 2
    rules.acquire(state, "nails", "salvage", SHANTY_OFFERS)
    assert state.owned == {"boards": "shanty", "nails": "salvage"}


def test_scene_offers_and_village_goods_have_their_places(state):
    with pytest.raises(rules.RuleError, match="isn't on offer"):
        rules.acquire(state, "boards", "shanty", [])
    with pytest.raises(rules.RuleError, match="sold in Concord village"):
        rules.acquire(state, "nails", "store", [])
    rules.move(state, "village")
    rules.acquire(state, "nails", "store", [])
    with pytest.raises(rules.RuleError, match="already has"):
        rules.acquire(state, "nails", "store", [])


def test_cant_overspend(state):
    state.money = mills(1.00)
    with pytest.raises(rules.RuleError, match="costs \\$4.25"):
        rules.acquire(state, "boards", "shanty", SHANTY_OFFERS)
    with pytest.raises(rules.RuleError, match="costs \\$2.00"):
        rules.adjust_money(state, -2, "A hired plow", {})


def test_the_house_goes_up_in_order(state):
    with pytest.raises(rules.RuleError, match="Build the frame first"):
        rules.build(state, "shell", 30)
    with pytest.raises(rules.RuleError, match="Missing: timber"):
        rules.build(state, "frame", 6)
    rules.gain_item(state, "Timber", "Hewn pine timbers")
    rules.build(state, "frame", 6)
    assert rules.house_percent(state) == 25
    with pytest.raises(rules.RuleError, match="Missing: boards"):
        rules.build(state, "shell", 30)


def test_walking(state):
    assert state.location == "woods"
    rules.move(state, "village")
    assert state.hours_spent == 1 and state.location_name == "Concord village"
    rules.move(state, "cabin")
    assert state.hours_spent == 3
    rules.move(state, "The old Hosmer orchard", hours=2)
    assert state.location_name == "The old Hosmer orchard" and state.hours_spent == 5


def test_money_changes_are_bounded(state):
    rules.adjust_money(state, 50, "A mysterious inheritance", {})
    assert state.money == mills(30)  # at most $10 per call
    with pytest.raises(rules.RuleError):
        rules.adjust_money(state, 0, "Nothing", {})


def test_day_labor_is_in_the_village(state):
    with pytest.raises(rules.RuleError, match="Concord village"):
        rules.day_labor(state, "mending fences")
    rules.move(state, "village")
    rules.day_labor(state, "mending fences")
    assert state.money == mills(21)


def test_trips(state):
    with pytest.raises(rules.RuleError, match="isn't sold at the stops"):
        rules.apply_trip(state, ["yard"], {"nails": "store"})
    state.money = mills(3.00)
    rules.apply_trip(state, ["labor", "store"], {"nails": "store"})  # a day's labor pays for the nails
    assert state.money == mills(3.00) + mills(1.00) - mills(3.90)
    state.money = mills(5.00)
    second = rules.apply_trip(state, ["store"], {"hair": "store"})
    assert second.score == -2  # another trip


def test_alignment_and_mood():
    assert rules.turn_alignment(6) == 2
    assert rules.turn_alignment(2) == 1
    assert rules.turn_alignment(0) == 0
    assert rules.turn_alignment(-3) == -1
    assert rules.turn_alignment(-6) == -2
    assert [rules.mood(d) for d in (9, 0, -3, -9)] == ["kindred", "hopeful", "uneasy", "estranged"]
    assert rules.tags(["nature", "made_up"], ["comfort"]) == {"nature": 1, "comfort": -1}


def test_season_end_turns_free_hours_into_spirit(state):
    state.hours_left = 60
    rules.end_season(state)
    assert state.spirit == 7 and state.season_index == 1 and state.hours_left == 100
    state.hours_left = -30
    rules.end_season(state)
    assert state.spirit == 5


def test_widget_requests_are_validated():
    assert WIDGET_ADAPTER.validate_python({"component": "choices", "options": ["Sit", "Swim"]}).options == ["Sit", "Swim"]
    with pytest.raises(ValidationError):
        WIDGET_ADAPTER.validate_python({"component": "choices", "options": ["Only one"]})
    with pytest.raises(ValidationError):
        WIDGET_ADAPTER.validate_python({"component": "free_dragon"})
    with pytest.raises(ValidationError):
        WIDGET_ADAPTER.validate_python({"component": "material_card", "materials": ["gold_bars"]})
