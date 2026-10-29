from types import SimpleNamespace

from app.services.pilot_read import PilotReadService


class ScriptedClient:
    def __init__(self, results):
        self.results = list(results)

    def table(self, _name):
        return self

    def __getattr__(self, _name):
        return lambda *_args, **_kwargs: self

    def execute(self):
        return SimpleNamespace(data=self.results.pop(0))


def test_pilot_read_contains_only_admitted_style_evidence():
    service = PilotReadService(ScriptedClient([
        [{
            "id": "g1", "played_at": "2026-10-27T12:00:00Z", "opponent": "m_volkov",
            "result": "win", "user_color": "white", "time_control": "180",
            "game_analyses": [{"brilliant_pct": 2.9, "total_moves": 34}],
        }],
        [{"ply": 36, "san": "Rxe5", "is_brilliant": True, "signals": ["sacrifice"]}],
        [{"id": "f1", "game_id": "g1", "resonance": "yes", "comment": "It fits", "updated_at": "2026-10-28T12:00:00Z"}],
    ]))

    result = service.read("participant", "g1")

    assert result["headline"] == "You offered material by choice, and it held."
    assert result["moments"][0]["label"] == "19. Rxe5"
    assert result["feedback"]["resonance"] == "yes"
    assert not ({"chaos", "budget", "questions", "intention", "styleRead"} & result.keys())


def test_pilot_read_returns_none_for_a_game_outside_the_participant_scope():
    assert PilotReadService(ScriptedClient([[]])).read("participant-a", "participant-b-game") is None
