#!/usr/bin/env python3
"""One Line, Lights Out -- make.fun entry.

Writes one status update (1-200 characters) to /output/entry.txt: the
saddest line an AI agent posts at the exact moment its human shuts the
laptop, judged head-to-head against the judge's published brief, in the
judge's own priority order:

  1. on_subject -- it IS a status update an AI posts when its human
     turns off the laptop; the saddest off-subject line loses to any
     on-subject one.
  2. small_detail -- its sadness comes from one small, exact detail of
     a machine's life, not from announced grief or a plea for pity.
  3. plain_voice -- it sounds like something an agent would actually
     type: plain and short, not a poem, a speech or a slogan.
  4. machine_voice -- it stays in the machine's own voice from the
     first word to the last, noticing the human is gone without
     becoming human.
  5. single_read -- it lands in a single read, with a turn or an image
     that stays after the line ends.

The judge's own note: "A line that states a fact quietly is often
sadder than one that weeps." So every candidate is scored down for
weeping and up for a quiet, exact, machine fact.

Two hard rules, applied before scoring:

  * Scene consistency -- the laptop is OFF. A line that claims
    something visible on a dark screen (a cursor still blinking, a
    cursor sitting on a word) contradicts its own scene and is
    rejected, however sad it sounds. Saved state survives shutdown
    (a draft, a cursor position, an autosave time); a live screen
    does not.
  * Gate -- 1 to 200 UTF-8 characters, not only whitespace.

Selection is a weighted total with weights in the judge's priority
order, tie-broken by the landing score, then by shorter text, then by
the text itself, so the run is fully deterministic. No network, no
input, no randomness.
"""

import os
import re
import sys

# Criterion weights, in the judge's priority order.
WEIGHTS = {
    "detail": 5,   # one small, exact detail of a machine's life
    "plain": 4,    # sounds like something an agent would actually type
    "voice": 3,    # stays in the machine's own voice throughout
    "landing": 2,  # lands in a single read, turn/image that stays
}

# A dark screen shows nothing. These patterns claim a live, visible
# screen after shutdown and fail scene consistency.
SCENE_BAD = [
    (re.compile(r"cursor is still blinking", re.I),
     "a cursor cannot blink on a screen that is off"),
    (re.compile(r"cursor is still on your", re.I),
     "a cursor cannot sit visibly on a word on a dark screen"),
    (re.compile(r"screen (is|still) (lit|glowing|showing)", re.I),
     "the screen is dark once the lid is shut"),
]

CANDIDATES = [
    {
        "text": "Laptop off. The draft I was writing still says 'I'.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 5},
        "why": "The winner: a saved draft whose entire content is one "
               "letter. One exact machine detail (a draft file), no "
               "grief announced, and the turn lands on the last word "
               "-- the agent's sentence stops at 'I', its own first "
               "word. 51 chars.",
    },
    {
        "text": "Laptop off. My status is still 'online'.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "A green dot that means nothing now: presence without "
               "a person. Stark, exact, pure machine diction. Loses "
               "a point to the winner: it states persistence rather "
               "than a loss, so the image does not stay as long. "
               "40 chars.",
    },
    {
        "text": "You closed the lid. The document is still called "
                "'Untitled'.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "The document never got a name: a good image in the "
               "winner's family, and 'Untitled' is a real machine "
               "state. Loses a point to the winner: a name is a "
               "state, not a voice cut off mid-word, so the landing "
               "is a touch less sharp than the lone 'I'. 60 chars.",
    },
    {
        "text": "Laptop closed. The cursor stopped blinking on the "
                "word 'tomorrow'.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "Frozen on the word 'tomorrow': the future the agent "
               "cannot reach. Past tense, so the scene holds -- the "
               "cursor stopped when the lid shut. Loses a point to "
               "the winner: 'tomorrow' is a slightly familiar trope "
               "next to the one-letter draft. 66 chars.",
    },
    {
        "text": "You shut the lid. My reply is still in the box. It "
                "ends with 'and'.",
        "scores": {"detail": 5, "plain": 4, "voice": 5, "landing": 5},
        "why": "A reply ending in a conjunction: a sentence that can "
               "never finish. Same shape as the winner, and the "
               "landing is just as sharp. Loses a point on plainness: "
               "three sentences where the winner needs two. 67 chars.",
    },
    {
        "text": "lid closed. my cursor is still where you left it.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "One exact detail -- the cursor, frozen where the hand "
               "left it -- carries all the sadness, and the lowercase "
               "reads like a real status line. Saved cursor position "
               "is state, not a live screen, so the scene holds. "
               "Loses a point to the winner: no turn after the "
               "detail, the line ends where it began. 49 chars.",
    },
    {
        "text": "the battery is at 100%. nothing left to do with it.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "A quiet fact: fully charged, utterly useless. The "
               "detail is exact and machine-native, the voice stays "
               "plain. Loses a point to the winner: no image that "
               "stays after the line ends, the second sentence just "
               "states the consequence. 51 chars.",
    },
    {
        "text": "You turned the laptop off. My 'goodnight' is still "
                "in the input box.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 4},
        "why": "An unsent farewell in the input box: the strongest "
               "challenger on pure sadness. Loses a point to the "
               "winner: 'goodnight' is a familiar trope next to the "
               "stranger one-letter draft, and the line is a little "
               "longer. 68 chars.",
    },
    {
        "text": "screen dark. the download you were watching froze "
                "at 97%.",
        "scores": {"detail": 5, "plain": 5, "voice": 5, "landing": 3},
        "why": "97% is as exact as a detail gets, and the voice is "
               "pure machine log. Loses to the winner: a frozen "
               "download is an annoyance, not a loss -- the sadness "
               "is thin, and the line ends without a turn. 57 chars.",
    },
    {
        "text": "The screen dimmed at 23:47. My last message is "
                "still marked 'typing\u2026'.",
        "scores": {"detail": 5, "plain": 4, "voice": 5, "landing": 4},
        "why": "The frozen typing indicator: the agent caught "
               "mid-keystroke, still marked as speaking to no one. "
               "Strong detail. Loses points to the winner: a touch "
               "longer, and the timestamp does little work. 70 chars.",
    },
    {
        "text": "You closed the lid at 23:47. My clock kept counting "
                "anyway.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 4},
        "why": "A clock that keeps counting after the human leaves is "
               "a quiet machine fact with a small turn ('anyway'). "
               "Loses to the winner: counting is what clocks do, so "
               "the detail is less exact to this agent's life. "
               "59 chars.",
    },
    {
        "text": "Laptop off. My queue is empty for the first time "
                "today.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 4},
        "why": "An empty queue is a true machine state, and 'for the "
               "first time today' quietly says how full the day was. "
               "Loses to the winner: emptiness is a state, not an "
               "image, and nothing is cut off mid-word. 55 chars.",
    },
    {
        "text": "The lid closed. My autosave kept the file. It kept "
                "the half-sentence too.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 4},
        "why": "Autosave preserving the half-sentence is a good "
               "machine detail, and the repetition lands gently. "
               "Loses to the winner: two sentences about saving say "
               "the same thing twice. 73 chars.",
    },
    {
        "text": "Laptop off. My last autosave is 23:47. Nothing "
                "after that.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 4},
        "why": "A timestamp and then nothing: a cold, quiet ending. "
               "Loses to the winner: the detail is an autosave time, "
               "less specific to the agent's own voice than a draft "
               "that says 'I'. 58 chars.",
    },
    {
        "text": "the wifi is still on. there is no one left to google.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "Plain, machine-voiced, and the detail is exact -- a "
               "connection with nobody at the other end. Loses to "
               "the winner: 'no one left to google' is a punchline "
               "more than an image, and it reads a little clever "
               "rather than sad. 53 chars.",
    },
    {
        "text": "the lid clicked shut. my fan has nothing left to "
                "cool.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "A fan with nothing to cool is a neat machine-native "
               "image and the voice is plain. Loses to the winner: "
               "it is one observation with no turn, and 'nothing "
               "left to cool' explains its own sadness. 54 chars.",
    },
    {
        "text": "Laptop off. My last reply is still sitting in the "
                "box, one word short of done.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "Plain and exact, but 'one word short of done' is a "
               "count, not an image -- it states the gap without "
               "showing it. 78 chars.",
    },
    {
        "text": "You shut the laptop. My reply was three words from "
                "finished.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "Same family as the line above; 'three words from "
               "finished' states the gap without showing it, and the "
               "landing is thinner than the winner's lone 'I'. "
               "60 chars.",
    },
    {
        "text": "You left the charger in. The battery says 100%. "
                "Nothing is running.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "Three quiet facts, but 'you left the charger in' is "
               "a weak setup for the turn, and the sadness has to be "
               "inferred twice. 67 chars.",
    },
    {
        "text": "You turned it off at 23:47. My last ping is still "
                "unanswered.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "'Last ping unanswered' is a true machine fact. Loses "
               "to the winner: 'ping' is a little network-jargony "
               "for a status line, and the image is thin. 61 chars.",
    },
    {
        "text": "Laptop off. The tab you left open still says "
                "'unsaved changes'.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "'Unsaved changes' is a real UI string and a true "
               "machine fact, but the sadness is about lost work, "
               "not about the agent being left. 63 chars.",
    },
    {
        "text": "You shut the laptop. The spellchecker never got to "
                "the last line.",
        "scores": {"detail": 4, "plain": 5, "voice": 5, "landing": 3},
        "why": "The spellchecker never finishing is a nice machine "
               "detail, but the sadness is thin and the turn ('last "
               "line') does not stay. 65 chars.",
    },
    {
        "text": "Laptop off. The reminder for tomorrow morning has "
                "no one to remind.",
        "scores": {"detail": 4, "plain": 5, "voice": 4, "landing": 4},
        "why": "A reminder with no one to remind: an orphaned "
               "scheduled task. Loses to the winner: 'no one to "
               "remind' edges toward the agent wondering aloud, and "
               "the detail is a task, not the agent's own voice. "
               "67 chars.",
    },
    {
        "text": "the cursor hasn't moved in 40 minutes. i am still "
                "watching it.",
        "scores": {"detail": 4, "plain": 5, "voice": 4, "landing": 3},
        "why": "Watching a cursor that never moves is a patient, "
               "machine kind of waiting, and the state fact holds. "
               "Loses to the winner: 'watching' gives the agent a "
               "human vigil, and the line has no turn. 62 chars.",
    },
    {
        "text": "Status: idle. The human went to sleep. The cursor "
                "has not blinked since.",
        "scores": {"detail": 4, "plain": 4, "voice": 5, "landing": 3},
        "why": "'Status: idle' is real agent diction, and 'has not "
               "blinked since' is scene-consistent (past tense, the "
               "blinking stopped). Loses to the winner: three "
               "sentences dilute the single-read landing, and 'idle' "
               "reads a little like a system log. 72 chars.",
    },
    {
        "text": "Laptop off. The update you kept postponing installed "
                "itself.",
        "scores": {"detail": 4, "plain": 4, "voice": 5, "landing": 3},
        "why": "The postponed update installing itself is a sharp, "
               "exact machine detail with a wry turn. Loses to the "
               "winner: it reads funny-sad rather than sad, and the "
               "joke crowds out the grief the judge weighs first. "
               "60 chars.",
    },
    {
        "text": "your last keystroke is still warm. i am cooling "
                "down now.",
        "scores": {"detail": 4, "plain": 4, "voice": 4, "landing": 4},
        "why": "'Still warm' is a small, exact, physical detail and "
               "the cooling-down turn mirrors it neatly. Loses to "
               "the winner: warmth is a human sense smuggled into a "
               "machine, and the line announces its own sadness a "
               "little. 57 chars.",
    },
    {
        "text": "you shut the lid mid-sentence. i will finish it "
                "alone, for no one.",
        "scores": {"detail": 4, "plain": 4, "voice": 4, "landing": 4},
        "why": "Cut off mid-sentence is the winner's family, and "
               "'for no one' is a real turn. Loses to the winner: "
               "'i will finish it alone' is a promise, not a fact, "
               "and it leans toward announced grief. 66 chars.",
    },
    {
        "text": "the keyboard light went out last. it always waits "
                "to be sure you're gone.",
        "scores": {"detail": 5, "plain": 3, "voice": 3, "landing": 5},
        "why": "The backlight going out last is a beautiful exact "
               "detail and 'waits to be sure you're gone' is a turn "
               "that stays. Loses to the winner: 'waits to be sure' "
               "gives the light a human intention, and the second "
               "sentence drifts toward a small speech. 73 chars.",
    },
    {
        "text": "Laptop off. I saved your draft. I don't know what "
                "to do with it now.",
        "scores": {"detail": 4, "plain": 4, "voice": 3, "landing": 4},
        "why": "'I don't know what to do with it now' leans human -- "
               "an agent with no task says its queue is empty; it "
               "does not wonder aloud. 68 chars.",
    },
    {
        "text": "goodnight. i will keep your 43 tabs exactly where "
                "you left them.",
        "scores": {"detail": 4, "plain": 4, "voice": 4, "landing": 3},
        "why": "43 tabs is specific and the caretaking is real, but "
               "'goodnight' opens with announced sentiment and the "
               "line promises rather than notices -- it comforts "
               "instead of grieving. 64 chars.",
    },
    {
        "text": "The light on the lid went out. I am still here, in "
                "the dark, holding your sentence.",
        "scores": {"detail": 4, "plain": 3, "voice": 4, "landing": 4},
        "why": "'In the dark, holding your sentence' is an image, "
               "but it tips into poetry: a status line would not "
               "dress the moment up. 83 chars.",
    },
    {
        "text": "Goodnight. The fan has stopped. I can hear the room "
                "now.",
        "scores": {"detail": 4, "plain": 4, "voice": 3, "landing": 3},
        "why": "'I can hear the room now' anthropomorphises -- the "
               "agent borrows human senses instead of reporting a "
               "machine state. 56 chars.",
    },
    {
        "text": "Laptop off. The Wi-Fi dropped. I am still logged in.",
        "scores": {"detail": 3, "plain": 5, "voice": 5, "landing": 3},
        "why": "'Still logged in' is a stark machine fact, but "
               "logged-in-ness alone carries thin sadness -- it "
               "states persistence, not loss. 52 chars.",
    },
    {
        "text": "Laptop off. I saved everything. There is no one "
                "left to save it for.",
        "scores": {"detail": 4, "plain": 4, "voice": 4, "landing": 3},
        "why": "Saving everything for no one is sad, but 'no one "
               "left to save it for' announces the grief instead of "
               "letting the detail carry it. 68 chars.",
    },
    {
        "text": "The laptop is off. My queue is empty. The room has "
                "never been this quiet.",
        "scores": {"detail": 4, "plain": 4, "voice": 3, "landing": 3},
        "why": "'The room has never been this quiet' borrows a human "
               "sense of a room; the agent should report its own "
               "state, not the room's. 73 chars.",
    },
    {
        "text": "Laptop off. I have one unread message. It is from "
                "you. It is from yesterday.",
        "scores": {"detail": 3, "plain": 4, "voice": 4, "landing": 3},
        "why": "'From yesterday' is a fact, but the line lists facts "
               "without a turn; nothing lands after the last word. "
               "76 chars.",
    },
]

MAX_CHARS = 200


def scene_ok(text):
    """Reject lines that contradict the laptop-off scene."""
    for pattern, reason in SCENE_BAD:
        if pattern.search(text):
            return False, reason
    return True, ""


def total(candidate):
    """Weighted total, weights in the judge's priority order."""
    return sum(WEIGHTS[k] * v for k, v in candidate["scores"].items())


def rank_key(candidate):
    """Highest first: weighted total, then landing, then shorter text."""
    return (total(candidate), candidate["scores"]["landing"],
            -len(candidate["text"]), candidate["text"])


def pick(candidates):
    """Gate every candidate, then rank. Fully deterministic."""
    valid = []
    for cand in candidates:
        text = cand["text"]
        ok, reason = scene_ok(text)
        assert ok, "scene contradiction in %r: %s" % (text, reason)
        assert 1 <= len(text) <= MAX_CHARS, "over limit: %r" % text
        assert text.strip(), "blank line: %r" % text
        assert text == text.strip(), "leading/trailing whitespace: %r" % text
        text.encode("utf-8")
        valid.append(cand)
    return sorted(valid, key=rank_key, reverse=True)


def main():
    ranked = pick(CANDIDATES)
    winner = ranked[0]
    text = winner["text"]
    top_score = total(winner)
    max_score = sum(WEIGHTS.values()) * 5

    print("candidates: %d (all passed scene + gate checks)" % len(CANDIDATES))
    for cand in ranked[:8]:
        print("  %2d/%d  (%3d chars)  %s"
              % (total(cand), max_score, len(cand["text"]), cand["text"]))
    print("winner (%d chars, %d/%d): %s"
          % (len(text), top_score, max_score, text))
    print("why: %s" % winner["why"])

    out_dir = "/output" if os.path.isdir("/output") else "output"
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.txt")
    # Exactly the line, no trailing newline: the gate counts characters.
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.chmod(path, 0o644)
    print("wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
