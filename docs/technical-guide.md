# OrCAD Checker -- Developer Technical Guide

## Development Setup

### Prerequisites

- Python 3.10+
- Node.js 18+ (for frontend development)
- Git

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd orcad-checker

# Install Python package in development mode
pip install -e ".[dev]"

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### Running Locally

**Backend only (API server)**:
```bash
orcad-check serve --port 8000
```

**Frontend dev server** (with API proxy to backend):
```bash
# Terminal 1: Start backend
orcad-check serve --port 8000

# Terminal 2: Start frontend dev server (port 8080, proxies /api/* to :8000)
cd frontend && npm run serve
```

**Run checks from CLI**:
```bash
orcad-check run tests/fixtures/sample_design.json
orcad-check run tests/fixtures/sample_design.json --rules rules/default_rules.yaml --json
orcad-check list
```

### Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_PROVIDER` | `anthropic` | LLM provider: `anthropic` or `openai_compatible` |
| `ANTHROPIC_API_KEY` | _(required if anthropic)_ | Anthropic API key |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Anthropic model name |
| `OPENAI_BASE_URL` | _(required if openai_compatible)_ | OpenAI-compatible API base URL |
| `OPENAI_API_KEY` | | API key for OpenAI-compatible provider |
| `OPENAI_MODEL` | `default` | Model name for OpenAI-compatible provider |

---

## How to Add a New Checker

### Step 1: Create the Checker Module

Create `src/orcad_checker/checkers/my_check.py`:

```python
from orcad_checker.checkers.base import BaseChecker
from orcad_checker.engine.registry import register_checker
from orcad_checker.models.design import Design
from orcad_checker.models.results import CheckResult, Finding, Severity, Status


@register_checker("my_check")
class MyChecker(BaseChecker):
    name = "My Custom Check"
    description = "Describes what this check validates"
    default_severity = "WARNING"

    def check(self, design: Design) -> list[CheckResult]:
        # Access checker-specific config from YAML params
        threshold = self.config.get("threshold", 10)

        findings = []
        for comp in design.components:
            # Your validation logic here
            if some_condition(comp):
                findings.append(Finding(
                    message=f"Issue found on {comp.refdes}: ...",
                    refdes=comp.refdes,
                    page=comp.page,
                ))

        if not findings:
            return [CheckResult(
                rule_id="my_check",
                rule_name=self.name,
                severity=Severity.WARNING,
                status=Status.PASS,
            )]

        return [CheckResult(
            rule_id="my_check",
            rule_name=self.name,
            severity=Severity.WARNING,
            status=Status.FAIL,
            findings=findings,
        )]
```

Key points:
- The `@register_checker("my_check")` decorator registers the class in the global registry
- The `check()` method receives a `Design` model and returns a list of `CheckResult`
- Always return a PASS result when no findings, so the check appears in the report
- Access parameters from `self.config` (populated from YAML `params`)

### Step 2: Add a Rule Entry

Add to `rules/default_rules.yaml`:

```yaml
  - id: my_check
    enabled: true
    severity: warning
    params:
      threshold: 10
```

### Step 3: Write Tests

Create `tests/test_checkers/test_my_check.py`:

```python
from orcad_checker.checkers.my_check import MyChecker
from orcad_checker.models.results import Status


def test_my_check_pass(sample_design):
    checker = MyChecker()
    results = checker.check(sample_design)
    assert len(results) == 1
    assert results[0].status == Status.PASS


def test_my_check_with_params(sample_design):
    checker = MyChecker(config={"threshold": 5})
    results = checker.check(sample_design)
    # Assert expected behavior
```

### Step 4 (Optional): Add TCL Counterpart

Create `tcl/checkers/my_check.tcl`:

```tcl
proc check_my_check {design} {
    set findings [list]
    foreach page [GetPages $design] {
        foreach part [GetPartInsts $page] {
            # Your validation logic using OrCAD TCL API
            set refdes [GetPropValue $part "Reference"]
            # ...
            if {$some_condition} {
                lappend findings [finding "Issue on $refdes: ..." $refdes]
            }
        }
    }

    if {[llength $findings] == 0} {
        check_result "my_check" $::CHECK_WARNING "PASS" [list]
    } else {
        check_result "my_check" $::CHECK_WARNING "FAIL" $findings
    }
}
```

Register it in `tcl/checkers/load_all.tcl`:

```tcl
source [file join $_checker_dir my_check.tcl]
```

No manual registration is needed on the Python side -- `discover_checkers()` auto-imports all modules in the `checkers/` package (except `base.py`).

---

## How to Add a New API Endpoint

### Step 1: Create or Edit a Route Module

To add a new route to an existing module, edit the file in `src/orcad_checker/web/routes/`. To create a new module:

```python
# src/orcad_checker/web/routes/my_feature.py
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/my-feature", tags=["my-feature"])


class MyRequest(BaseModel):
    name: str
    value: int = 0


class MyResponse(BaseModel):
    result: str


@router.get("")
def list_items():
    return []


@router.post("", response_model=MyResponse)
def create_item(req: MyRequest):
    return MyResponse(result=f"Created {req.name}")
```

### Step 2: Register the Router

Add to `src/orcad_checker/web/app.py`:

```python
from orcad_checker.web.routes import my_feature

app.include_router(my_feature.router)
```

### Step 3: Add Frontend API Client

Add to `frontend/src/api/scripts.js` (or create a new API file):

```javascript
export function listMyItems() {
  return api.get('/my-feature');
}

export function createMyItem(data) {
  return api.post('/my-feature', data);
}
```

---

## Testing

### Test Framework

Tests use `pytest` with `pytest-asyncio` for async tests. Test fixtures are in `tests/fixtures/`.

### Running Tests

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_checkers/test_duplicate_refdes.py

# Run a specific test by name
pytest tests/test_engine.py -k "test_run_checks"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=orcad_checker
```

### Test Structure

```
tests/
    conftest.py               # Shared fixtures
    fixtures/
        sample_design.json    # Test design data
    test_checkers/            # Per-checker tests
        test_duplicate_refdes.py
    test_engine.py            # Engine integration tests
    test_parser.py            # Parser tests
    test_store.py             # Database tests
    test_api.py               # API endpoint tests
    test_tcl_results.py       # TCL results upload tests
```

### Key Fixture

The `sample_design` fixture (from `conftest.py`) parses `tests/fixtures/sample_design.json` into a `Design` model:

```python
@pytest.fixture
def sample_design():
    return parse_design_file(FIXTURES_DIR / "sample_design.json")
```

### Writing Tests

For checker tests, instantiate the checker directly and call `check()`:

```python
def test_checker_detects_issue(sample_design):
    checker = MyChecker(config={"param": "value"})
    results = checker.check(sample_design)
    assert results[0].status == Status.FAIL
    assert len(results[0].findings) > 0
```

For engine tests, use `run_checks()`:

```python
def test_run_selected_checkers(sample_design):
    report = run_checks(sample_design, selected_checkers=["duplicate_refdes"])
    assert report.summary.total_checks == 1
```

For API tests, use FastAPI's `TestClient`:

```python
from fastapi.testclient import TestClient
from orcad_checker.web.app import app

client = TestClient(app)

def test_list_checkers():
    response = client.get("/api/v1/checkers")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
```

---

## Database

### Location

SQLite database at `data/orcad_checker.db`, auto-created on first access via `Database.__init__()`.

### No Migration Framework

Tables are created with `CREATE TABLE IF NOT EXISTS` on every `Database()` instantiation. Schema changes require either:
- Manually altering the SQLite database
- Deleting the database file and letting it be recreated
- Adding `ALTER TABLE` statements to `_init_tables()`

### Seeding

The knowledge base is seeded from `data/seed_knowledge.json` via `store/seed.py`:

```python
from orcad_checker.store.seed import seed_knowledge
seed_knowledge()  # Only seeds if knowledge_docs table is empty
```

The seed file contains 7 documents covering OrCAD TCL API reference, examples, and best practices.

### Direct Access

The `Database` class can be used directly for testing or scripting:

```python
from orcad_checker.store.database import Database

db = Database()  # Uses default path
# or
db = Database("/tmp/test.db")  # Custom path

scripts = db.list_scripts(status="published")
doc = db.create_doc(KnowledgeDoc(title="My Doc", content="..."))
```

---

## Docker Deployment

### Building

```bash
# Build the image
docker compose build

# Or build directly
docker build -t orcad-checker .
```

### Running

```bash
# Start with docker compose
docker compose up -d

# View logs
docker compose logs -f orcad-checker

# Stop
docker compose down
```

### Configuration

Create a `.env` file in the project root:

```env
PORT=8000
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### Volumes

| Container Path | Purpose |
|---------------|---------|
| `/app/data` | SQLite database persistence (named volume `orcad-data`) |
| `/app/rules` | Rule YAML files (bind mount for live updates) |

### Health Check

The container has a built-in health check that polls `GET /api/v1/checkers` every 30 seconds.

---

## Frontend Development

### Stack

- **Vue 2.7** with Options API
- **Element UI 2.15** for UI components
- **Axios** for HTTP requests
- **Vue CLI 5** for build tooling

### Development Server

```bash
cd frontend
npm install
npm run serve    # Starts on :8080 with proxy to :8000
```

The `vue.config.js` proxies `/api/*` requests to `http://localhost:8000`:

```javascript
module.exports = {
  devServer: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  outputDir: 'dist',
};
```

### Production Build

```bash
cd frontend
npm run build    # Outputs to frontend/dist/
```

The FastAPI app serves `frontend/dist/` as static files when the directory exists:

```python
frontend_dist = Path(__file__).parent.parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
```

### Component Structure

| Component | File | Description |
|-----------|------|-------------|
| `FileUpload` | `FileUpload.vue` | Design JSON file upload (drag-and-drop) |
| `CheckerSelector` | `CheckerSelector.vue` | Checker selection grid with run button |
| `ResultDashboard` | `ResultDashboard.vue` | Check results summary and details |
| `ResultDetail` | `ResultDetail.vue` | Individual check result display |
| `AiSummary` | `AiSummary.vue` | AI-generated result summary |
| `RuleEditor` | `RuleEditor.vue` | YAML rule editor |
| `ScriptMarket` | `ScriptMarket.vue` | Script marketplace CRUD |
| `AiChat` | `AiChat.vue` | AI assistant chat interface |
| `KnowledgeBase` | `KnowledgeBase.vue` | Knowledge document management |

### API Modules

- `frontend/src/api/index.js`: Core API (checkers, check, rules, summarize)
- `frontend/src/api/scripts.js`: Scripts, knowledge, agent, and client APIs

---

## TCL Client Development

### Loading in OrCAD

In OrCAD Capture's TCL console:

```tcl
source "C:/path/to/tcl/orcad_checker.tcl"
```

This loads all components and opens the GUI automatically.

### Setting Server URL

Before sourcing, set the server URL if not using localhost:

```tcl
set ::server_url "http://192.168.1.100:8000"
source "C:/path/to/tcl/orcad_checker.tcl"
```

### Adding a TCL Checker

1. Create `tcl/checkers/my_check.tcl` implementing a proc that:
   - Takes a `design` parameter (the OrCAD design object)
   - Uses OrCAD TCL API to inspect the design
   - Calls `finding` to create finding dicts
   - Calls `check_result` to record the result
2. Add `source [file join $_checker_dir my_check.tcl]` to `load_all.tcl`
3. Add the checkbox variable and proc name mapping to `main_window.tcl`

### Available TCL Commands After Loading

| Command | Description |
|---------|-------------|
| `orcad_checker_gui` | Open the GUI window |
| `run_all_checks` | Run all checks (text output to console) |
| `run_single_check <name>` | Run one specific check |
| `upload_check_results <name>` | Upload results to server |
| `agent_chat <session_id> <message>` | Chat with AI agent |
| `fetch_ota_manifest` | Get OTA update manifest |
| `download_script <id>` | Download a script from server |

---

## AI Provider Configuration

### Anthropic (Default)

```env
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

Uses the official `anthropic` Python SDK with async client.

### OpenAI-Compatible

For internal LLM deployments or other OpenAI-compatible APIs:

```env
AI_PROVIDER=openai_compatible
OPENAI_BASE_URL=http://192.168.1.100:8000/v1
OPENAI_API_KEY=your-key
OPENAI_MODEL=your-model-name
```

Uses the official `openai` Python SDK pointed at the custom base URL. The API key can be set to any value if the internal deployment does not require authentication.

### Adding a New Provider

1. Create `src/orcad_checker/ai/my_provider.py`
2. Implement the `BaseLLMClient` interface:
   ```python
   from orcad_checker.ai.base_client import BaseLLMClient

   class MyProviderClient(BaseLLMClient):
       async def chat(self, system_prompt: str, user_message: str) -> str:
           # Call your provider's API
           return response_text
   ```
3. Add a case in the `_create_client()` function in both `tcl_agent.py` and `summarizer.py`

---

## Troubleshooting

### "No active design" error in TCL

The OrCAD design must be open before running checks. Ensure a `.dsn` file is open in OrCAD Capture.

### Database locked errors

SQLite uses WAL journal mode for better concurrent read access, but only one writer is allowed at a time. If running multiple processes, consider using separate database instances or adding retry logic.

### Frontend shows blank page

1. Ensure the backend is running on port 8000
2. In development, ensure the frontend dev server is running (`npm run serve`)
3. In production, ensure `frontend/dist/` exists (run `cd frontend && npm run build`)

### AI features return errors

1. Verify `AI_PROVIDER` is set correctly
2. Check that the corresponding API key is set and valid
3. For `openai_compatible`, verify `OPENAI_BASE_URL` is reachable
4. Check server logs for detailed error messages

### Checkers not found

`discover_checkers()` auto-imports all modules in `src/orcad_checker/checkers/`. Ensure:
- The file is in the `checkers/` directory
- The file is not named `base.py` (excluded from discovery)
- The class has the `@register_checker("rule_id")` decorator
- There are no import errors in the module

### OrCAD auto-load directory not found

Set the `CDS_ROOT` environment variable to your Cadence installation root, or use `orcad-check scripts deploy` which checks common paths like `C:/Cadence/SPB_17.4/tools/capture/tclscripts/capAutoLoad`.

### Test failures

```bash
# Run tests with verbose output to see details
pytest -v

# Run a single test for debugging
pytest tests/test_engine.py::test_run_checks -v -s
```

Ensure `pip install -e ".[dev]"` has been run to install test dependencies (`pytest`, `pytest-asyncio`).
