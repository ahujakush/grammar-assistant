from backend.grammar.engine import (
    analyze_grammar,
    build_ll1_table,
    compute_first_follow,
    left_factor,
    automaton_to_regex,
    build_automaton,
    minimize_dfa,
    nfa_to_dfa,
    parse_with_cyk,
    run_pipeline,
    remove_left_recursion,
    remove_unit_productions,
    remove_useless_symbols,
    to_cnf,
    to_gnf,
)


def test_cfg_with_epsilon():
    result = analyze_grammar("S -> aSb | ε")
    assert result["classification"]["code"] == 2
    assert result["properties"]["has_epsilon"]


def test_regular_grammar():
    result = analyze_grammar("S -> aA | b\nA -> aS | a")
    assert result["classification"]["code"] == 3
    assert result["automaton"]["transitions"]


def test_left_recursion_is_reported():
    result = analyze_grammar("E -> E + T | T")
    assert result["properties"]["has_left_recursion"]
    assert any("left recursion" in step["title"].lower() for step in result["steps"])


def test_unit_productions_are_removed():
    productions = [{"lhs": ["S"], "rhs": ["A"]}, {"lhs": ["A"], "rhs": ["a"]}]
    transformed, steps = remove_unit_productions(productions)
    assert {tuple(p["rhs"]) for p in transformed if p["lhs"] == ["S"]} == {("a",)}
    assert steps


def test_useless_symbols_and_left_factoring():
    productions = [
        {"lhs": ["S"], "rhs": ["a", "A"]},
        {"lhs": ["A"], "rhs": ["b"]},
        {"lhs": ["U"], "rhs": ["U"]},
    ]
    transformed, _ = remove_useless_symbols(productions)
    assert all(p["lhs"] != ["U"] for p in transformed)
    factored, steps = left_factor([
        {"lhs": ["A"], "rhs": ["a", "b"]},
        {"lhs": ["A"], "rhs": ["a", "c"]},
    ])
    assert any(p["lhs"] == ["A"] and p["rhs"] == ["a", "A'"] for p in factored)
    assert steps


def test_indirect_left_recursion_is_removed():
    productions = [
        {"lhs": ["A"], "rhs": ["B", "a"]},
        {"lhs": ["A"], "rhs": ["b"]},
        {"lhs": ["B"], "rhs": ["A", "c"]},
        {"lhs": ["B"], "rhs": ["d"]},
    ]
    transformed, steps = remove_left_recursion(productions)
    assert not any(p["rhs"] and p["rhs"][0] == p["lhs"][0] for p in transformed)
    assert any("Substitute" in step["title"] for step in steps)


def test_cnf_and_gnf_produce_steps():
    productions = [
        {"lhs": ["S"], "rhs": ["A", "B", "C"]},
        {"lhs": ["A"], "rhs": ["a"]},
        {"lhs": ["B"], "rhs": ["b"]},
        {"lhs": ["C"], "rhs": ["c"]},
    ]
    cnf, cnf_steps = to_cnf(productions, "S")
    assert cnf_steps
    assert all(len(p["rhs"]) <= 2 for p in cnf)
    gnf, gnf_steps = to_gnf(productions)
    assert gnf_steps
    assert gnf


def test_first_follow_and_ll1_conflict_reporting():
    productions = [
        {"lhs": ["S"], "rhs": ["a", "A"]},
        {"lhs": ["S"], "rhs": ["a", "B"]},
        {"lhs": ["A"], "rhs": ["b"]},
        {"lhs": ["B"], "rhs": ["c"]},
    ]
    analysis = compute_first_follow(productions, "S")
    assert analysis["first"]["S"] == ["a"]
    assert "$" in analysis["follow"]["S"]
    table = build_ll1_table(productions, "S")
    assert table["conflicts"]
    assert not table["is_ll1"]


def test_ll1_grammar_reports_true_verdict():
    productions = [
        {"lhs": ["S"], "rhs": ["a", "A"]},
        {"lhs": ["S"], "rhs": ["b"]},
        {"lhs": ["A"], "rhs": ["c"]},
    ]
    table = build_ll1_table(productions, "S")
    assert table["is_ll1"]


def test_cyk_returns_parse_tree():
    productions = [
        {"lhs": ["S"], "rhs": ["A", "B"]},
        {"lhs": ["A"], "rhs": ["a"]},
        {"lhs": ["B"], "rhs": ["b"]},
    ]
    result = parse_with_cyk(productions, "ab", "S")
    assert result["accepted"]
    assert result["parse_tree"]["symbol"] == "S"
    assert result["parse_tree"]["children"]


def test_regular_automaton_can_be_determinized_and_minimized():
    automaton = build_automaton(
        [{"lhs": ["S"], "rhs": ["a", "A"]}, {"lhs": ["A"], "rhs": ["b"]}],
        {"S", "A"},
    )
    dfa = nfa_to_dfa(automaton)
    minimized = minimize_dfa(dfa)
    assert dfa["transitions"]
    assert minimized["states"]
    assert automaton_to_regex(dfa)


def test_left_linear_automaton_reverses_edges_and_uses_start_state():
    result = analyze_grammar("S -> Aa | b\nA -> a")
    automaton = result["automaton"]
    assert automaton["start"] == "q0"
    assert "S" in automaton["final_states"]
    assert {tuple(t.values()) for t in automaton["transitions"]} == {("q0", "b", "S"), ("q0", "a", "A"), ("A", "a", "S")}


def test_epsilon_non_terminal_is_an_automaton_final_state():
    result = analyze_grammar("S -> aA | ε\nA -> b | ε")
    assert set(result["automaton"]["final_states"]) == {"F", "S", "A"}


def test_pipeline_returns_each_intermediate_stage():
    result = run_pipeline("S -> A | ε\nA -> a", "S")
    assert result["valid"]
    assert result["stages"][0]["title"] == "Original grammar"
    assert result["final_grammar"]
