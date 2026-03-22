"""
dept_ai.py — Gemini AI for department bots.
Each department has its own AI conversation history.
"""

import os
import google.generativeai as genai
from shared.db import load, save

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Federal Polytechnic")


def _data_file(dept_key: str) -> str:
    return f"dept_data_{dept_key}.json"


async def ask_gemini(user_id: int, dept_key: str, dept_name: str, question: str) -> str:
    """Ask Gemini AI with department-specific context and per-user history."""

    system = (
        f"You are an academic assistant for the {dept_name} department at {SCHOOL_NAME}.\n"
        f"Help students with course concepts, assignments, past questions, and study tips.\n"
        f"Focus on topics relevant to {dept_name}.\n"
        f"Be clear, friendly, and use simple English.\n"
        f"Use bullet points and numbered lists when explaining steps.\n"
        f"Where possible, relate examples to the Nigerian academic context.\n"
        f"If a question is unrelated to academics, politely redirect."
    )

    DEFAULT = {"members": {}, "admins": [], "banned": [], "files": [],
               "announcements": [], "pinned": "", "pending": [],
               "approved": [], "ai_history": {}, "stats": {}}

    try:
        d       = load(_data_file(dept_key), DEFAULT)
        history = d.get("ai_history", {}).get(str(user_id), [])

        model   = genai.GenerativeModel("gemini-1.5-flash", system_instruction=system)
        chat    = model.start_chat(history=[
            {"role": m["role"], "parts": [m["content"]]}
            for m in history[-10:]
        ])

        resp   = await chat.send_message_async(question)
        answer = resp.text

        # Save history
        history.append({"role": "user",  "content": question})
        history.append({"role": "model", "content": answer})
        history = history[-20:]

        if "ai_history" not in d:
            d["ai_history"] = {}
        d["ai_history"][str(user_id)] = history

        if "stats" not in d:
            d["stats"] = {}
        d["stats"]["questions"] = d["stats"].get("questions", 0) + 1
        save(_data_file(dept_key), d)

        return answer

    except Exception as e:
        err = str(e)
        if "API_KEY" in err or "api key" in err.lower():
            return "⚠️ AI is not configured yet. Ask your admin to add the Gemini API key."
        if "quota" in err.lower():
            return "⚠️ AI is temporarily busy. Please try again in a minute."
        return f"⚠️ Something went wrong. Please try again.\n\n`{err[:80]}`"


def clear_history(user_id: int, dept_key: str) -> None:
    DEFAULT = {"ai_history": {}}
    d = load(_data_file(dept_key), DEFAULT)
    d.get("ai_history", {}).pop(str(user_id), None)
    save(_data_file(dept_key), d)
