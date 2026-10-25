"""Local Ollama chat: a native tool-call loop, then a structured final reply.

Two phases, because Ollama's grammar-constrained `format=` forces JSON tokens
from the first one and so suppresses tool calls -- they can't share a call:
  1. act   -- loop with `tools`, running each tool call until the model stops.
  2. speak -- one `format=schema` call coerces the answer into JSON, e.g.
              {"response": "hi", "emotion": "happy"}.
With no `schema` it behaves like a plain chat and returns the reply text.
"""
from __future__ import annotations

import json
import logging
import os
from functools import cache

log = logging.getLogger("robot.llm")

# env defaults; any response() call can override them.
MODEL = os.getenv("ROBOT_MODEL", "qwen3.5:4b")
OPTS = {"num_ctx": int(os.getenv("ROBOT_NUM_CTX", "4096")), "temperature": 0.7}


def _default_think():
    """ROBOT_THINK: true (default -- Qwen answers better with it) / false, or a level the model lists
    in `ollama show` (gpt-oss: low/medium/high). qwen3.5 only knows true/false, so 'low' = true there.
    Cost, measured on qwen3.5:4b in chat: ~5 s/turn thinking vs ~1.3 s/turn with false."""
    v = os.getenv("ROBOT_THINK", "true").strip().lower()
    bools = {"1": True, "true": True, "yes": True, "on": True, "0": False, "false": False, "no": False, "off": False}
    return bools.get(v, v)


THINK = _default_think()


@cache
def _get_client():
    from ollama import Client
    return Client(timeout=60.0)                  # reads OLLAMA_HOST itself


def response(
    prompt: str = "",
    *,
    instruction: str = "",
    messages: list[dict] = None,
    images: list[bytes] = None,
    schema: dict = None,
    model: str = None,
    tools: list = None,
    options: dict = None,
    think=None,
    keep_alive: str = "30m",
    max_steps: int = 10,
    history: list = None,
    **_,
):
    """Run the tool loop, then return a dict matching `schema` (or reply text).

    Pass a ready `messages` list, or let it build [instruction] + history + prompt.
    """
    client = _get_client()
    msgs = list(messages) if messages else _build(instruction, history, prompt, images)
    fns = {t.__name__: t for t in tools} if tools else {}
    shared = dict(model=model or MODEL, options=options or OPTS,
                  think=THINK if think is None else think, keep_alive=keep_alive)

    # phase 1 -- let the model act with tools until it stops calling them
    content = ""
    for _step in range(max_steps):
        try:
            msg = client.chat(messages=msgs, tools=tools, **shared).message
        except Exception as e:
            return _shape(f"Error: {e}", schema)
        if not msg.tool_calls:
            content = msg.content or ""
            break
        msgs.append(msg)  # assistant turn carrying the tool_calls
        for tc in msg.tool_calls:
            msgs.append({"role": "tool", "tool_name": tc.function.name,
                         "content": str(_call(fns, tc))})

    # phase 2 -- coerce the final answer into the schema (grammar-constrained)
    reply = _structured(client, msgs, schema, content, shared) if schema else content

    if history is not None:
        text = reply.get("response", "") if isinstance(reply, dict) else reply
        history += [{"role": "user", "content": prompt},
                    {"role": "assistant", "content": text}]
    return reply


def _build(instruction, history, prompt, images):
    """[system] + history + the user turn (with optional images)."""
    msgs = []
    if instruction:
        msgs.append({"role": "system", "content": instruction})
    if history:
        msgs += history
    user = {"role": "user", "content": prompt}
    if images:
        user["images"] = images
    msgs.append(user)
    return msgs


def _structured(client, msgs, schema, fallback, shared):
    """Force the final answer to match `schema`, then parse it to a dict."""
    # a Pydantic model class carries its own JSON schema; a dict is used as-is
    fmt = schema.model_json_schema() if hasattr(schema, "model_json_schema") else schema
    cool = {**shared, "options": {**shared["options"], "temperature": 0.3}}
    try:
        out = client.chat(messages=msgs, format=fmt, **cool).message
        return json.loads(out.content or "{}")
    except Exception as e:
        log.warning("structured reply failed: %s", e)
        return _shape(fallback or "...", schema)


def _shape(text, schema):
    """A bare reply in the right shape: a dict when a schema is in play, else text."""
    return {"response": text} if schema else text


def _call(fns, tc):
    fn = fns.get(tc.function.name)
    if not fn:
        return f"unknown tool: {tc.function.name}"
    args = tc.function.arguments or {}           # ollama hands back a parsed Mapping
    log.info("tool %s(%s)", tc.function.name, args)
    try:
        return fn(**args)
    except Exception as e:
        return f"error: {e}"


# MARK: Test
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # emoji-safe on Windows
    from pydantic import BaseModel
    class Nums(BaseModel):
        n: list[int]

    def add(a: int, b: int) -> int:
        """Add two numbers.

        Args:
          a: first number
          b: second number
        """                                     # Google-style Args -> ollama's tool param descriptions
        return a + b

    print(f"Ollama | {MODEL}")
    print("\n--- Basic ---")
    print(response("Say hi briefly"))
    print("\n--- Schema ---")
    print(response("Numbers 1-3", schema=Nums))
    print("\n--- Tools ---")
    print(response("What is 2+3?", tools=[add]))
