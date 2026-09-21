import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.grammar.engine import (
    analyze_grammar,
    format_grammar,
    left_factor,
    parse_grammar,
    parse_with_cyk,
    remove_epsilon,
    remove_left_recursion,
    remove_unit_productions,
    remove_useless_symbols,
    run_pipeline,
    to_cnf,
    to_gnf,
)

app = FastAPI(title="Intelligent Grammar Transformation Assistant")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    grammar: str
    start_symbol: str | None = None

class ParseRequest(BaseModel):
    grammar: str
    string: str
    start_symbol: str | None = None

class PipelineRequest(BaseModel):
    grammar: str
    start_symbol: str | None = None

class AskRequest(BaseModel):
    grammar: str
    question: str
    start_symbol: str | None = None
    parse_string: str | None = None


def _rules_for_lhs(productions, symbol):
    return [format_grammar([production])[-1] for production in productions if production["lhs"] == [symbol]]


def _format_sets(values):
    return "{ " + ", ".join(values) + " }"


def _first_reasons(symbol, productions, first_follow):
    computed = set(first_follow["first"].get(symbol, []))
    reasons = {value: [] for value in computed}
    for production in productions:
        if production["lhs"] != [symbol]:
            continue
        rendered = format_grammar([production])[0]
        rhs = production["rhs"]
        if not rhs:
            if "ε" in reasons:
                reasons["ε"].append(f"'ε' is included because {rendered}.")
            continue
        nullable_prefix = True
        for current in rhs:
            current_first = set(first_follow["first"].get(current, []))
            if current not in first_follow["non_terminals"]:
                current_first.add(current)
            for value in current_first & computed:
                if value != "ε":
                    reasons[value].append(f"'{value}' is included because {rendered} begins with '{value}'." if current == value and nullable_prefix else f"'{value}' is included through FIRST({current}) in {rendered}.")
            if "ε" not in current_first:
                nullable_prefix = False
                break
        if nullable_prefix and "ε" in reasons:
            reasons["ε"].append(f"'ε' is included because all symbols in {rendered} can derive ε.")
    return {value: list(dict.fromkeys(lines)) for value, lines in reasons.items()}


def _follow_reasons(symbol, productions, first_follow, start_symbol):
    computed = set(first_follow["follow"].get(symbol, []))
    reasons = {value: [] for value in computed}
    if symbol == start_symbol and "$" in reasons:
        reasons["$"].append(f"'$' is included because {symbol} is the start symbol.")
    non_terminals = set(first_follow["non_terminals"])
    for production in productions:
        rhs = production["rhs"]
        rendered = format_grammar([production])[0]
        for index, current in enumerate(rhs):
            if current != symbol:
                continue
            suffix = rhs[index + 1:]
            nullable_suffix = True
            for following in suffix:
                following_first = set(first_follow["first"].get(following, [following]))
                for value in (following_first - {"ε"}) & computed:
                    if following in non_terminals:
                        reasons[value].append(f"'{value}' is included because it is in FIRST({following}) after {symbol} in {rendered}.")
                    else:
                        reasons[value].append(f"'{value}' is included because {symbol} is immediately followed by '{value}' in {rendered}.")
                if "ε" not in following_first:
                    nullable_suffix = False
                    break
            if nullable_suffix:
                for value in computed & set(first_follow["follow"].get(production["lhs"][0], [])):
                    reasons[value].append(f"'{value}' is included because the suffix after {symbol} in {rendered} can derive ε, so FOLLOW({production['lhs'][0]}) is propagated.")
    return {value: list(dict.fromkeys(lines)) for value, lines in reasons.items()}


def _intent(question):
    text = question.lower()
    if any(term in text for term in ("first", "follow")):
        return "first_follow"
    if "ll(1)" in text or "ll1" in text or "conflict" in text or "predictive" in text:
        return "ll1"
    if "parse tree" in text or "derivation" in text:
        return "parse_tree"
    if "left factor" in text:
        return "left_factoring"
    if "left recursion" in text or "left-recursion" in text:
        return "left_recursion"
    if "epsilon" in text or "empty production" in text:
        return "epsilon"
    if "unit production" in text:
        return "unit"
    if "useless" in text or "unreachable" in text or "non-generating" in text:
        return "useless"
    if "cnf" in text or "chomsky normal" in text:
        return "cnf"
    if "gnf" in text or "greibach normal" in text:
        return "gnf"
    if any(term in text for term in ("classif", "type of grammar", "what type", "which automaton", "why is this cfg", "context-free", "type 2")):
        return "classification"
    return "general"


def answer_grammar_question(question, analysis, grammar, parse_string=None):
    normalized = question.lower().strip()
    if not normalized:
        return "Ask a question about the current grammar analysis."
    productions, _, _, parse_errors = parse_grammar(grammar)
    if parse_errors:
        return "I cannot answer reliably because the current grammar has errors: " + "; ".join(parse_errors)
    intent = _intent(normalized)
    classification = analysis["classification"]
    first_follow = analysis["first_follow"]

    if intent == "classification":
        automaton = " A finite automaton corresponds to this regular grammar." if classification["code"] == 3 else " A pushdown automaton corresponds to this context-free grammar." if classification["code"] == 2 else ""
        return f"This is a {classification.get('label', classification['type'])}. {classification['reason']}{automaton} The productions are: {'; '.join(analysis['productions'])}."

    if intent == "left_recursion":
        recursive = [production for production in productions if production["lhs"] and production["rhs"] and production["lhs"] == [production["rhs"][0]]]
        if not recursive:
            return "No direct left recursion was detected in the current productions."
        lines = ["Yes. The current grammar contains direct left recursion:"]
        for production in recursive:
            lines.append(f"- {format_grammar([production])[0]}")
        lines.append("\nThis can make a top-down parser recurse before consuming input.")
        recursion_result, recursion_steps = remove_left_recursion(productions)
        if any("Remove direct left recursion" in step["title"] for step in recursion_steps):
            lines.append("The deterministic transformation gives:")
            lines.extend(f"- {rule}" for rule in format_grammar(recursion_result))
        return "\n".join(lines)

    if intent == "first_follow":
        requested = next((symbol for symbol in first_follow["non_terminals"] if symbol.lower() in normalized), None)
        lines = []
        if "first" in normalized:
            names = [requested] if requested else first_follow["non_terminals"]
            for name in names:
                if lines:
                    lines.append("")
                lines.extend([f"FIRST({name})", _format_sets(first_follow["first"].get(name, [])), "", "Explanation:"])
                for value in first_follow["first"].get(name, []):
                    lines.extend(f"- {reason}" for reason in _first_reasons(name, productions, first_follow).get(value, []))
        if "follow" in normalized:
            names = [requested] if requested else first_follow["non_terminals"]
            for name in names:
                if lines:
                    lines.append("")
                lines.extend([f"FOLLOW({name})", _format_sets(first_follow["follow"].get(name, [])), "", "Explanation:"])
                for value in first_follow["follow"].get(name, []):
                    lines.extend(f"- {reason}" for reason in _follow_reasons(name, productions, first_follow, analysis["start_symbol"]).get(value, []))
        return "\n".join(lines)

    if intent == "ll1":
        ll1 = analysis["ll1"]
        if ll1["is_ll1"]:
            return "The grammar is actually LL(1), so there are no LL(1) conflicts. The computed parsing table has one production for every populated lookahead cell."
        lines = [f"The grammar is not LL(1): the computed table has {len(ll1['conflicts'])} conflict(s)."]
        lines.extend(f"- Cell {conflict['cell']}: {' versus '.join(conflict['productions'])}" for conflict in ll1["conflicts"])
        return "\n".join(lines)

    if intent == "epsilon":
        epsilon_rules = [rule for production in productions if not production["rhs"] for rule in format_grammar([production])]
        if not epsilon_rules:
            return "The current grammar contains no epsilon productions."
        lines = ["The current grammar contains these epsilon productions:"] + [f"- {rule}" for rule in epsilon_rules]
        if "remove" in normalized:
            lines.append("Removing epsilon productions gives:")
            lines.extend(f"- {rule}" for rule in format_grammar(remove_epsilon(productions)))
        else:
            lines.append("Epsilon denotes the empty string. It is retained when it is part of the grammar's language or when left-recursion elimination introduces it as a repetition helper.")
        return "\n".join(lines)

    if intent == "unit":
        unit_rules = [format_grammar([production])[0] for production in productions if len(production["lhs"]) == 1 and len(production["rhs"]) == 1 and production["rhs"][0] in analysis["non_terminals"]]
        if not unit_rules:
            return "The current grammar contains no unit productions."
        lines = ["The current grammar contains these unit productions:"] + [f"- {rule}" for rule in unit_rules]
        if "remove" in normalized:
            transformed, _ = remove_unit_productions(productions)
            lines.append("After unit-production removal:")
            lines.extend(f"- {rule}" for rule in format_grammar(transformed))
        return "\n".join(lines)

    if intent == "useless":
        transformed, _ = remove_useless_symbols(productions, analysis["start_symbol"])
        if len(format_grammar(transformed)) == len(analysis["productions"]):
            return "No useless symbols were removed by the deterministic analysis."
        return "The deterministic useless-symbol removal result is:\n" + "\n".join(f"- {rule}" for rule in format_grammar(transformed))

    if intent == "left_factoring":
        transformed, steps = left_factor(productions)
        if not steps:
            return "The current grammar has no common alternative prefix requiring left factoring."
        return "Left factoring is useful here because alternatives share a prefix. The result is:\n" + "\n".join(f"- {rule}" for rule in format_grammar(transformed))

    if intent == "cnf":
        transformed, steps = to_cnf(productions, analysis["start_symbol"])
        return ("The deterministic CNF conversion trace is:\n" if "convert" in normalized else "The deterministic CNF result is:\n") + "\n".join(f"- {rule}" for rule in format_grammar(transformed))

    if intent == "gnf":
        transformed, steps = to_gnf(productions)
        return "The deterministic GNF result is:\n" + "\n".join(f"- {rule}" for rule in format_grammar(transformed))

    if intent == "parse_tree":
        value = parse_string or _extract_parse_string(question)
        if not value:
            return "Provide an input string, for example: 'Show the parse tree for id + id.'"
        tokens, unknown = tokenize_input(value, set(analysis["terminals"]))
        if unknown:
            return f"The input cannot be parsed because '{unknown}' is not a terminal in the current grammar."
        parsed = parse_with_cyk(productions, " ".join(tokens), analysis["start_symbol"])
        if not parsed["accepted"]:
            return f"No parse tree exists for '{value}' from start symbol {analysis['start_symbol']}."
        return f"The input '{value}' is accepted. Its parse tree root is {parsed['parse_tree']['symbol']} and the computed derivation has {len(parsed['derivation'])} step(s)."

    return f"This is a {classification.get('label', classification['type'])} with start symbol {analysis['start_symbol']}. It has productions {'; '.join(analysis['productions'])}. FIRST and FOLLOW sets, LL(1) conflicts, validation results, and transformation trace are all computed from the current grammar."


def _extract_parse_string(question):
    match = re.search(r"\bfor\s+(.+?)(?:\?|$)", question, re.IGNORECASE)
    return match.group(1).strip(" '\"") if match else None


def tokenize_input(value: str, terminals: set[str]):
    if value.strip() in ("", "ε", "epsilon"):
        return [], None
    ordered_terminals = sorted(terminals, key=lambda terminal: (-len(terminal), terminal))
    tokens = []
    for piece in value.split():
        index = 0
        while index < len(piece):
            match = next((terminal for terminal in ordered_terminals if piece.startswith(terminal, index)), None)
            if match is None:
                return None, piece[index]
            tokens.append(match)
            index += len(match)
    return tokens, None

@app.get("/api/health")
def health():
    return {"status": "ok"}

@app.post("/api/analyze")
def analyze(request: AnalyzeRequest):
    return analyze_grammar(request.grammar, request.start_symbol)

@app.post("/api/parse")
def parse(request: ParseRequest):
    productions, _, terminals, errors = parse_grammar(request.grammar)
    if errors:
        return {"accepted": False, "derivation": [], "parse_tree": None, "errors": errors}
    tokens, unknown = tokenize_input(request.string, terminals)
    if unknown is not None:
        return {"accepted": False, "derivation": [], "parse_tree": None, "error": f"Unknown symbol '{unknown}'."}
    result = parse_with_cyk(productions, " ".join(tokens), request.start_symbol)
    return {"accepted": result["accepted"], "tree": result.get("parse_tree"), "derivation": result.get("derivation", [])}

@app.post("/api/pipeline")
def pipeline(request: PipelineRequest):
    return run_pipeline(request.grammar, request.start_symbol)

@app.post("/api/ask")
def ask(request: AskRequest):
    analysis = analyze_grammar(request.grammar, request.start_symbol)
    return {"answer": answer_grammar_question(request.question, analysis, request.grammar, request.parse_string)}
