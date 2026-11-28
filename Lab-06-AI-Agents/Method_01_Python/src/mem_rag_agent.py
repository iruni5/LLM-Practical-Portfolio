import os
import re
import time
import sqlite3
import platform
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

import psutil
import pyautogui
import pygetwindow as gw
import networkx as nx

# Optional clipboard support for instant, error-free Notepad typing
try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    HAS_PYPERCLIP = False

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.tools import tool
from langchain_core.messages import (
    SystemMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
)

# =============================================================================
# 1. CONFIGURATION, MODELS & DATABASES
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "chroma_db"
GRAPH_PATH = DB_PATH / "knowledge_graph.graphml"
SQLITE_PATH = BASE_DIR / "student_memory.db"
COLLECTION = "university_knowledge"

embeddings = OllamaEmbeddings(model="qwen3-embedding:0.6b")
llm = ChatOllama(model="llama3.2:3b", temperature=0)


def init_sqlite_db():
    """Initialize SQLite database for persistent student memory."""
    conn = sqlite3.connect(str(SQLITE_PATH))
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fact TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


init_sqlite_db()


def store_fact_in_sqlite(fact: str) -> bool:
    """Insert a clean fact into SQLite, ignoring duplicates."""
    cleaned = re.sub(r"^[\-\*\•\d\.\s]+", "", str(fact)).strip()
    if not cleaned or len(cleaned) < 3:
        return False

    conn = sqlite3.connect(str(SQLITE_PATH))
    c = conn.cursor()
    try:
        c.execute(
            "INSERT OR IGNORE INTO memories (fact, timestamp) VALUES (?, ?)",
            (cleaned, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        inserted = c.rowcount > 0
    finally:
        conn.close()

    if inserted:
        print(f"[SAVED TO SQLITE] {cleaned}")
    return inserted


def get_all_sqlite_memories() -> list[str]:
    """Return all saved personal facts from SQLite."""
    conn = sqlite3.connect(str(SQLITE_PATH))
    c = conn.cursor()
    c.execute("SELECT fact FROM memories ORDER BY id DESC")
    rows = [r[0] for r in c.fetchall()]
    conn.close()
    return rows


def auto_extract_personal_facts(user_input: str):
    """
    Lightweight rule + LLM extractor that automatically catches personal statements
    (e.g., 'my name is...', 'I study...', 'my partner is...') before tool routing.
    """
    text = user_input.strip()
    lower = text.lower()

    # Do not extract facts from questions
    if lower.startswith(("what ", "who ", "where ", "when ", "why ", "how ", "can ", "open ", "calculate ", "find ", "search ", "create ", "show ")):
        print("\n[MEMORY] Query detected — no new personal fact to save.")
        return

    # Fast deterministic regex patterns for common student facts
    name_match = re.search(r"\b(?:my name is|i am|i'm|call me)\s+([A-Za-z][A-Za-z\s]{1,35})", text, re.IGNORECASE)
    if name_match:
        extracted_name = name_match.group(1).strip().rstrip(".")
        store_fact_in_sqlite(f"The user's name is {extracted_name}.")
        return

    # Check if message contains first-person declarative statements
    if any(token in lower for token in ["my ", "i study", "i like", "i live", "i work", "remember that"]):
        prompt = (
            "Extract a single concise third-person fact about the user from this statement.\n"
            "Example: 'my name is Kavindu' -> 'The user's name is Kavindu.'\n"
            "Example: 'my project partner is Yeran' -> 'The user's project partner is Yeran.'\n"
            "If there is no personal fact about the user, reply ONLY with: NONE\n\n"
            f"Statement: \"{text}\"\nFact:"
        )
        try:
            resp = llm.invoke(prompt).content.strip()
            if "NONE" not in resp.upper() and len(resp) < 150:
                print("\n[NEW MEMORIES DETECTED]")
                for line in resp.splitlines():
                    if line.strip() and "NONE" not in line.upper():
                        store_fact_in_sqlite(line.strip())
                return
        except Exception:
            pass

    print("\n[MEMORY] No new personal information to save.")


# =============================================================================
# 2. DEFINE ALL TOOLS (DESKTOP AUTOMATION + SQLITE MEMORY + HYBRID/KG RAG)
# =============================================================================

@tool
def open_calculator(expression: str) -> str:
    """Open Windows Calculator and enter a mathematical expression (e.g., '25*4')."""
    cleaned_expr = (
        str(expression)
        .replace("×", "*")
        .replace("x", "*")
        .replace("÷", "/")
        .replace("=", "")
        .strip()
    )
    allowed = set("0123456789+-*/(). ")
    if not cleaned_expr or not all(c in allowed for c in cleaned_expr):
        return f"Invalid mathematical expression: '{expression}'"

    print(f"\n[EXECUTING] Opening Windows Calculator for '{cleaned_expr}'...")
    subprocess.Popen("calc.exe")

    windows = []
    for _ in range(10):
        time.sleep(0.5)
        windows = [w for w in gw.getWindowsWithTitle("Calculator") if w.width > 100 and w.height > 100]
        if windows:
            break

    if not windows:
        return "Calculator window not found."

    window = windows[0]
    try:
        if window.isMinimized:
            window.restore()
        window.activate()
        time.sleep(0.5)
        # Click near the upper-middle area of Calculator to guarantee focus
        click_x = window.left + int(window.width * 0.5)
        click_y = window.top + int(window.height * 0.25)
        pyautogui.click(click_x, click_y)
    except Exception:
        pass

    time.sleep(0.3)
    pyautogui.press("esc")
    time.sleep(0.2)
    pyautogui.write(cleaned_expr, interval=0.08)
    pyautogui.press("enter")
    time.sleep(0.5)

    print("[SUCCESS] Expression entered into Calculator.")
    return f"Entered {cleaned_expr} into Windows Calculator."


@tool
def get_date_time() -> str:
    """Retrieves the current system date and time."""
    print("\n[EXECUTING] Retrieving current date and time...")
    now = datetime.now()
    return f"The current date and time is: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@tool
def open_notepad_and_write(text: str) -> str:
    """
    Opens a BRAND-NEW empty document in Windows Notepad and writes the provided text.
    ONLY use this tool when the user explicitly asks to open Notepad or write a note.
    """
    print("\n[EXECUTING] Opening a fresh empty Notepad tab/window...")
    subprocess.Popen(["notepad.exe"])
    time.sleep(2.0)

    windows = gw.getWindowsWithTitle("Notepad") or gw.getWindowsWithTitle("Untitled - Notepad")
    if not windows:
        return "Notepad window not found."

    window = windows[0]
    try:
        window.restore()
        window.activate()
    except Exception:
        pass
    time.sleep(0.6)

    # CRITICAL FIX: Force a brand-new blank tab/file so it never types into an old open file
    pyautogui.hotkey("ctrl", "n")
    time.sleep(0.6)

    # Type cleanly using clipboard paste if pyperclip is available, otherwise pyautogui.write
    if HAS_PYPERCLIP:
        pyperclip.copy(text)
        pyautogui.hotkey("ctrl", "v")
    else:
        pyautogui.write(text, interval=0.04)

    print("[SUCCESS] Text written to a new empty Notepad document.")
    return f"Successfully opened a new blank Notepad document and wrote: '{text}'"


@tool
def search_files(directory: str, search_term: str) -> str:
    """Searches for files by name or extension in a specified directory. Example: directory='D:\\MSC AI', search_term='.pdf'"""
    print(f"\n[EXECUTING] Searching for '{search_term}' in '{directory}'...")
    if not os.path.exists(directory):
        return f"The directory '{directory}' does not exist."

    found_files = []
    try:
        for root, _, files in os.walk(directory):
            for file in files:
                if search_term.lower() in file.lower():
                    found_files.append(os.path.join(root, file))

        if found_files:
            result = "\n".join(found_files[:10])
            if len(found_files) > 10:
                result += f"\n...and {len(found_files) - 10} more files."
            return f"Found matching files:\n{result}"
        return f"No files matching '{search_term}' were found in '{directory}'."
    except Exception as e:
        return f"Error searching for files: {str(e)}"


@tool
def create_text_file(filepath: str, content: str) -> str:
    """Creates a text file on disk with user-provided content. Example filepath: 'D:\\MSC AI\\test.txt'"""
    print(f"\n[EXECUTING] Creating file at '{filepath}'...")
    try:
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(content)
        print("[SUCCESS] File created.")
        return f"Successfully created file '{filepath}' with the provided content."
    except Exception as e:
        return f"Failed to create file. Error: {str(e)}"


@tool
def get_system_info() -> str:
    """Retrieves operating system, processor, and RAM memory specifications."""
    print("\n[EXECUTING] Retrieving system specifications...")
    try:
        total_ram = round(psutil.virtual_memory().total / (1024.0 ** 3), 2)
        available_ram = round(psutil.virtual_memory().available / (1024.0 ** 3), 2)
        info = (
            f"OS: {platform.system()} {platform.release()} ({platform.architecture()[0]})\n"
            f"Processor: {platform.processor()}\n"
            f"Total Memory: {total_ram} GB\n"
            f"Available Memory: {available_ram} GB"
        )
        return f"System Information:\n{info}"
    except Exception as e:
        return f"Failed to retrieve system info: {str(e)}"


@tool
def open_file_or_app(target: str) -> str:
    """Opens a specific file, folder, or Windows app (e.g., 'outlookcal:' for Calendar)."""
    print(f"\n[EXECUTING] Attempting to open '{target}'...")
    try:
        os.startfile(target)
        print("[SUCCESS] Opened successfully.")
        return f"Successfully opened {target}"
    except Exception as e:
        return f"Failed to open '{target}'. Error: {str(e)}"


@tool
def save_student_memory(fact: str) -> str:
    """Saves personal facts about the user (e.g. name, major, friends, preferences) to SQLite long-term memory."""
    store_fact_in_sqlite(fact)
    return f"Saved to long-term memory: {fact}"


@tool
def search_student_memory(query: str) -> str:
    """Searches long-term SQLite memory to answer questions about the user (e.g., 'What is my name?', 'Who is my partner?')."""
    print(f"\n[EXECUTING] Searching SQLite student memory for: '{query}'...")
    all_memories = get_all_sqlite_memories()
    if not all_memories:
        return "No personal memories stored yet."

    stop_words = {"what", "who", "where", "when", "is", "are", "my", "the", "tell", "me", "about", "do", "you", "know"}
    keywords = [
        w.lower()
        for w in re.findall(r"\w+", query)
        if w.lower() not in stop_words and len(w) > 2
    ]

    matched = [
        mem for mem in all_memories
        if any(k in mem.lower() for k in keywords)
    ]

    # Fallback: if no specific keyword matched, return all saved personal facts so the agent never misses a name
    final_list = matched if matched else all_memories[:10]
    return "Stored User Memories:\n" + "\n".join(f"- {m}" for m in final_list)


@tool
def search_university_knowledge(query: str) -> str:
    """Retrieves information from uploaded PDFs (university handbooks, novels, course modules) via ChromaDB and Knowledge Graph."""
    print(f"\n[EXECUTING] Searching ChromaDB & Knowledge Graph for: '{query}'...")
    if not DB_PATH.exists():
        return "Error: ChromaDB folder not found. Please ingest a PDF first."

    output_blocks = []

    # 1. Check NetworkX Knowledge Graph if available
    if GRAPH_PATH.exists():
        try:
            G = nx.read_graphml(str(GRAPH_PATH))
            q_words = {w.lower() for w in re.findall(r"\w+", query) if len(w) > 3}
            kg_facts = []
            for u, v, data in G.edges(data=True):
                if any(w in str(u).lower() or w in str(v).lower() for w in q_words):
                    label = data.get("label", "RELATED_TO")
                    kg_facts.append(f"[{u}] --({label})--> [{v}]")
            if kg_facts:
                output_blocks.append("Knowledge Graph Facts:\n" + "\n".join(kg_facts[:5]))
        except Exception:
            pass

    # 2. Query ChromaDB Vector Store
    try:
        vector_store = Chroma(
            collection_name=COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(DB_PATH),
        )
        results = vector_store.similarity_search(query, k=3)
        for doc in results:
            fname = doc.metadata.get("filename", doc.metadata.get("source", "Document"))
            page = doc.metadata.get("page", 0) + 1
            snippet = doc.page_content.strip()[:450]
            output_blocks.append(f"Source: {fname}, Page: {page}\n{snippet}...")
    except Exception as e:
        return f"Error querying ChromaDB: {str(e)}"

    if output_blocks:
        return "\n\n---\n\n".join(output_blocks)

    return "No relevant information found in the university knowledge base."


# =============================================================================
# 3. REGISTER TOOLS & SAFE ARGUMENT EXECUTION ENGINE
# =============================================================================
tools = [
    open_calculator,
    get_date_time,
    open_notepad_and_write,
    search_files,
    create_text_file,
    get_system_info,
    open_file_or_app,
    save_student_memory,
    search_student_memory,
    search_university_knowledge,
]
tool_map = {t.name: t for t in tools}
agent = llm.bind_tools(tools)

try:
    from langchain_google_community import CalendarToolkit, GmailToolkit  # pyright: ignore[reportMissingImports]
except ImportError:
    CalendarToolkit = None
    GmailToolkit = None

CREDENTIALS_FILE = BASE_DIR / "credentials.json"
TOKEN_FILE = BASE_DIR / "token.json"

extra_google_tools = []
if CREDENTIALS_FILE.exists():
    try:
        if CalendarToolkit is None or GmailToolkit is None:
            raise ImportError("langchain-google-community is not installed")
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from langchain_google_community import CalendarToolkit, GmailToolkit

        scopes = [
            "https://www.googleapis.com/auth/calendar",
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.compose",
        ]

        creds = None
        if TOKEN_FILE.exists():
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), scopes)
                creds = flow.run_local_server(port=0)
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")

        cal_service = build("calendar", "v3", credentials=creds)
        gmail_service = build("gmail", "v1", credentials=creds)

        cal_tools = CalendarToolkit(api_resource=cal_service).get_tools()
        gmail_tools = GmailToolkit(api_resource=gmail_service).get_tools()

        all_google_tools = cal_tools + gmail_tools
        print("[ALL GOOGLE TOOLS]:", [getattr(t, "name", "") for t in all_google_tools])

        wanted_names = {
            "get_current_events",
            "create_calendar_event",
            "search_gmail",
            "create_gmail_draft",
        }
        extra_google_tools = [
            t for t in all_google_tools if getattr(t, "name", "") in wanted_names
        ]

        if not extra_google_tools and all_google_tools:
            extra_google_tools = cal_tools[:2] + gmail_tools[:2]

        print(
            f"[GOOGLE] Loaded {len(extra_google_tools)} Calendar/Gmail tools:",
            [getattr(t, "name", "") for t in extra_google_tools],
        )
    except Exception as e:
        print(f"Failed to initialize Google toolkits: {e}")

tools = [
    open_calculator,
    get_date_time,
    open_notepad_and_write,
    search_files,
    create_text_file,
    get_system_info,
    open_file_or_app,
    save_student_memory,
    search_student_memory,
    search_university_knowledge,
    *extra_google_tools,
]
tool_map = {t.name: t for t in tools}
agent = llm.bind_tools(tools)


def extract_first_string_arg(args_dict: dict) -> str:
    """Extracts a string value even if the 3B LLM nests dictionaries like {'query': {'name': 'Kavindu'}}."""
    for val in args_dict.values():
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            nested = ", ".join(f"{k}: {v}" for k, v in val.items())
            if nested:
                return nested
    return str(args_dict)


def safe_execute_tool(tool_name: str, raw_args: dict, user_question: str) -> str:
    """
    Executes the selected tool with intent guardrails so 'open_notepad_and_write'
    is NEVER triggered when the user is just stating or asking their name.
    """
    q_low = user_question.lower()

    # GUARDRAIL: Block Notepad unless the user explicitly asked for Notepad or a note
    if tool_name == "open_notepad_and_write":
        notepad_keywords = ["notepad", "note", "write down", "type in", "draft", "editor"]
        if not any(k in q_low for k in notepad_keywords):
            print("[GUARDRAIL] Blocked accidental Notepad call -> Rerouting to SQLite Memory.")
            if q_low.startswith(("what", "who", "where", "when", "do you know", "tell me")):
                return search_student_memory.invoke({"query": user_question})
            else:
                fact_text = extract_first_string_arg(raw_args) or user_question
                return save_student_memory.invoke({"fact": fact_text})

    selected_tool = tool_map.get(tool_name)
    if not selected_tool:
        return f"Error: Tool '{tool_name}' not found."

    try:
        return selected_tool.invoke(raw_args)
    except Exception as e:
        # Automatic recovery if llama3.2:3b passes wrong parameter names (Pydantic error)
        fallback_str = extract_first_string_arg(raw_args) or user_question
        if tool_name == "save_student_memory":
            return save_student_memory.invoke({"fact": fallback_str})
        if tool_name == "search_student_memory":
            return search_student_memory.invoke({"query": fallback_str})
        if tool_name == "search_university_knowledge":
            return search_university_knowledge.invoke({"query": fallback_str})
        if tool_name == "open_calculator":
            return open_calculator.invoke({"expression": fallback_str})
        return f"Error executing {tool_name}: {str(e)}"


# =============================================================================
# 4. AGENT EXECUTION LOOP (CLEAN SHORT-TERM MEMORY)
# =============================================================================
SYSTEM_PROMPT = """You are an Intelligent Student & Desktop AI Agent.

STRICT TOOL SELECTION RULES:
1. 'open_calculator': ONLY when the user asks to calculate a math expression.
2. 'get_date_time': ONLY when the user asks for the current date or time.
3. 'open_notepad_and_write': ONLY when the user explicitly says "open Notepad" or "write in Notepad". NEVER use Notepad to remember personal facts!
4. 'search_files': ONLY when the user asks to find files in a directory path.
5. 'create_text_file': ONLY when the user explicitly asks to create/save a .txt file at a path.
6. 'get_system_info': ONLY when the user asks for PC specs, OS, processor, or RAM.
7. 'open_file_or_app': ONLY when the user asks to launch a file or app (like 'outlookcal:').
8. 'save_student_memory': When the user tells you personal information about themselves (e.g., "My name is Kavindu", "My partner is Yeran").
9. 'search_student_memory': When the user asks a personal question about themselves (e.g., "What is my name?", "Who is my partner?").
10. 'search_university_knowledge': When the user asks about university modules, course codes, handbook rules, or uploaded PDFs.
"""


def run_agent(question: str, chat_history: list) -> tuple[str, list]:
    # 1. Automatically extract personal facts if the user is introducing themselves
    auto_extract_personal_facts(question)

    # 2. Inject current SQLite profile summary so the agent is always grounded
    saved_facts = get_all_sqlite_memories()
    memory_context = (
        "\nKnown facts about the user from SQLite:\n" + "\n".join(f"- {f}" for f in saved_facts[:8])
        if saved_facts
        else "\nKnown facts about the user from SQLite: None yet."
    )

    # 3. Build working messages for this turn
    working_messages = [SystemMessage(content=SYSTEM_PROMPT + memory_context)]
    working_messages.extend(chat_history)
    working_messages.append(HumanMessage(content=question))

    # Allow up to 3 tool iterations per turn to prevent infinite loops
    for _ in range(3):
        response = agent.invoke(working_messages)
        working_messages.append(response)

        if response.tool_calls:
            for call in response.tool_calls:
                t_name = call["name"]
                t_args = call["args"]
                print(f"\n[TOOL SELECTED] {t_name}")
                print(f"[TOOL ARGUMENTS] {t_args}")

                result = safe_execute_tool(t_name, t_args, question)
                preview = str(result)[:250] + ("..." if len(str(result)) > 250 else "")
                print(f"[TOOL RESULT] {preview}")

                working_messages.append(
                    ToolMessage(content=str(result), tool_call_id=call["id"])
                )
        else:
            final_answer = response.content
            break
    else:
        # Generate final response if max tool calls reached
        final_answer = llm.invoke(working_messages).content

    # 4. Append ONLY clean Human/AI text messages to short-term history
    #    (Stripping raw tool_calls stops 3B models from repeating old tools on the next turn!)
    chat_history.append(HumanMessage(content=question))
    chat_history.append(AIMessage(content=final_answer))

    # Keep last 6 turns (12 messages)
    if len(chat_history) > 12:
        chat_history = chat_history[-12:]

    print("\n[SHORT-TERM MEMORY] Conversation updated.")
    return final_answer, chat_history


# =============================================================================
# 5. INTERACTIVE TERMINAL INTERFACE
# =============================================================================
if __name__ == "__main__":
    print("\n===================================================")
    print(" 🌟 ULTIMATE MASTER AI AGENT (BULLETPROOF EDITION)")
    print(" Desktop Automation + SQLite Memory + Hybrid/KG RAG")
    print("===================================================")

    session_history = []

    while True:
        try:
            user_q = input("\nYou: ").strip()
            if not user_q:
                continue
            if user_q.lower() in ["exit", "quit"]:
                print("Exiting agent.")
                break

            answer, session_history = run_agent(user_q, session_history)
            print(f"\nAgent: {answer}")

        except KeyboardInterrupt:
            print("\nExiting agent.")
            break
        except Exception as e:
            print(f"\n[SYSTEM ERROR] {e}")