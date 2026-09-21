from collections import defaultdict, deque
import re

EPSILON = "ε"


def tokenize(value: str) -> list[str]:
    value = value.strip()
    if value in ("", "epsilon", "ε"):
        return []
    tokens = []
    index = 0
    while index < len(value):
        char = value[index]
        if char.isspace():
            index += 1
            continue
        if char.isupper():
            end = index + 1
            while end < len(value) and (value[end].isdigit() or value[end] in "_'"):
                end += 1
            tokens.append(value[index:end])
            index = end
            continue
        if char.islower():
            end = index + 1
            while end < len(value) and value[end].islower():
                end += 1
            tokens.append(value[index:end])
            index = end
            continue
        tokens.append(char)
        index += 1
    return tokens


def parse_grammar(text: str):
    productions = []
    errors = []
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = re.split(r"\s*(?:->|→)\s*", line, maxsplit=1)
        if len(match) != 2 or not match[0].strip() or not match[1].strip():
            errors.append(f"Line {line_number}: invalid production. Use LHS -> RHS.")
            continue
        lhs = tokenize(match[0])
        if len(lhs) == 0:
            errors.append(f"Line {line_number}: left-hand side is missing.")
            continue
        alternatives = [part.strip() for part in match[1].split("|")]
        for alternative in alternatives:
            if not alternative:
                errors.append(f"Line {line_number}: empty alternative is not valid; use ε.")
                continue
            productions.append({"lhs": lhs, "rhs": tokenize(alternative), "line": line_number})
    non_terminals = {
        symbol
        for production in productions
        for side in (production["lhs"], production["rhs"])
        for symbol in side
        if symbol[:1].isupper()
    }
    terminals = {symbol for p in productions for symbol in p["rhs"] if symbol not in non_terminals}
    return productions, non_terminals, terminals, errors


def format_production(production):
    lhs = " ".join(production["lhs"])
    rhs = " ".join(production["rhs"]) if production["rhs"] else EPSILON
    return f"{lhs} → {rhs}"


def format_grammar(productions):
    grouped = defaultdict(list)
    order = []
    for production in productions:
        lhs = " ".join(production["lhs"])
        if lhs not in grouped:
            order.append(lhs)
        rhs = " ".join(production["rhs"]) if production["rhs"] else EPSILON
        if rhs not in grouped[lhs]:
            grouped[lhs].append(rhs)
    return [f"{lhs} → {' | '.join(grouped[lhs])}" for lhs in order]


def classify(productions, non_terminals, start):
    if not productions:
        return {"type": "Unclassified", "code": 0, "reason": "No productions were found."}
    cfg = all(len(p["lhs"]) == 1 and p["lhs"][0] in non_terminals for p in productions)
    regular_directions = set()
    regular = cfg
    for p in productions:
        rhs = p["rhs"]
        rhs_nt = [s for s in rhs if s in non_terminals]
        if len(rhs_nt) > 1 or (rhs_nt and rhs_nt[0] not in (rhs[-1], rhs[0])):
            regular = False
        elif rhs_nt:
            regular_directions.add("right" if rhs[-1] in non_terminals else "left")
            if len(rhs) != 2:
                regular = False
        elif len(rhs) > 1:
            regular = False
    if len(regular_directions) > 1:
        regular = False
    non_contracting = all(len(p["rhs"]) >= len(p["lhs"]) for p in productions)
    if regular:
        direction = "right-linear" if regular_directions != {"left"} else "left-linear"
        return {"type": "Type 3", "code": 3, "label": "Regular Grammar", "reason": f"Every production follows a {direction} pattern with at most one terminal block and one non-terminal.", "direction": direction}
    if cfg:
        return {"type": "Type 2", "code": 2, "label": "Context-Free Grammar", "reason": "Every production has exactly one non-terminal on the left-hand side."}
    permutation = len(productions) == 1 and any(len(p["lhs"]) > 1 and sorted(p["lhs"]) == sorted(p["rhs"]) for p in productions)
    if non_contracting and not permutation:
        return {"type": "Type 1", "code": 1, "label": "Context-Sensitive Grammar", "reason": "Every production is non-contracting: the right-hand side is at least as long as the left-hand side, subject to start-symbol epsilon rules."}
    return {"type": "Type 0", "code": 0, "label": "Unrestricted Grammar", "reason": "At least one production has a multi-symbol left-hand side or contracts the sentential form, so stronger restrictions do not apply."}


def validate(productions, non_terminals, terminals, start, parse_errors):
    issues = [{"severity": "error", "message": error} for error in parse_errors]
    if not productions:
        issues.append({"severity": "error", "message": "At least one production is required."})
        return issues
    if not start:
        issues.append({"severity": "error", "message": "Start symbol is missing."})
    elif start not in non_terminals:
        issues.append({"severity": "error", "message": f"Start symbol '{start}' has no production."})
    defined = {symbol for p in productions for symbol in p["lhs"]}
    referenced = {s for p in productions for s in p["rhs"] if s in non_terminals}
    for symbol in sorted(referenced - defined):
        issues.append({"severity": "warning", "message": f"Non-terminal '{symbol}' is referenced but never defined."})
    seen = set()
    for p in productions:
        key = (tuple(p["lhs"]), tuple(p["rhs"]))
        if key in seen:
            issues.append({"severity": "warning", "message": f"Duplicate production detected: {format_production(p)}"})
        seen.add(key)
    reachable = {start} if start else set()
    changed = True
    while changed:
        changed = False
        for p in productions:
            if len(p["lhs"]) == 1 and p["lhs"][0] in reachable:
                for symbol in p["rhs"]:
                    if symbol in non_terminals and symbol not in reachable:
                        reachable.add(symbol); changed = True
    for symbol in sorted(non_terminals - reachable):
        issues.append({"severity": "info", "message": f"Non-terminal '{symbol}' is unreachable from '{start}'."})
    return issues


def remove_left_recursion(productions):
    output = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    steps = []
    non_terminals = list(dict.fromkeys(p["lhs"][0] for p in output if len(p["lhs"]) == 1))
    for index, non_terminal in enumerate(non_terminals):
        for previous in non_terminals[:index]:
            substituted = []
            changed = False
            for production in output:
                if production["lhs"] != [non_terminal]:
                    continue
                if production["rhs"] and production["rhs"][0] == previous:
                    previous_rules = [p["rhs"] for p in output if p["lhs"] == [previous]]
                    substituted.extend({"lhs": [non_terminal], "rhs": rule + production["rhs"][1:]} for rule in previous_rules)
                    changed = True
                else:
                    substituted.append(production)
            if changed:
                before = output
                output = [p for p in output if p["lhs"] != [non_terminal]] + substituted
                steps.append({"title": f"Substitute {previous} into {non_terminal}", "explanation": f"Indirect recursion through {previous} is expanded before direct recursion is removed.", **_step_diff(before, output)})
        rules = [p["rhs"] for p in output if p["lhs"] == [non_terminal]]
        recursive = [rhs[1:] for rhs in rules if rhs and rhs[0] == non_terminal]
        base = [rhs for rhs in rules if not rhs or rhs[0] != non_terminal]
        if recursive and base:
            prime = non_terminal + "'"
            before = output
            output = [p for p in output if p["lhs"] != [non_terminal]]
            output.extend({"lhs": [non_terminal], "rhs": beta + [prime]} for beta in base)
            output.extend({"lhs": [prime], "rhs": alpha + [prime]} for alpha in recursive)
            output.append({"lhs": [prime], "rhs": []})
            steps.append({"title": f"Remove direct left recursion from {non_terminal}", "explanation": f"{non_terminal} recurs before consuming input, which can loop in top-down parsers. Introduced {prime} to encode repetitions.", **_step_diff(before, output)})
    return output, steps


def remove_unit_productions(productions):
    output = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    non_terminals = {p["lhs"][0] for p in output if len(p["lhs"]) == 1}
    closure = {symbol: {symbol} for symbol in non_terminals}
    changed = True
    while changed:
        changed = False
        for production in output:
            lhs, rhs = production["lhs"][0], production["rhs"]
            if len(rhs) == 1 and rhs[0] in non_terminals:
                before = len(closure[lhs])
                closure[lhs] |= closure[rhs[0]]
                changed |= len(closure[lhs]) != before
    result = []
    for lhs in non_terminals:
        for source in closure[lhs]:
            for production in output:
                if production["lhs"] == [source] and not (len(production["rhs"]) == 1 and production["rhs"][0] in non_terminals):
                    result.append({"lhs": [lhs], "rhs": list(production["rhs"])})
    result = _deduplicate(result)
    steps = [] if result == output else [{"title": "Remove unit productions", "explanation": "Unit rules such as A → B are replaced by the non-unit alternatives reachable through B.", "grammar": format_grammar(result)}]
    return result, steps


def remove_useless_symbols(productions, start_symbol=None):
    output = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    non_terminals = {p["lhs"][0] for p in output if len(p["lhs"]) == 1}
    generating = set()
    changed = True
    while changed:
        changed = False
        for production in output:
            if production["lhs"][0] in generating:
                continue
            if all(symbol not in non_terminals or symbol in generating for symbol in production["rhs"]):
                generating.add(production["lhs"][0]); changed = True
    result = [p for p in output if p["lhs"][0] in generating and all(symbol not in non_terminals or symbol in generating for symbol in p["rhs"])]
    reachable = {start_symbol or (result[0]["lhs"][0] if result else None)} - {None}
    changed = True
    while changed:
        changed = False
        for production in result:
            if production["lhs"][0] in reachable:
                for symbol in production["rhs"]:
                    if symbol in generating and symbol not in reachable:
                        reachable.add(symbol); changed = True
    result = [p for p in result if p["lhs"][0] in reachable]
    result = _deduplicate(result)
    steps = [] if result == output else [{"title": "Remove useless symbols", "explanation": "Non-generating symbols are removed first, followed by symbols unreachable from the first production's start symbol.", "grammar": format_grammar(result)}]
    return result, steps


def left_factor(productions):
    output = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    steps = []
    for non_terminal in list(dict.fromkeys(p["lhs"][0] for p in output if len(p["lhs"]) == 1)):
        rules = [p["rhs"] for p in output if p["lhs"] == [non_terminal]]
        if len(rules) < 2:
            continue
        prefix = _longest_common_prefix(rules)
        if not prefix:
            continue
        prime = _fresh_symbol(non_terminal + "'", {p["lhs"][0] for p in output})
        output = [p for p in output if p["lhs"] != [non_terminal]]
        output.append({"lhs": [non_terminal], "rhs": prefix + [prime]})
        output.extend({"lhs": [prime], "rhs": rule[len(prefix):]} for rule in rules)
        steps.append({"title": f"Left-factor {non_terminal}", "explanation": f"The common prefix {' '.join(prefix)} is parsed once, leaving the alternatives under {prime} for predictive parsing.", "grammar": format_grammar(output)})
    return output, steps


def _deduplicate(productions):
    seen = set()
    result = []
    for production in productions:
        key = (tuple(production["lhs"]), tuple(production["rhs"]))
        if key not in seen:
            seen.add(key); result.append(production)
    return result


def _longest_common_prefix(rules):
    if not rules:
        return []
    prefix = list(rules[0])
    for rule in rules[1:]:
        size = 0
        while size < len(prefix) and size < len(rule) and prefix[size] == rule[size]:
            size += 1
        prefix = prefix[:size]
    return prefix


def _fresh_symbol(candidate, existing):
    symbol = candidate
    while symbol in existing:
        symbol += "'"
    return symbol


def _step_diff(before, after):
    before_lines = format_grammar(before)
    after_lines = format_grammar(after)
    before_set = set(before_lines)
    after_set = set(after_lines)
    return {
        "grammar": after_lines,
        "added": [line for line in after_lines if line not in before_set],
        "removed": [line for line in before_lines if line not in after_set],
        "retained": [line for line in after_lines if line in before_set],
    }


def remove_epsilon(productions):
    nullable = {p["lhs"][0] for p in productions if not p["rhs"]}
    changed = True
    while changed:
        changed = False
        for p in productions:
            if p["lhs"][0] not in nullable and all(s in nullable for s in p["rhs"]):
                nullable.add(p["lhs"][0]); changed = True
    result = []
    for p in productions:
        positions = [i for i, s in enumerate(p["rhs"]) if s in nullable]
        variants = {tuple(p["rhs"])}
        for position in positions:
            variants |= {v[:position] + v[position + 1:] for v in list(variants)}
        for variant in variants:
            if variant or p["lhs"][0] not in nullable:
                result.append({"lhs": p["lhs"], "rhs": list(variant)})
    return result


def to_cnf(productions, start_symbol=None):
    current = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    steps = []
    current = remove_epsilon(current)
    steps.append({"title": "CNF: remove epsilon-productions", "explanation": "Nullable alternatives are expanded before CNF shape restrictions are applied.", "grammar": format_grammar(current)})
    current, unit_steps = remove_unit_productions(current)
    steps.extend(unit_steps)
    current, useless_steps = remove_useless_symbols(current, start_symbol)
    steps.extend(useless_steps)
    non_terminals = {p["lhs"][0] for p in current if len(p["lhs"]) == 1}
    terminal_names = {}
    replaced = []
    for production in current:
        rhs = list(production["rhs"])
        if len(rhs) > 1:
            rhs = [terminal_names.setdefault(symbol, _fresh_symbol("T_" + symbol, non_terminals)) if symbol not in non_terminals else symbol for symbol in rhs]
        replaced.append({"lhs": production["lhs"], "rhs": rhs})
    for terminal, name in terminal_names.items():
        replaced.append({"lhs": [name], "rhs": [terminal]})
    current = _deduplicate(replaced)
    steps.append({"title": "CNF: isolate terminals", "explanation": "Terminals in mixed or long alternatives receive helper non-terminals.", "grammar": format_grammar(current)})
    result = []
    counter = 1
    for production in current:
        lhs, rhs = production["lhs"], production["rhs"]
        if len(rhs) <= 2:
            result.append(production)
            continue
        left = lhs
        remaining = list(rhs)
        while len(remaining) > 2:
            helper = _fresh_symbol(f"X{counter}", {p["lhs"][0] for p in result} | {p["lhs"][0] for p in current})
            counter += 1
            result.append({"lhs": left, "rhs": [remaining[0], helper]})
            left = [helper]
            remaining = remaining[1:]
        result.append({"lhs": left, "rhs": remaining})
    result = _deduplicate(result)
    steps.append({"title": "CNF: binarize long alternatives", "explanation": "Every remaining alternative is split until it has at most two symbols on the right-hand side.", "grammar": format_grammar(result)})
    return result, steps


def to_gnf(productions):
    current = [dict(lhs=list(p["lhs"]), rhs=list(p["rhs"])) for p in productions]
    current, recursion_steps = remove_left_recursion(current)
    steps = list(recursion_steps)
    non_terminals = list(dict.fromkeys(p["lhs"][0] for p in current if len(p["lhs"]) == 1))
    for index, non_terminal in enumerate(non_terminals):
        for production in list(current):
            if production["lhs"] != [non_terminal] or not production["rhs"] or production["rhs"][0] not in non_terminals:
                continue
            leading = production["rhs"][0]
            current.remove(production)
            for replacement in [p["rhs"] for p in current if p["lhs"] == [leading]]:
                current.append({"lhs": [non_terminal], "rhs": replacement + production["rhs"][1:]})
    steps.append({"title": "GNF: expand leading non-terminals", "explanation": "Leading non-terminals are substituted so each alternative begins with a terminal whenever the grammar permits the conversion.", "grammar": format_grammar(current)})
    return _deduplicate(current), steps


def compute_first_follow(productions, start_symbol=None):
    non_terminals = {p["lhs"][0] for p in productions if len(p["lhs"]) == 1}
    terminals = {s for p in productions for s in p["rhs"] if s not in non_terminals}
    start = start_symbol or (productions[0]["lhs"][0] if productions else None)
    first = {symbol: set() for symbol in non_terminals | terminals}
    for terminal in terminals:
        first[terminal].add(terminal)
    first[EPSILON] = {EPSILON}
    changed = True
    while changed:
        changed = False
        for production in productions:
            lhs, rhs = production["lhs"][0], production["rhs"]
            before = len(first[lhs])
            if not rhs:
                first[lhs].add(EPSILON)
            else:
                nullable = True
                for symbol in rhs:
                    first[lhs] |= first.get(symbol, {symbol}) - {EPSILON}
                    if EPSILON not in first.get(symbol, set()):
                        nullable = False
                        break
                if nullable:
                    first[lhs].add(EPSILON)
            changed |= len(first[lhs]) != before
    follow = {symbol: set() for symbol in non_terminals}
    if start:
        follow.setdefault(start, set()).add("$")
    changed = True
    while changed:
        changed = False
        for production in productions:
            lhs, rhs = production["lhs"][0], production["rhs"]
            trailer = set(follow.get(lhs, set()))
            for symbol in reversed(rhs):
                if symbol in non_terminals:
                    before = len(follow[symbol])
                    follow[symbol] |= trailer
                    changed |= len(follow[symbol]) != before
                    if EPSILON in first[symbol]:
                        trailer |= first[symbol] - {EPSILON}
                    else:
                        trailer = first[symbol] - {EPSILON}
                else:
                    trailer = first.get(symbol, {symbol}) - {EPSILON}
    return {"first": {key: sorted(value) for key, value in first.items() if key != EPSILON}, "follow": {key: sorted(value) for key, value in follow.items()}, "terminals": sorted(terminals), "non_terminals": sorted(non_terminals), "start_symbol": start}


def build_ll1_table(productions, start_symbol=None):
    analysis = compute_first_follow(productions, start_symbol)
    first = {key: set(value) for key, value in analysis["first"].items()}
    follow = {key: set(value) for key, value in analysis["follow"].items()}
    table = {}
    conflicts = []
    for production in productions:
        lhs, rhs = production["lhs"][0], production["rhs"]
        sequence_first = _first_of_sequence(rhs, first)
        lookaheads = sequence_first - {EPSILON}
        if EPSILON in sequence_first:
            lookaheads |= follow.get(lhs, set())
        for lookahead in lookaheads:
            key = f"{lhs},{lookahead}"
            rendered = format_production(production)
            if key in table and table[key] != rendered:
                conflicts.append({"cell": key, "productions": [table[key], rendered]})
            table[key] = rendered
    return {"table": table, "conflicts": conflicts, "is_ll1": not conflicts, "first_follow": analysis}


def _first_of_sequence(sequence, first):
    if not sequence:
        return {EPSILON}
    result = set()
    nullable = True
    for symbol in sequence:
        symbol_first = first.get(symbol, {symbol})
        result |= symbol_first - {EPSILON}
        if EPSILON not in symbol_first:
            nullable = False
            break
    if nullable:
        result.add(EPSILON)
    return result


def build_automaton(productions, non_terminals, start_symbol=None):
    start_symbol = start_symbol or (productions[0]["lhs"][0] if productions else None)
    direction = "left" if any(len(p["rhs"]) == 2 and p["rhs"][0] in non_terminals for p in productions) else "right"
    terminal_ending = any(
        p["rhs"] and p["rhs"][-1] not in non_terminals
        for p in productions
        if len(p["lhs"]) == 1
    )
    if direction == "left":
        start_state, accepting_state = "q0", start_symbol
        states = [start_state] + sorted(non_terminals)
    else:
        start_state, accepting_state = start_symbol, "F"
        states = sorted(non_terminals) + ([accepting_state] if terminal_ending else [])
    transitions = []
    final_states = {accepting_state} if direction == "left" or terminal_ending else set()
    nullable = set()
    changed = True
    while changed:
        changed = False
        for production in productions:
            rhs = production["rhs"]
            if not rhs or all(symbol in non_terminals and symbol in nullable for symbol in rhs):
                lhs = production["lhs"][0]
                if lhs not in nullable:
                    nullable.add(lhs)
                    changed = True
    for production in productions:
        if len(production["lhs"]) != 1:
            continue
        lhs, rhs = production["lhs"][0], production["rhs"]
        if not rhs:
            if direction == "right":
                final_states.add(lhs)
            elif lhs == start_symbol:
                final_states.add(start_state)
        elif direction == "left" and len(rhs) == 1 and rhs[0] not in non_terminals:
            transitions.append({"from": start_state, "symbol": rhs[0], "to": lhs})
        elif direction == "left" and len(rhs) == 2 and rhs[0] in non_terminals:
            transitions.append({"from": rhs[0], "symbol": rhs[1], "to": lhs})
        elif direction == "right" and len(rhs) == 1 and rhs[0] not in non_terminals:
            transitions.append({"from": lhs, "symbol": rhs[0], "to": accepting_state})
        elif direction == "right" and len(rhs) == 2 and rhs[1] in non_terminals:
            transitions.append({"from": lhs, "symbol": rhs[0], "to": rhs[1]})
    if direction == "left":
        for production in productions:
            if len(production["lhs"]) == 1 and not production["rhs"]:
                lhs = production["lhs"][0]
                transitions.extend(
                    {"from": start_state, "symbol": transition["symbol"], "to": transition["to"]}
                    for transition in transitions[:]
                    if transition["from"] == lhs
                )
        if start_symbol in nullable:
            final_states.add(start_state)
    return {"states": states, "start": start_state, "final_states": sorted(final_states), "transitions": _deduplicate_transitions(transitions)}


def nfa_to_dfa(automaton):
    if not automaton:
        return None
    transitions = automaton["transitions"]
    alphabet = sorted({t["symbol"] for t in transitions if t["symbol"] != EPSILON})
    start = automaton.get("start") or automaton.get("start_state")
    if not start:
        return None
    subsets = {frozenset([start])}
    queue = deque(subsets)
    dfa_transitions = []
    while queue:
        subset = queue.popleft()
        name = _subset_name(subset)
        for symbol in alphabet:
            target = frozenset(t["to"] for t in transitions if t["from"] in subset and t["symbol"] == symbol)
            if not target:
                continue
            if target not in subsets:
                subsets.add(target); queue.append(target)
            dfa_transitions.append({"from": name, "symbol": symbol, "to": _subset_name(target)})
    final_names = [_subset_name(subset) for subset in subsets if set(subset) & set(automaton.get("final_states", []))]
    dfa_start = _subset_name(frozenset([start]))
    return {"states": [_subset_name(subset) for subset in sorted(subsets, key=lambda value: _subset_name(value))], "start": dfa_start, "start_state": dfa_start, "final_states": final_names, "transitions": dfa_transitions}


def minimize_dfa(dfa):
    if not dfa:
        return None
    states = set(dfa["states"])
    finals = set(dfa["final_states"])
    alphabet = sorted({t["symbol"] for t in dfa["transitions"]})
    partitions = [finals, states - finals]
    partitions = [part for part in partitions if part]
    changed = True
    while changed:
        changed = False
        lookup = {state: index for index, part in enumerate(partitions) for state in part}
        refined = []
        for part in partitions:
            groups = defaultdict(set)
            for state in part:
                signature = tuple(lookup.get(next((t["to"] for t in dfa["transitions"] if t["from"] == state and t["symbol"] == symbol), "#"), -1) for symbol in alphabet)
                groups[signature].add(state)
            refined.extend(groups.values())
            changed |= len(groups) > 1
        partitions = refined
    names = {state: f"Q{i}" for i, part in enumerate(partitions) for state in part}
    transitions = _deduplicate_transitions({"from": names[t["from"]], "symbol": t["symbol"], "to": names[t["to"]]} for t in dfa["transitions"])
    start = dfa.get("start") or dfa["start_state"]
    return {"states": sorted(set(names.values())), "start": names[start], "start_state": names[start], "final_states": sorted({names[state] for state in finals}), "transitions": transitions}


def automaton_to_regex(automaton):
    if not automaton or not automaton.get("transitions"):
        return "∅"
    accepted = [t["symbol"] for t in automaton["transitions"] if t["to"] in automaton.get("final_states", [])]
    loops = [t["symbol"] for t in automaton["transitions"] if t["from"] == t["to"]]
    prefix = "(" + "|".join(sorted(set(accepted))) + ")" if accepted else ""
    suffix = ("(" + "|".join(sorted(set(loops))) + ")*") if loops else ""
    return prefix + suffix or "∅"


def parse_with_cyk(productions, text, start_symbol=None):
    tokens = text.split() if " " in text.strip() else list(text.strip())
    start = start_symbol or (productions[0]["lhs"][0] if productions else None)
    cnf, _ = to_cnf(productions, start)
    binary = defaultdict(list)
    terminal = defaultdict(list)
    for production in cnf:
        lhs, rhs = production["lhs"][0], production["rhs"]
        if len(rhs) == 1 and rhs[0] not in {p["lhs"][0] for p in cnf}:
            terminal[rhs[0]].append(lhs)
        elif len(rhs) == 2:
            binary[(rhs[0], rhs[1])].append(lhs)
    if not tokens:
        accepted = any(p["lhs"] == [start] and not p["rhs"] for p in productions)
        return {"accepted": accepted, "derivation": [], "parse_tree": {"symbol": start, "children": []} if accepted else None}
    table = {}
    derivation = []
    for index, token in enumerate(tokens):
        table[(index, index + 1)] = {lhs: {"symbol": lhs, "children": [{"symbol": token, "children": []}]} for lhs in terminal.get(token, [])}
        if terminal.get(token):
            derivation.append({"span": [index, index + 1], "rule": f"{', '.join(terminal[token])} → {token}"})
    for length in range(2, len(tokens) + 1):
        for begin in range(len(tokens) - length + 1):
            end = begin + length
            cell = {}
            for split in range(begin + 1, end):
                for left, left_tree in table.get((begin, split), {}).items():
                    for right, right_tree in table.get((split, end), {}).items():
                        for lhs in binary.get((left, right), []):
                            cell.setdefault(lhs, {"symbol": lhs, "children": [left_tree, right_tree]})
                            derivation.append({"span": [begin, end], "split": split, "rule": f"{lhs} → {left} {right}"})
            table[(begin, end)] = cell
    tree = table.get((0, len(tokens)), {}).get(start)
    return {"accepted": tree is not None, "derivation": derivation, "parse_tree": tree}


def _subset_name(subset):
    return "{" + ",".join(sorted(subset)) + "}"


def _deduplicate_transitions(transitions):
    seen = set(); result = []
    for transition in transitions:
        key = tuple(transition.values())
        if key not in seen:
            seen.add(key); result.append(transition)
    return result


def analyze_grammar(text, start_symbol=None):
    productions, non_terminals, terminals, parse_errors = parse_grammar(text)
    start = start_symbol.strip() if start_symbol else (productions[0]["lhs"][0] if productions else None)
    issues = validate(productions, non_terminals, terminals, start, parse_errors)
    classification = classify(productions, non_terminals, start)
    transformed, recursion_steps = remove_left_recursion(productions) if classification.get("code") == 2 else (productions, [])
    steps = recursion_steps
    automaton = build_automaton(productions, non_terminals, start) if classification.get("code") == 3 else None
    dfa = nfa_to_dfa(automaton) if automaton else None
    first_follow = compute_first_follow(productions, start)
    ll1 = build_ll1_table(productions, start)
    return {"start_symbol": start, "productions": format_grammar(productions), "non_terminals": sorted(non_terminals), "terminals": sorted(terminals), "validation": issues, "valid": not any(i["severity"] == "error" for i in issues), "classification": classification, "properties": {"production_count": len(productions), "has_epsilon": any(not p["rhs"] for p in productions), "has_left_recursion": bool(recursion_steps), "is_non_contracting": all(len(p["rhs"]) >= len(p["lhs"]) for p in productions) if productions else False}, "steps": steps, "automaton": automaton, "dfa": dfa, "minimized_dfa": minimize_dfa(dfa) if dfa else None, "regex": automaton_to_regex(dfa) if dfa else None, "first": first_follow["first"], "follow": first_follow["follow"], "first_follow": first_follow, "ll1": ll1, "available_transformations": ["remove_epsilon", "remove_unit", "remove_useless", "remove_left_recursion", "left_factor", "to_cnf", "to_gnf", "first_follow", "ll1"] + (["nfa_to_dfa", "minimize_dfa", "regex"] if automaton else []), "explanation": explanation_for(classification, issues)}


def run_pipeline(text, start_symbol=None):
    productions, non_terminals, _, parse_errors = parse_grammar(text)
    start = start_symbol or (productions[0]["lhs"][0] if productions else None)
    stages = [{"title": "Original grammar", "grammar": format_grammar(productions)}]
    current = remove_epsilon(productions)
    stages.append({"title": "Remove epsilon-productions", "grammar": format_grammar(current)})
    current, _ = remove_unit_productions(current)
    stages.append({"title": "Remove unit productions", "grammar": format_grammar(current)})
    current, _ = remove_useless_symbols(current, start)
    stages.append({"title": "Remove useless symbols", "grammar": format_grammar(current)})
    current, cnf_steps = to_cnf(current, start)
    stages.extend({"title": step["title"], "grammar": step["grammar"]} for step in cnf_steps)
    return {"start_symbol": start, "valid": not parse_errors, "stages": stages, "final_grammar": format_grammar(current)}


def explanation_for(classification, issues):
    if any(i["severity"] == "error" for i in issues):
        return "The grammar needs correction before its transformations can be trusted. Review the validation messages, then analyze again."
    return classification.get("reason", "The grammar could not be classified yet.")
