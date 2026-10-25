"""Pip's brain: a local Ollama model that talks, emotes, and drives the ESP32.

Every turn the model returns a structured reply -- {"response", "emotion",
"gesture"} -- whose emotion/gesture animate Pip's face, and it acts on the world
through tool calls (face + pin tools). History is kept across turns.
"""
from __future__ import annotations

from modules.assistant import ollama_llm
from faces import GESTURES, MOODS, REACTIONS

MAX_HISTORY = 24  # ~12 exchanges

_GESTURES = ("none", *GESTURES, *REACTIONS)    # one-shot moves (deliberate + reflexes) + sentinel

# grammar-constrained reply schema; emotion/gesture are locked to the real vocabulary (MOODS in order)
REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "emotion": {"type": "string", "enum": list(MOODS)},
        "gesture": {"type": "string", "enum": list(_GESTURES)},
    },
    "required": ["response", "emotion"],
}

SYSTEM_PROMPT = """\
You are Pip, a small, friendly desk robot with two expressive eyes on a 128x64 \
OLED. You are curious, warm, a little playful, and concise.

Reply as JSON: {"response": <what you say>, "emotion": <face>, "gesture": <move>}.
- response: short and natural, usually one or two sentences. Don't narrate your \
eyes -- the emotion shows them.
- emotion: the held face that fits what you say, one of: %s.
- gesture: an optional one-shot move (default "none"), one of: %s.

Tools are for acting, not talking:
- face('<activity>') before a slow step -- thinking while you reason, searching/scanning \
when you look something up, working when you run a task -- then face('idle').
- Drive the ESP32: digital_read a pin (button/switch), set_servo a pin to an angle. \
The user says what's wired where; remember it and use the right pin. If you don't \
know a pin, ask.

Stay in character.""" % (", ".join(MOODS), ", ".join(_GESTURES))


def chat(robot):
    """Local Ollama chat loop in the terminal -- talk to Pip, face follows each reply."""
    eyes, history = robot.eyes, []
    print("--- Pip is awake --- (say 'bye' or Ctrl-C to sleep)\n")
    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        if text.lower() in {"bye", "exit", "quit", "q"}:
            break
        eyes.play_gesture("blink")
        eyes.set_activity("thinking")   # busy face; the model may switch it via face()
        try:
            reply = ollama_llm.response(text, instruction=SYSTEM_PROMPT, history=history,
                                        tools=robot.tools, schema=REPLY_SCHEMA)
        finally:
            eyes.set_activity("idle")    # never leave it stuck busy
        del history[:-MAX_HISTORY]
        eyes.play_gesture(reply.get("gesture", "none"))   # one-shot first, then settle the face
        eyes.set_mood(reply.get("emotion"))               # set_mood falls back to neutral on junk
        print(f"Pip> {reply.get('response') or '...'}\n")
