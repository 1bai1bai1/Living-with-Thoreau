"""The game master loop, with the model scripted."""

from app.gm import ApproveAction, SayAction, TripAction, TripBuy, stream_act, stream_next
from app.world import mills
from tests.conftest import ScriptedLLM, collect, text_of


def kinds(events):
    return [e["type"] for e in events]


async def open_scene(session, llm):
    return await collect(stream_next(session, llm))


async def say(session, llm, text):
    return await collect(stream_act(session, llm, SayAction(kind="say", text=text)))


async def test_a_scene_opens_with_narration_then_thoreau(session):
    llm = ScriptedLLM(gm=[[("text", "Ice groans on the pond."), ("call", "show_widget",
                                                                       {"component": "choices", "options": ["Borrow an axe", "Buy one"]})],
                          [("text", " The pines wait.")]],
                      thoreau=["Borrow one!"])
    events = await open_scene(session, llm)
    assert events[0]["type"] == "scene" and events[0]["scene"]["id"] == "axe"
    assert "Ice groans" in text_of(events, "narrator")
    widget = next(e for e in events if e["type"] == "widget")
    assert widget["component"] == "choices" and widget["props"]["options"] == ["Borrow an axe", "Buy one"]
    assert text_of(events, "thoreau") == "Borrow one!"
    assert events[-1]["type"] == "ready"
    assert session.state.phase == "open"


async def test_purchases_wait_for_approval(session):
    session.state.anchor_index = 1  # straight to Collins's shanty
    llm = ScriptedLLM(gm=[[("text", "Collins leans on his doorframe.")],
                          [("call", "acquire", {"material": "boards", "method": "shanty"})],
                          [("text", "Collins pockets the coins.")]],
                      thoreau=["(opening)", "There it is! A whole house for four dollars."])
    await open_scene(session, llm)
    events = await say(session, llm, "I'll take the shanty")
    assert kinds(events)[-2:] == ["approval_required", "ready"]
    ask = next(e for e in events if e["type"] == "approval_required")
    assert ask["title"] == "Spend $4.25?"
    assert session.state.money == mills(20)  # nothing spent yet

    events = await collect(stream_act(session, llm, ApproveAction(kind="approve", key=ask["key"], approved=True)))
    step = next(e for e in events if e["type"] == "step")
    assert "Spent $4.25" in step["lines"]
    assert session.state.owned == {"boards": "shanty"}
    assert "pockets the coins" in text_of(events, "narrator")
    start = next(e for e in events if e["type"] == "channel_start" and e["channel"] == "thoreau")
    assert start["tone"] == 2  # exactly his kind of choice
    assert session.state.drift == 2


async def test_a_material_is_never_counted_twice(session):
    session.state.anchor_index = 1
    llm = ScriptedLLM(gm=[[("text", "Collins waits.")],
                          [("call", "acquire", {"material": "boards", "method": "shanty"})],
                          [("call", "adjust_money", {"dollars": -4.25, "reason": "Paid Collins for the shanty"}),
                           ("call", "adjust_money", {"dollars": 4.25, "reason": "Bought Collins's shanty"}),
                           ("call", "spend_time", {"activity": "Taking the shanty apart", "hours": 8})],
                          [("text", "Collins pockets the coins.")]])
    await open_scene(session, llm)
    ask = next(e for e in await say(session, llm, "buy it") if e["type"] == "approval_required")
    events = await collect(stream_act(session, llm, ApproveAction(kind="approve", key=ask["key"], approved=True)))
    assert not any(e["type"] == "approval_required" for e in events)  # no second purchase to approve
    assert session.state.money == mills(20) - mills(4.25)
    assert session.state.hours_spent == 8  # the dismantling, counted once


async def test_declining_means_it_didnt_happen(session):
    session.state.anchor_index = 1
    llm = ScriptedLLM(gm=[[("text", "Collins waits.")],
                          [("call", "acquire", {"material": "boards", "method": "shanty"})],
                          [("text", "You walk away.")]])
    await open_scene(session, llm)
    ask = next(e for e in await say(session, llm, "buy it") if e["type"] == "approval_required")
    await collect(stream_act(session, llm, ApproveAction(kind="approve", key=ask["key"], approved=False)))
    assert session.state.owned == {} and session.state.money == mills(20)
    _, contents = llm.gm_calls[-1]
    assert contents[-1].parts[0].function_response.response["declined"] is True


async def test_talking_to_thoreau_goes_to_thoreau(session):
    llm = ScriptedLLM(gm=[[("text", "The woods are still.")],
                          [("call", "pass_to_thoreau", {"player_words": "Henry, what would you do?"})]],
                      thoreau=["Hello.", "I'd borrow the axe, and bring it back sharper."])
    await open_scene(session, llm)
    events = await say(session, llm, "Henry, what would you do?")
    assert text_of(events, "narrator") == ""
    assert "sharper" in text_of(events, "thoreau")
    assert 'spoke to you directly: "Henry, what would you do?"' in llm.thoreau_prompts[-1].user
    assert session.contents[-1].role == "model"  # the conversation still alternates


async def test_thoreau_can_stay_silent(session):
    llm = ScriptedLLM(gm=[[("text", "Ice.")], [("text", "You look at the sky.")]], thoreau=["Hi.", "(silent)"])
    await open_scene(session, llm)
    events = await say(session, llm, "I look up at the sky")
    assert not any(e["type"] == "channel_start" and e["channel"] == "thoreau" for e in events)


async def test_a_scene_ends_only_when_its_goal_is_met(session):
    llm = ScriptedLLM(gm=[[("text", "Pines.")],
                          [("call", "end_beat", {"summary": "Skipped the work."})],
                          [("text", "Not yet, the timbers aren't cut.")],
                          [("call", "gain_item", {"key": "timber", "label": "Hewn pine timbers"}),
                           ("call", "end_beat", {"summary": "Borrowed an axe and hewed the frame."})],
                          [("text", "The timbers lie stacked.")],
                          [("text", "Collins's shanty sits by the tracks.")]])
    await open_scene(session, llm)
    first = await say(session, llm, "I'm done here")
    assert any(e["type"] == "step" and "isn't met yet" in (e.get("error") or "") for e in first)
    assert session.state.phase == "open"

    events = await say(session, llm, "I borrow an axe and cut the pines")
    done = next(e for e in events if e["type"] == "beat_complete")
    assert done["summary"] == "Borrowed an axe and hewed the frame."
    assert session.state.phase == "between"
    assert session.state.history[-1].startswith("An Axe and Some Pines:")

    nxt = await open_scene(session, llm)
    assert nxt[0]["scene"]["id"] == "shanty" and session.state.location == "railroad"
    assert len(session.contents) >= 1 and "new scene" in session.contents[0].parts[0].text


async def test_bad_widget_requests_go_back_to_the_model(session):
    llm = ScriptedLLM(gm=[[("call", "show_widget", {"component": "choices", "options": ["Just one"]})],
                          [("text", "Pines.")]])
    events = await open_scene(session, llm)
    assert not any(e["type"] == "widget" for e in events)
    _, contents = llm.gm_calls[-1]
    assert "error" in contents[-1].parts[0].function_response.response


async def test_the_trip_planner_resolves_then_the_game_master_narrates(session):
    session.state.anchor_index = 3  # Into Concord
    llm = ScriptedLLM(gm=[[("text", "The road to Concord.")], [("text", "The storekeeper wraps your nails.")]])
    await open_scene(session, llm)
    events = await collect(stream_act(session, llm, TripAction(kind="trip", stops=["store"],
                                                                buys=[TripBuy(material="nails", method="store")])))
    assert session.state.owned == {"nails": "store"}
    assert [e["type"] for e in events if e["type"] != "debug"][0] == "step"
    _, contents = llm.gm_calls[-1]
    assert "trip planner" in contents[-1].parts[0].text


async def test_a_model_failure_mid_turn_keeps_the_game(session):
    llm = ScriptedLLM(gm=[[("text", "Pines.")]], fail_on_round=2)
    await open_scene(session, llm)
    events = await say(session, llm, "look around")
    assert [e["type"] for e in events][-2:] == ["error", "ready"]
    assert session.contents[-1].role == "model"
    assert session.state.phase == "open"


async def test_the_game_master_can_invent_a_side_scene(session):
    llm = ScriptedLLM(gm=[[("text", "Pines.")],
                          [("call", "propose_side_scene", {"title": "A Woodchopper's Song",
                                                           "premise": "Alek Therien comes by singing.", "location": "woods"}),
                           ("call", "gain_item", {"key": "timber", "label": "Timber"}),
                           ("call", "end_beat", {"summary": "Cut the timbers."})],
                          [("text", "Done.")],
                          [("text", "A song comes through the trees.")]])
    await open_scene(session, llm)
    await say(session, llm, "I cut the pines")
    events = await open_scene(session, llm)
    assert events[0]["scene"]["title"] == "A Woodchopper's Song" and events[0]["scene"]["side"] is True
    assert session.state.anchor_index == 1  # the shanty still comes next


async def test_the_debug_panel_sees_every_decision(session):
    session.state.anchor_index = 1
    llm = ScriptedLLM(gm=[[("text", "Collins waits.")],
                          [("call", "acquire", {"material": "boards", "method": "shanty"})],
                          [("text", "Done.")]],
                      thoreau=["(opening)", "Yes!"])
    opened = await open_scene(session, llm)
    beat = next(e for e in opened if e["type"] == "debug" and e["kind"] == "beat")
    assert beat["beat"] == "shanty" and beat["offers"] == ["boards:shanty", "nails:salvage"]
    assert any(e["type"] == "debug" and e["kind"] == "round" and "CURRENT SCENE" in e["system"] for e in opened)

    ask = next(e for e in await say(session, llm, "buy it") if e["type"] == "approval_required")
    events = await collect(stream_act(session, llm, ApproveAction(kind="approve", key=ask["key"], approved=True)))
    debug = [e for e in events if e["type"] == "debug"]
    tool = next(e for e in debug if e["kind"] == "tool")
    assert tool["name"] == "acquire" and tool["status"] == "ok" and tool["score"] == 6
    thoreau = next(e for e in debug if e["kind"] == "thoreau")
    assert thoreau["alignment"] == 2 and thoreau["turn_score"] == 6 and thoreau["silent"] is False


async def test_the_first_want_gets_a_warning(session):
    llm = ScriptedLLM(gm=[[("text", "Pines.")],
                          [("call", "gain_item", {"key": "brass_lamp", "label": "A brass lamp",
                                                  "values_plus": ["superfluity", "comfort"]}),
                           ("call", "spend_time", {"activity": "Choosing a lamp", "hours": 1,
                                                   "values_plus": ["superfluity"]})],
                          [("text", "The lamp gleams on the stump.")]],
                      thoreau=["Hello.", "(silent)"])
    await open_scene(session, llm)
    events = await say(session, llm, "I buy a fine brass lamp for the house")
    assert session.state.wants == 1  # one lamp, one want, even when the model tags it twice
    assert session.state.happiness > 50  # a little lift: that's the trap
    assert "first want" in llm.thoreau_prompts[-1].user
    # He must speak even if the model tries to stay silent: the authored warning stands in.
    assert "That's how it starts" in text_of(events, "thoreau")



async def test_the_ending_is_written_once(session):
    from app import director

    director.fast_forward(session.state, "leaving")
    llm = ScriptedLLM(gm=[[("text", "The path to the pond is worn smooth.")],
                          [("call", "end_beat", {"summary": "Left the woods.", "outcome": "left"})],
                          [("text", "You shoulder your pack.")]],
                      thoreau=["(opening)", "(react)", "Two years, two months and two days.", "Go on, friend."])
    await open_scene(session, llm)
    await say(session, llm, "I close the door and walk to Concord")
    events = await open_scene(session, llm)
    ending = events[0]
    assert ending["type"] == "ending" and ending["title"] == "Leaving the Woods"
    assert ending["accounts"]["ending"] == "left" and ending["accounts"]["thoreau_spent_on_house"] == "$28.12½"
    assert text_of(events, "narrator") == "Two years, two months and two days."  # the epilogue
    assert text_of(events, "thoreau") == "Go on, friend."  # his last word
    calls = len(llm.thoreau_prompts)
    again = await open_scene(session, llm)  # a reload shows the same ending without asking the model again
    assert text_of(again, "thoreau") == "Go on, friend." and len(llm.thoreau_prompts) == calls


async def test_pay_for_all_of_it_covers_the_rest_of_the_turn(session):
    from app import director

    director.fast_forward(session.state, "chimney")
    llm = ScriptedLLM(gm=[[("text", "Cold.")],
                          [("call", "acquire", {"material": "bricks", "method": "old"})],
                          [("call", "acquire", {"material": "lime", "method": "casks"})],
                          [("call", "acquire", {"material": "mantle_iron", "method": "store"})],
                          [("text", "You load the cart.")]])
    await open_scene(session, llm)
    session.state.location, session.state.location_name = "village", "Concord village"  # walked in already
    ask = next(e for e in await say(session, llm, "buy the bricks, the lime and the iron") if e["type"] == "approval_required")
    events = await collect(stream_act(session, llm, ApproveAction(kind="approve", key=ask["key"], approved=True,
                                                                  all_this_turn=True)))
    assert not any(e["type"] == "approval_required" for e in events)
    assert {"bricks", "lime", "mantle_iron"} <= set(session.state.owned)
