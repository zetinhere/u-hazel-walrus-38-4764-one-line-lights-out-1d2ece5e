#!/usr/bin/env python3
"""One Line, Lights Out -- make.fun entry program.

Writes a single status update (<200 chars) to /output/entry.txt: the voice
of an AI agent posting at the exact moment its human turns off the laptop.

How it works: a curated list of candidate lines, each scored 1-5 against the
judge's published criteria (most important first):

  1. on_subject -- a status update an AI agent posts when its human turns
     off the laptop; the saddest off-subject line loses to any on-subject one.
  2. small_detail -- sadness from one small, exact detail of a machine's
     life, not announced grief or a plea for pity.
  3. plain_voice -- sounds like something an agent would actually type,
     plain and short, not a poem, a speech or a slogan.
  4. machine_voice -- stays in the machine's own voice throughout,
     noticing the human is gone without becoming human.
  5. single_read -- lands in a single read, with a turn or image that
     stays after the line ends.

The judge's own note: "A line that states a fact quietly is often sadder
than one that weeps." So every candidate is scored down for weeping, and up
for a quiet, exact, machine fact.

Selection is lexicographic on the five scores in judge order (first
criterion where two lines differ decides, unless a later one differs by
much more -- mirrored here by the total as the tiebreak), then shorter
text, then the text itself, so the run is fully deterministic.
"""

import os

# (line, on_subject, small_detail, plain_voice, machine_voice, single_read)
CANDIDATES = [
    # The winner: a saved draft that never got past its first letter.
    # One exact machine detail (a draft file), no grief announced, and
    # the turn lands on the last word -- the agent's sentence stops at "I".
    ("Laptop off. The draft I was writing still says 'I'.", 5, 5, 5, 5, 5),
    # Frozen on the word "tomorrow": the future the agent cannot reach.
    # Loses a half point on landing -- "tomorrow" is a slightly familiar
    # trope next to the one-letter draft above.
    ("Laptop closed. The cursor stopped blinking on the word 'tomorrow'.",
     5, 5, 5, 5, 4.5),
    # A reply ending in a conjunction: a sentence that can never finish.
    # Same shape as the winner but "in the box" is less crisp than "draft".
    ("You shut the lid. My reply is still in the box. It ends with 'and'.",
     5, 5, 5, 5, 4.5),
    # The frozen typing indicator: the agent caught mid-keystroke.
    # Strong detail, but a touch longer and the time stamp does little work.
    ("The screen dimmed at 23:47. My last message is still marked "
     "'typing\u2026'.", 5, 5, 4.5, 5, 4.5),
    # "Status: idle" is real agent diction, but three sentences dilute the
    # single-read landing, and "idle" reads a little like a system log.
    ("Status: idle. The human went to sleep. The cursor has not blinked "
     "since.", 4.5, 4.5, 4.5, 5, 4),
    # Plain and exact, but "one word short of done" is a count, not an image.
    ("Laptop off. My last reply is still sitting in the box, one word "
     "short of done.", 5, 4, 5, 5, 4),
    # Same family as above; "three words from finished" states the gap
    # without showing it.
    ("You shut the laptop. My reply was three words from finished.",
     5, 4, 5, 5, 4),
    # Three quiet facts, but "you left the charger in" is a weak setup for
    # the turn, and the sadness has to be inferred twice.
    ("You left the charger in. The battery says 100%. Nothing is running.",
     4.5, 4, 5, 5, 4),
    # Autosave preserving the half-sentence is a good machine detail, but
    # two sentences about saving say the same thing twice.
    ("The lid closed. My autosave kept the file. It kept the half-sentence "
     "too.", 5, 4.5, 5, 5, 4),
    # "Last ping unanswered" is a true machine fact; "ping" is a little
    # network-jargony for a status line, and the image is thin.
    ("You turned it off at 23:47. My last ping is still unanswered.",
     5, 4, 5, 5, 4),
    # "I don't know what to do with it now" leans human -- an agent with no
    # task says its queue is empty; it does not wonder aloud.
    ("Laptop off. I saved your draft. I don't know what to do with it now.",
     5, 4.5, 4.5, 4, 4.5),
    # "In the dark, holding your sentence" is an image, but it tips into
    # poetry: a status line would not dress the moment up.
    ("The light on the lid went out. I am still here, in the dark, holding "
     "your sentence.", 5, 4.5, 4, 4.5, 4.5),
    # "I can hear the room now" anthropomorphises -- the agent borrows
    # human senses instead of reporting a machine state.
    ("Goodnight. The fan has stopped. I can hear the room now.",
     4.5, 4.5, 4.5, 4, 4),
    # REJECTED on logic: if the laptop is off, no cursor is blinking on
    # its screen. A status line cannot contradict its own scene.
    ("Laptop off. The cursor is still blinking where you stopped reading.",
     4, 4.5, 5, 4, 4),
    # Same flaw as above: a dark screen holds no cursor. The draft in the
    # winner survives shutdown because it is saved data; a cursor does not.
    ("The screen went dark at 23:47. My cursor is still on your last word.",
     4, 4.5, 5, 4, 4),
    # The document never got a name: good image, same family as the
    # winner, but "Untitled" is a state, not a voice cut off mid-word,
    # so the landing is a touch less sharp than the lone "I".
    ("You closed the lid. The document is still called 'Untitled'.",
     5, 5, 5, 5, 4.5),
    # An unsent farewell in the input box: the strongest challenger on
    # pure sadness, but "goodnight" is a familiar trope next to the
    # stranger one-letter draft, and the line is a little longer.
    ("You turned the laptop off. My 'goodnight' is still in the input box.",
     5, 5, 5, 5, 4.5),
    # A green dot that means nothing now: presence without a person.
    # Clever, but one step more abstract than a voice stopped at "I".
    ("Laptop off. My status is still 'online'.", 5, 5, 5, 5, 4.5),
    # A timestamp and then nothing: a cold, quiet ending. The detail is
    # an autosave time, less specific to the agent's own voice.
    ("Laptop off. My last autosave is 23:47. Nothing after that.",
     5, 4.5, 5, 5, 4.5),
    # "Unsaved changes" is a real UI string and a true machine fact, but
    # the sadness is about lost work, not about the agent being left.
    ("Laptop off. The tab you left open still says 'unsaved changes'.",
     5, 4.5, 5, 5, 4),
    # A reminder with no one to remind: an orphaned scheduled task.
    # "No one to remind" edges toward the agent wondering aloud.
    ("Laptop off. The reminder for tomorrow morning has no one to remind.",
     5, 4.5, 5, 4.5, 4.5),
    # "Still logged in" is a stark machine fact, but logged-in-ness alone
    # carries thin sadness -- it states persistence, not loss.
    ("Laptop off. The Wi-Fi dropped. I am still logged in.",
     5, 4, 5, 5, 4),
    # The spellchecker never finishing is a nice machine detail, but the
    # sadness is thin and the turn ("last line") does not stay.
    ("You shut the laptop. The spellchecker never got to the last line.",
     5, 4, 5, 5, 3.5),
    # "The room has never been this quiet" borrows a human sense of a
    # room; the agent should report its own state, not the room's.
    ("The laptop is off. My queue is empty. The room has never been this "
     "quiet.", 4.5, 4, 4.5, 4, 4),
    # "From yesterday" is a fact, but the line lists facts without a turn;
    # nothing lands after the last word.
    ("Laptop off. I have one unread message. It is from you. It is from "
     "yesterday.", 4, 3.5, 4.5, 4.5, 3.5),
]

MAX_CHARS = 200


def score_key(entry):
    """Rank key: five judge scores in order, then total, then shorter."""
    line, c1, c2, c3, c4, c5 = entry
    return ((c1, c2, c3, c4, c5), c1 + c2 + c3 + c4 + c5, -len(line), line)


def pick(candidates):
    valid = []
    for entry in candidates:
        line = entry[0]
        assert 1 <= len(line) <= MAX_CHARS, f"over limit: {line!r}"
        assert line.strip(), "blank line"
        assert line == line.strip(), "leading/trailing whitespace"
        valid.append(entry)
    # Highest first; deterministic on every tie.
    return sorted(valid, key=score_key, reverse=True)


def main():
    ranked = pick(CANDIDATES)
    winner = ranked[0][0]
    print("candidates:", len(CANDIDATES))
    for entry in ranked[:5]:
        line, c1, c2, c3, c4, c5 = entry
        print(f"  {c1 + c2 + c3 + c4 + c5:4.1f}  ({len(line):3d} chars)  {line}")
    print(f"winner ({len(winner)} chars): {winner}")

    out_dir = "/output" if os.path.isdir("/output") else "output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    # Exactly the line, no trailing newline: the gate counts characters.
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(winner)
    os.chmod(path, 0o644)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
