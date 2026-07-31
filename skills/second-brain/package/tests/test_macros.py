from brain.ingest.macros import extract_preamble_info


def test_macro_extraction_against_golden(normalized, golden_macros):
    assert normalized.macro_names == golden_macros["names"]
    assert normalized.macros == golden_macros["definitions"]


def test_starred_and_optional_arg_forms():
    preamble = r"""
\newcommand*{\foo}{F}
\renewcommand{\bar}[2][x]{#1#2}
\def\baz#1{B#1}
\DeclareMathOperator{\supp}{supp}
"""
    info = extract_preamble_info(preamble)
    by_name = {m.name: m for m in info.macros}
    assert set(by_name) == {"foo", "bar", "baz", "supp"}
    assert by_name["bar"].definition == r"\renewcommand{\bar}[2][x]{#1#2}"
    assert by_name["baz"].kind == "def"
    assert by_name["supp"].kind == "mathoperator"


def test_newtheorem_shared_counters():
    preamble = r"""
\newtheorem{thm}{Theorem}[section]
\newtheorem{lem}[thm]{Lemma}
\newtheorem*{note}{Note}
"""
    info = extract_preamble_info(preamble)
    specs = info.theorem_specs
    assert specs["thm"].display == "Theorem"
    assert specs["lem"].counter == specs["thm"].counter
    assert specs["note"].numbered is False
