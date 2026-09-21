from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def parse(grammar, string, start="S"):
    return client.post("/api/parse", json={"grammar": grammar, "string": string, "start_symbol": start}).json()


def test_parse_tokenizes_compact_and_spaced_strings():
    grammar = "S -> aSb | ε"
    for value in ("aabb", "a a b b", "ab", "", "ε"):
        assert parse(grammar, value)["accepted"]
    for value in ("aab", "abab", "ba"):
        assert not parse(grammar, value)["accepted"]


def test_parse_reports_unknown_symbols():
    result = parse("S -> aSb | ε", "aabc")
    assert result == {
        "accepted": False,
        "derivation": [],
        "parse_tree": None,
        "error": "Unknown symbol 'c'.",
    }


def test_parse_uses_longest_terminal_match():
    result = parse("S -> id + id", "id+id")
    assert result["accepted"]


def ask(grammar, question, start="S"):
    return client.post("/api/ask", json={"grammar": grammar, "question": question, "start_symbol": start}).json()["answer"]


def test_assistant_uses_current_analysis_for_first_follow_and_ll1():
    grammar = "S -> aSb | ε"
    first_follow = ask(grammar, "Calculate FIRST and FOLLOW.")
    assert "FIRST(S)\n{ a, ε }" in first_follow
    assert "FOLLOW(S)\n{ $, b }" in first_follow
    assert "'a' is included because S → a S b begins with 'a'." in first_follow
    assert "'$' is included because S is the start symbol." in first_follow
    ll1 = ask(grammar, "Why is this grammar not LL(1)?")
    assert "actually LL(1)" in ll1
    assert "no LL(1) conflicts" in ll1


def test_assistant_uses_transformation_data_for_left_recursion():
    answer = ask("E -> E + T | T\nT -> t", "Where is the left recursion?", "E")
    assert "E → E + T" in answer
    assert "E → T E'" in answer