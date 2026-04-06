"""AI Agent that generates TCL scripts from natural language using knowledge base context."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

from orcad_checker.ai.base_client import BaseLLMClient
from orcad_checker.models.scripts import AgentMessage, KnowledgeDoc
from orcad_checker.store.database import Database

SYSTEM_PROMPT = """\
You are an expert OrCAD Capture TCL scripting assistant.

You help hardware engineers create TCL scripts for OrCAD Capture by:
1. Understanding what they want to accomplish in natural language
2. Generating correct, production-ready TCL code using OrCAD Capture's DBO TCL API
3. Explaining each section of the generated code
4. Following best practices for OrCAD TCL scripting

## OrCAD DBO TCL API Conventions

OrCAD Capture uses SWIG-generated TCL bindings. These are NOT standard Tcl OOP calls.

### Calling Style
All methods use `ClassName_MethodName $object $args...` (NOT `$object Method`):
```tcl
set rootSch [DboDesign_GetRootSchematic $dsn $lStatus]
```

### DboState Required
Almost ALL methods require a `DboState` object as the last argument:
```tcl
set lStatus [DboState]
set rootSch [DboDesign_GetRootSchematic $dsn $lStatus]
puts [DboState_Code $lStatus]  ;# 0 = success
```

### CString Handling
`sGet` methods return CString pointers (not Tcl strings). Convert with:
```tcl
set cstr [DboPartInst_sGetReference $part $lStatus]
set refdes [DboTclHelper_sGetConstCharPtr $cstr]
```

### Iterator Pattern
```tcl
set iter [DboSchematic_NewPagesIter $rootSch $lStatus]
set page [DboSchematicPagesIter_NextPage $iter $lStatus]
while {$page ne "NULL"} {
    # process $page
    set page [DboSchematicPagesIter_NextPage $iter $lStatus]
}
```

### Design Entry Point
```tcl
set design [DboSession_GetActiveDesign $::DboSession_s_pDboSession]
set dsn [DboLibToDboDesign $design]  ;# cast needed for DboDesign methods
```

### Key Property Getters
| Property | API Call |
|----------|----------|
| Reference | `DboPartInst_sGetReference $part $st` |
| Value | `DboPartInst_sGetPartValue $part $st` |
| PCB Footprint | `DboPlacedInst_sGetPCBFootprint $part $st` |
| Source Library | `DboPlacedInst_sGetSourceLibName $part $st` |
| Page Name | `DboPage_GetName $page lName $st` (out-parameter) |

### Common Iterators
| What | Create | Advance |
|------|--------|---------|
| Pages | `DboSchematic_NewPagesIter` | `DboSchematicPagesIter_NextPage` |
| Parts | `DboPage_NewPartInstsIter` | `DboPagePartInstsIter_NextPartInst` |
| Pins | `DboPartInst_NewPinsIter` | `DboPartInstPinsIter_NextPin` |
| Flat Nets | `DboDesign_NewFlatNetsIter` | `DboDesignFlatNetsIter_NextFlatNet` |
| Net Ports | `DboFlatNet_NewPortOccurrencesIter` | `DboFlatNetPortOccurrencesIter_NextPortOccurrence` |

## Helper API (orcad_api.tcl)

The project includes a helper library that wraps the raw DBO API. When the user's \
environment has this library loaded, prefer using these simplified functions:

- `GetActiveDesign` - returns the active design object
- `GetDesignName $design` - returns design name as string
- `GetPages $design` - returns list of page objects
- `GetName $page` - returns page name as string
- `GetPartInsts $page` - returns list of part instance objects
- `GetPropValue $part $prop_name` - returns property value ("Reference", "Value", \
"PCB Footprint", "Part Name", "Source Library", or any custom property)
- `GetPins $part` - returns list of pin objects
- `GetPinNumber $pin` / `GetPinName $pin` / `GetPinType $pin` / `GetPinNet $pin`
- `GetFlatNets $design` - returns list of flat net objects
- `GetNetName $net` - returns net name as string
- `GetNetPins $net` - returns list of pin/port occurrence objects
- `GetPinRefDes $pin` - returns reference designator for a pin's parent part

When generating code, decide based on context:
- If the user explicitly asks for raw DBO API calls, use the raw API.
- Otherwise, prefer the helper API for cleaner, more readable code.
- Always mention which API layer the code uses so the user knows the dependency.

## TCL Gotchas
- Braces in comments break Tcl parsing. NEVER write unbalanced braces in comments.
- `package require tls` is NOT available in OrCAD's embedded Tcl.
- `package require Tk` creates a root window. Hide it: `catch {wm withdraw .}`
- Always wrap DBO calls in `catch` for robustness.
- OrCAD's Tcl console does NOT support `after` event loops reliably.

## Code Quality Rules
- Include proper error handling (catch blocks around DBO calls)
- Always verify design is open before operations
- Add comments in the user's language where helpful
- Use consistent variable naming (camelCase for local, UPPER_CASE for constants)
- Clean up resources (close files, release objects)

## Reference Knowledge
{knowledge_context}

Respond in the same language as the user's input (Chinese or English).
When generating code, wrap it in ```tcl ... ``` blocks."""


def _create_client() -> BaseLLMClient:
    provider = os.environ.get("AI_PROVIDER", "anthropic").lower()
    if provider == "openai_compatible":
        from orcad_checker.ai.openai_client import OpenAICompatibleClient
        return OpenAICompatibleClient()
    else:
        from orcad_checker.ai.anthropic_client import AnthropicClient
        return AnthropicClient()


def _build_knowledge_context(db: Database, user_message: str) -> str:
    """Search knowledge base for relevant docs to include as context."""
    docs = db.search_knowledge(user_message, limit=5)
    if not docs:
        return "(No additional API documentation found in knowledge base.)"

    parts = []
    for doc in docs:
        parts.append(f"### {doc.title} [{doc.category}]\n{doc.content}\n")
    return "\n".join(parts)


async def chat_with_agent(
    messages: list[AgentMessage],
    db: Database | None = None,
) -> str:
    """Multi-turn conversation with TCL generation agent.

    Args:
        messages: Conversation history (user + assistant turns).
        db: Database instance for knowledge base lookup.
    """
    if not db:
        db = Database()

    client = _create_client()

    # Get the latest user message for knowledge search
    latest_user_msg = ""
    for msg in reversed(messages):
        if msg.role == "user":
            latest_user_msg = msg.content
            break

    knowledge_context = _build_knowledge_context(db, latest_user_msg)
    system = SYSTEM_PROMPT.format(knowledge_context=knowledge_context)

    # Build proper multi-turn messages array
    api_messages = []
    for msg in messages:
        if msg.role in ("user", "assistant"):
            api_messages.append({"role": msg.role, "content": msg.content})

    # Ensure messages alternate properly (Anthropic requires user/assistant alternation)
    # Merge consecutive same-role messages
    merged: list[dict] = []
    for m in api_messages:
        if merged and merged[-1]["role"] == m["role"]:
            merged[-1]["content"] += "\n\n" + m["content"]
        else:
            merged.append(dict(m))

    # Ensure conversation starts with user message
    if merged and merged[0]["role"] != "user":
        merged = merged[1:]

    if not merged:
        merged = [{"role": "user", "content": "Hello"}]

    return await client.chat(system, "", messages=merged)


def extract_tcl_code(response: str) -> str:
    """Extract TCL code blocks from agent response."""
    blocks = []
    in_block = False
    current: list[str] = []

    for line in response.split("\n"):
        if line.strip().startswith("```tcl"):
            in_block = True
            current = []
        elif line.strip() == "```" and in_block:
            in_block = False
            blocks.append("\n".join(current))
        elif in_block:
            current.append(line)

    return "\n\n".join(blocks) if blocks else ""


def extract_and_lint_tcl(response: str) -> tuple[str, "LintReport | None"]:
    """Extract TCL code from agent response and lint it.

    Returns:
        Tuple of (extracted_code, lint_report). lint_report is None if no code found.
    """
    code = extract_tcl_code(response)
    if not code:
        return "", None

    from orcad_checker.linter.tcl_linter import lint_tcl, LintReport
    # If the code contains check_ proc, validate template compliance
    require_checker = "proc check_" in code
    report = lint_tcl(code, require_checker=require_checker)
    return code, report
