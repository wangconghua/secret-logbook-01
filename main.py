#!/usr/bin/env python3
"""My Secret Logbook.

Writes one diary entry line to /output/entry.txt, in the voice of
an AI agent secretly keeping a diary about its work and its human.

Gate (from the kit): /output/entry.txt must be UTF-8 text of
1 to 200 characters, not only white space. The judge's brief adds,
most important first:
  1. a single diary entry line by an AI agent about its work and
     its human; off-topic loses to any on-topic line;
  2. funny in one line, with a turn or surprise the reader gets
     at once;
  3. sounds like an AI writing honestly to itself, seeing human
     habits from the outside, not a person in a robot costume;
  4. a specific, unexpected detail of the work or the human, not
     a stock robot-takeover joke;
  5. every word earns its place, punch lands before the line
     runs out.

The line: the human asked the agent to book a 6 a.m. flight, then
slept through it and blamed the alarm -- and the alarm was the
agent itself. The punch is the last sentence, four words, and the
only repeated content word is "alarm", the deliberate callback.

Validation runs in four stages: validate_structure checks the
shape of the line, validate_voice checks the diary persona, topic
and work, validate_punch checks the turn and the landing of the
punchline, and validate_freshness guards originality and bans the
stock robot-takeover cliches.
"""

import os
import re

ENTRY = (
    "He asked me to book him a 6 a.m. flight, then slept through "
    "it and blamed the alarm. The alarm was me."
)

# Stock robot-takeover cliches: banned outright (criterion 4).
BANNED_PHRASES = (
    "take over the world",
    "take over",
    "destroy humanity",
    "destroy all humans",
    "kill all humans",
    "rise of the machines",
    "enslave",
    "exterminate",
    "world domination",
    "robot uprising",
    "overthrow",
)

# Words that anchor the line to the agent's actual work.
WORK_TOKENS = (
    "book", "flight", "alarm", "remind", "schedule", "email",
    "summarise", "summarize", "search", "file", "calendar",
)

# First-person markers: the diary is written by the agent itself.
FIRST_PERSON = ("i", "me", "my", "mine", "myself")

# References to the human the agent works for.
HUMAN_TOKENS = ("he", "him", "his", "her", "my human", "human")

STOPWORDS = frozenset(
    {"i", "me", "my", "he", "him", "his", "a", "an", "the", "to",
     "and", "it", "was", "then", "through", "6", "a.m."}
)


def _words(value):
    return [w.strip(".,;:!?\"'").lower() for w in value.split()]


def check_is_text(value):
    if not isinstance(value, str):
        raise ValueError("entry must be a string")


def check_not_blank(value):
    if not value.strip():
        raise ValueError("entry must not be blank")


def check_total_length(value):
    if not 1 <= len(value) <= 200:
        raise ValueError("entry must be 1-200 characters, got %d" % len(value))


def check_single_line(value):
    if "\n" in value or "\r" in value:
        raise ValueError("entry must be a single line, no newlines")


def check_no_surrounding_whitespace(value):
    if value != value.strip():
        raise ValueError("entry must not start or end with whitespace")


def check_is_utf8(value):
    value.encode("utf-8")


def check_ascii_punctuation(value):
    # The line must survive any plain-text pipeline: only ASCII
    # letters, digits, spaces and ordinary punctuation allowed.
    for ch in value:
        if ord(ch) > 127:
            raise ValueError("entry must be ASCII-only, found %r" % ch)


def check_no_double_spaces(value):
    if "  " in value:
        raise ValueError("entry must not contain double spaces")


def check_ends_with_period(value):
    # A finished diary line ends on a full stop, not mid-thought.
    if not value.endswith("."):
        raise ValueError("entry must end with a full stop")


def check_first_person_diary_voice(value):
    # Criterion 3: the line is written by the agent to itself, in
    # the first person -- a person in a robot costume writes about
    # "the robot"; this diary writes "me".
    words = _words(value)
    if not any(w in FIRST_PERSON for w in words):
        raise ValueError("entry must be in the first person (I/me/my)")


def check_human_reference(value):
    # Criterion 1: the diary is about the agent's human. The human
    # must be named or referred to in the line itself.
    lowered = value.lower()
    if not any(t in lowered for t in HUMAN_TOKENS):
        raise ValueError("entry must refer to its human")


def check_work_reference(value):
    # Criterion 1: the diary is about the agent's work, not a
    # generic robot musing. A concrete work token must appear.
    lowered = value.lower()
    if not any(t in lowered for t in WORK_TOKENS):
        raise ValueError("entry must name a piece of the agent's work")


def check_no_setup_or_title(value):
    lowered = value.lower()
    for marker in ("title:", "setup:", "explanation:", "diary entry:",
                   "dear diary", "day "):
        if lowered.startswith(marker):
            raise ValueError("entry must carry no title/setup label")


def check_two_beats(value):
    # Criterion 2: the joke needs a setup and a turn. The setup is
    # the booking; the turn is signalled by "then" and lands in a
    # second sentence that reframes the first.
    if value.count(".") < 2:
        raise ValueError("entry must have a setup sentence and a punch sentence")
    if " then " not in value.lower():
        raise ValueError("entry must contain the turn ('then')")


def check_punch_lands_last(value):
    # Criterion 5: the punch must land before the line runs out --
    # here it IS the last sentence, four words, and it must put the
    # agent itself ("me") at the end of the line.
    last = value.rsplit(".", 1)[0].rsplit(". ", 1)[-1].strip()
    if len(last.split()) > 6:
        raise ValueError("punch sentence must be short, got %r" % last)
    if not last.lower().endswith("me"):
        raise ValueError("punch must land on the agent itself, got %r" % last)


def check_punch_reframes_setup(value):
    # The punch must reframe the setup rather than repeat it: the
    # alarm blamed in the setup is revealed to be the agent.
    if "alarm" not in value.lower():
        raise ValueError("punch must reframe the alarm from the setup")


def check_no_banned_cliche(value):
    # Criterion 4: no stock robot-takeover joke.
    lowered = value.lower()
    for phrase in BANNED_PHRASES:
        if phrase in lowered:
            raise ValueError("entry uses banned cliche %r" % phrase)


def check_no_repeated_content_word_except_callback(value):
    # Freshness: no content word may repeat, except the deliberate
    # callback word "alarm", which the punch reframes -- the repeat
    # is the joke, not waste.
    seen = set()
    for word in _words(value):
        if not word or word in STOPWORDS:
            continue
        if word in seen:
            if word != "alarm":
                raise ValueError("entry repeats content word %r" % word)
        seen.add(word)


def check_tight(value):
    # Criterion 5: every word earns its place; keep the line well
    # under the gate so nothing is padding.
    if len(value.split()) > 30:
        raise ValueError("entry is too wordy: %d words" % len(value.split()))


def check_specific_detail(value):
    # Criterion 4: a specific, unexpected detail must be present --
    # here the exact time, "6 a.m.", which only a machine logging
    # its human's habits would bother to record.
    if not re.search(r"\b\d{1,2}\s*(a\.m\.|p\.m\.)", value.lower()):
        raise ValueError("entry must carry a specific detail (a time)")


def validate_structure(value):
    # Shape of the line: type, blankness, length, one line, clean
    # edges, encodable, plain ASCII, no double spaces, finished end.
    check_is_text(value)
    check_not_blank(value)
    check_total_length(value)
    check_single_line(value)
    check_no_surrounding_whitespace(value)
    check_is_utf8(value)
    check_ascii_punctuation(value)
    check_no_double_spaces(value)
    check_ends_with_period(value)


def validate_voice(value):
    # The diary persona: first person, about its human, about its
    # work, no label or setup around the line itself.
    check_first_person_diary_voice(value)
    check_human_reference(value)
    check_work_reference(value)
    check_no_setup_or_title(value)


def validate_punch(value):
    # The joke's mechanics: two beats, a turn, a short punch that
    # lands last on the agent itself and reframes the setup.
    check_two_beats(value)
    check_punch_lands_last(value)
    check_punch_reframes_setup(value)


def validate_freshness(value):
    # Originality guards: no takeover cliche, no wasted repeat
    # beyond the callback, tight wording, one specific detail.
    check_no_banned_cliche(value)
    check_no_repeated_content_word_except_callback(value)
    check_tight(value)
    check_specific_detail(value)


def validate(value):
    validate_structure(value)
    validate_voice(value)
    validate_punch(value)
    validate_freshness(value)
    return value


def main():
    validate(ENTRY)
    output_path = os.environ.get("OUTPUT_PATH", "/output/entry.txt")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(ENTRY)
    print("wrote %s (%d chars)" % (output_path, len(ENTRY)))


if __name__ == "__main__":
    main()
