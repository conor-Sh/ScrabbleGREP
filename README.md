# ScrabbleGREP

`ScrabbleGREP` is a small Unix-style command-line tool for searching a
Scrabble lexicon.

It works like `grep`, except that it searches playable Scrabble words and
can optionally restrict results to words constructible from a Scrabble rack.

The program is intentionally not a Scrabble game or solver.

## Requirements

- Python 3.10+
- A CSW24 word list

CSW24 means Collins Scrabble Words 2024, the UK/international Scrabble
lexicon.

The lexicon is not bundled with this project because it is a copyrighted
word list. Obtain it from a legitimate source and install it locally.

## Installation

Clone the project and install it:

    python -m pip install .

For development:

    python -m pip install pytest
    pytest

## Installing the lexicon

The default lexicon is CSW24.

Put the word list at:

    data/CSW24.txt

or:

    ~/.local/share/scrabblegrep/CSW24.txt

You can also explicitly specify it:

    scrabblegrep -l /path/to/CSW24.txt '^QU'

or set:

    export SCRABBLEGREP_LEXICON=/path/to/CSW24.txt

The lexicon should contain one word per line.

Words are case-insensitive. Comments beginning with `#` and blank lines
are ignored.

## Basic usage

Search for words beginning with QU:

    scrabblegrep '^QU'

Search for words containing Q:

    scrabblegrep 'Q'

Find exactly three-letter words:

    scrabblegrep '^...$'

Find words beginning with R:

    scrabblegrep '^R'

Find words ending in ING:

    scrabblegrep 'ING$'

The pattern is an ordinary regular expression. `^`, `$`, `.`, character
classes, `+`, `?`, and other Python regular-expression features work as
expected.

The regex is matched against the complete word.

## Racks

Use `-r` to specify the tiles available to the player.

A `?` represents a blank.

For example:

    scrabblegrep -r AEIRST? '^...$'

finds exactly three-letter words that can be constructed from:

    A E I R S T ?

Letter multiplicities matter.

For example, a rack containing one `A` cannot make `BANANA` unless it
has enough additional blanks.

## Regex and rack filtering are independent

The rack does not alter regex semantics.

This:

    scrabblegrep -r AEIRST? 'R..'

means:

> Find rack-playable Scrabble words containing an R followed by any
> two characters.

This:

    scrabblegrep -r AEIRST? '^R..'

means:

> Find rack-playable three-character words beginning with R.

And:

    scrabblegrep -r AEIRST? '^R..$'

requires the whole word to be exactly three characters beginning with R.

## Scores

Every result contains:

    WORD    SCORE

For example:

    QUIZ    22
    READ    5

Without a rack, the normal tile value is used.

When a rack is supplied, blanks contribute zero points.

The default ordering is:

1. descending Scrabble score
2. descending word length
3. alphabetical order for deterministic output

## Unix pipelines

Output is deliberately compact so it can be piped into other Unix tools.

For example:

    scrabblegrep -r AEIRST? | grep '^RE'

Or:

    scrabblegrep '^QU' | sort

You can also redirect it:

    scrabblegrep -r AEIRST? '^...$' > candidates.txt

## Another lexicon

The `-l` option allows another compatible lexicon:

    scrabblegrep -l ./my-word-list.txt '^A....$'

The file must contain one playable word per line.

This makes the program usable with other Scrabble word lists without
changing the search engine.

## Design

The implementation intentionally has no database, server, network
dependency, or custom query language.

The main operation is:

    load words
        |
        v
    regex filter
        |
        v
    optional rack filter
        |
        v
    calculate score
        |
        v
    sort
        |
        v
    stdout

The lexicon is loaded once per invocation and regular expressions are
compiled once. This is fast enough for the roughly 280,000-word CSW24
lexicon while keeping the implementation small and easy to inspect.

## License

The `scrabblegrep` source code is MIT licensed.

The Scrabble lexicon is separate and is not covered by this license.
Use the applicable license/terms for the particular word list you
install.
