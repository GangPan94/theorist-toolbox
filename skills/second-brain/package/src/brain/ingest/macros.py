"""Extract macro definitions and theorem-environment declarations from a preamble."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .texutil import read_group, read_optional, skip_ws

_DEF_CMDS = re.compile(
    r"\\(newcommand|renewcommand|providecommand|DeclareMathOperator|newtheorem)(\*?)(?![a-zA-Z])"
    r"|\\def(?![a-zA-Z])"
)

# Standard amsthm-style environment names usable without a \newtheorem declaration
# (papers that \input a style file we can't see still get sensible defaults).
STANDARD_ENVS = {
    "theorem": "Theorem", "lemma": "Lemma", "proposition": "Proposition",
    "corollary": "Corollary", "definition": "Definition", "assumption": "Assumption",
    "remark": "Remark", "claim": "Claim", "example": "Example",
    "conjecture": "Conjecture", "fact": "Fact", "observation": "Observation",
}

THEOREM_LIKE_DISPLAYS = {
    "Theorem", "Lemma", "Proposition", "Corollary", "Claim", "Conjecture", "Fact",
}


@dataclass
class Macro:
    name: str          # control-sequence name without backslash, e.g. "val"
    definition: str    # full source, e.g. "\\newcommand{\\val}{v_i(t_i)}"
    kind: str          # newcommand | renewcommand | providecommand | def | mathoperator


@dataclass
class TheoremSpec:
    env: str           # environment name as used in \begin{...}
    display: str       # human name, e.g. "Theorem"
    counter: str       # counter key; envs sharing a counter share numbering
    numbered: bool = True


@dataclass
class PreambleInfo:
    macros: list[Macro] = field(default_factory=list)
    theorem_specs: dict[str, TheoremSpec] = field(default_factory=dict)


def _read_control_name(s: str, i: int) -> tuple[str | None, int]:
    """Read a control sequence like \\val at position i (possibly brace-wrapped)."""
    i = skip_ws(s, i)
    if i < len(s) and s[i] == "{":
        inner, j = read_group(s, i)
        inner = inner.strip()
        if inner.startswith("\\"):
            return inner[1:], j
        return None, j
    if i < len(s) and s[i] == "\\":
        m = re.match(r"\\([a-zA-Z@]+)", s[i:])
        if m:
            return m.group(1), i + m.end()
    return None, i


def extract_preamble_info(preamble: str) -> PreambleInfo:
    info = PreambleInfo()
    for m in _DEF_CMDS.finditer(preamble):
        start = m.start()
        cmd = m.group(1) or "def"
        try:
            if cmd == "newtheorem":
                _parse_newtheorem(preamble, m.end(), starred=bool(m.group(2)), info=info)
            elif cmd == "DeclareMathOperator":
                i = m.end()
                name, i = _read_control_name(preamble, i)
                i = skip_ws(preamble, i)
                _, i = read_group(preamble, i)
                if name:
                    info.macros.append(Macro(name, preamble[start:i], "mathoperator"))
            elif cmd == "def":
                i = m.end()
                name, i = _read_control_name(preamble, i)
                # skip parameter text (e.g. #1#2) up to the body group
                while i < len(preamble) and preamble[i] != "{":
                    i += 1
                if i < len(preamble):
                    _, i = read_group(preamble, i)
                if name:
                    info.macros.append(Macro(name, preamble[start:i], "def"))
            else:  # newcommand / renewcommand / providecommand
                i = m.end()
                name, i = _read_control_name(preamble, i)
                _, i = read_optional(preamble, i)   # [nargs]
                _, i = read_optional(preamble, i)   # [default]
                i = skip_ws(preamble, i)
                if i < len(preamble) and preamble[i] == "{":
                    _, i = read_group(preamble, i)
                if name:
                    info.macros.append(Macro(name, preamble[start:i], cmd))
        except ValueError:
            continue  # malformed definition — skip, QA will notice missing macros
    return info


def _parse_newtheorem(s: str, i: int, starred: bool, info: PreambleInfo) -> None:
    i = skip_ws(s, i)
    env, i = read_group(s, i)
    env = env.strip()
    shared, i = read_optional(s, i)          # \newtheorem{lem}[thm]{Lemma}
    i = skip_ws(s, i)
    display, i = read_group(s, i)
    display = display.strip()
    _within, i = read_optional(s, i)         # \newtheorem{thm}{Theorem}[section]
    counter = (shared.strip() if shared else env)
    # If the shared counter refers to another declared env, share that env's counter key.
    if shared and shared.strip() in info.theorem_specs:
        counter = info.theorem_specs[shared.strip()].counter
    info.theorem_specs[env] = TheoremSpec(env=env, display=display,
                                          counter=counter, numbered=not starred)


def build_env_map(info: PreambleInfo) -> dict[str, TheoremSpec]:
    """Declared theorem environments, plus standard fallbacks for undeclared names."""
    env_map: dict[str, TheoremSpec] = {}
    for env, display in STANDARD_ENVS.items():
        env_map[env] = TheoremSpec(env=env, display=display, counter=env)
    env_map.update(info.theorem_specs)
    return env_map
