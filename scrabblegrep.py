#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path
from dataclasses import dataclass
from typing import Iterable


TILE_SCORES = {
    "A": 1, "B": 3, "C": 3, "D": 2, "E": 1, "F": 4, "G": 2,
    "H": 4, "I": 1, "J": 8, "K": 5, "L": 1, "M": 3, "N": 1,
    "O": 1, "P": 3, "Q": 10, "R": 1, "S": 1, "T": 1, "U": 1,
    "V": 4, "W": 4, "X": 8, "Y": 4, "Z": 10,
}

LEXICON_NAMES = {
    "CSW24": (
        "CSW24.txt",
        "csw24.txt",
        "CSW24.lst",
        "csw24.lst",
    )
}


@dataclass(frozen=True)
class Result:
    word: str
    score: int


def find_default_lexicon() -> Path | None:
    """
    Find a locally installed CSW24 lexicon.

    Search order:
      1. SCRABBLEGREP_LEXICON
      2. ./data/CSW24.txt
      3. ~/.local/share/scrabblegrep/CSW24.txt
      4. current directory
    """
    candidates: list[Path] = []

    env_path = os.environ.get("SCRABBLEGREP_LEXICON")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    names = LEXICON_NAMES["CSW24"]

    here = Path(__file__).resolve().parent
    candidates.extend(here / "data" / name for name in names)

    data_home = Path(
        os.environ.get(
            "XDG_DATA_HOME",
            "~/.local/share",
        )
    ).expanduser()

    candidates.extend(
        data_home / "scrabblegrep" / name
        for name in names
    )

    candidates.extend(Path.cwd() / name for name in names)

    for path in candidates:
        if path.is_file():
            return path

    return None


def load_lexicon(path: Path) -> tuple[str, ...]:
    """
    Load one playable word per line.

    Blank lines and lines beginning with '#' are ignored.
    Words must consist solely of A-Z characters.
    """
    words: set[str] = set()

    try:
        with path.open("r", encoding="utf-8") as fh:
            for lineno, raw in enumerate(fh, 1):
                word = raw.strip().upper()

                if not word or word.startswith("#"):
                    continue

                if any(ch not in TILE_SCORES for ch in word):
                    raise ValueError(
                        f"{path}:{lineno}: invalid word {word!r}; "
                        "expected A-Z letters"
                    )

                words.add(word)

    except OSError as exc:
        raise SystemExit(
            f"scrabblegrep: cannot read lexicon {path}: {exc}"
        ) from exc

    return tuple(words)


def parse_rack(rack: str) -> tuple[Counter[str], int]:
    rack = rack.upper()

    for char in rack:
        if char != "?" and char not in TILE_SCORES:
            raise ValueError(
                "rack must contain only A-Z letters and '?' for blanks"
            )

    letters = Counter(char for char in rack if char != "?")
    blanks = rack.count("?")

    return letters, blanks


def playable_from_rack(
    word: str,
    letters: Counter[str],
    blanks: int,
) -> bool:
    """
    Return whether WORD can be constructed from the rack.

    Real tiles are consumed first; any excess letter requirements
    are satisfied by blanks.
    """
    needed = Counter(word)

    missing = 0

    for char, count in needed.items():
        available = letters.get(char, 0)
        missing += max(0, count - available)

        if missing > blanks:
            return False

    return True


def score_from_rack(
    word: str,
    letters: Counter[str],
) -> int:
    """
    Score WORD using the real tiles in LETTERS.

    Any letter beyond the available real-tile count must be a blank
    and therefore contributes zero.
    """
    needed = Counter(word)
    score = 0

    for char, count in needed.items():
        real_tiles = min(count, letters.get(char, 0))
        score += real_tiles * TILE_SCORES[char]

    return score


def normal_score(word: str) -> int:
    return sum(TILE_SCORES[char] for char in word)


def search(
    words: Iterable[str],
    pattern: re.Pattern[str],
    rack: str | None = None,
) -> list[Result]:
    """
    Apply regex and rack filters independently.

    Regex matching is always performed against the complete word.
    """
    letters: Counter[str] | None = None
    blanks = 0

    if rack is not None:
        letters, blanks = parse_rack(rack)

    results: list[Result] = []

    for word in words:
        # Regex semantics are completely independent of rack handling.
        if pattern.search(word) is None:
            continue

        if letters is not None:
            if not playable_from_rack(word, letters, blanks):
                continue

            score = score_from_rack(word, letters)
        else:
            score = normal_score(word)

        results.append(Result(word, score))

    # Primary: descending score
    # Secondary: descending length
    # Tertiary: alphabetical, simply to make output deterministic.
    results.sort(
        key=lambda result: (
            -result.score,
            -len(result.word),
            result.word,
        )
    )

    return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrabblegrep",
        description=(
            "grep-like searching of a Scrabble word list. "
            "Patterns use normal Python regular expressions."
        ),
        epilog=(
            "Examples:\n"
            "  scrabblegrep '^QU'\n"
            "  scrabblegrep 'Q'\n"
            "  scrabblegrep '^...$'\n"
            "  scrabblegrep -r AEIRST? '^...$'\n"
            "  scrabblegrep -r AEIRST? '^R..$'\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "pattern",
        nargs="?",
        default=".*",
        help="regular expression to search for",
    )

    parser.add_argument(
        "-r",
        "--rack",
        metavar="RACK",
        help="Scrabble rack; use ? for a blank, e.g. AEIRST?",
    )

    parser.add_argument(
        "-l",
        "--lexicon",
        metavar="FILE",
        help="lexicon file; default is locally installed CSW24",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        pattern = re.compile(
            args.pattern,
            re.IGNORECASE,
        )
    except re.error as exc:
        parser.error(f"invalid regular expression: {exc}")

    if args.rack is not None:
        try:
            parse_rack(args.rack)
        except ValueError as exc:
            parser.error(str(exc))

    if args.lexicon:
        lexicon_path = Path(args.lexicon).expanduser()
    else:
        lexicon_path = find_default_lexicon()

    if lexicon_path is None:
        print(
            "scrabblegrep: no CSW24 lexicon found.\n"
            "\n"
            "Install a licensed CSW24 word list at one of:\n"
            "  data/CSW24.txt\n"
            "  ~/.local/share/scrabblegrep/CSW24.txt\n"
            "\n"
            "or set SCRABBLEGREP_LEXICON, or use -l FILE.",
            file=sys.stderr,
        )
        return 2

    words = load_lexicon(lexicon_path)

    for result in search(words, pattern, args.rack):
        print(f"{result.word}\t{result.score}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
