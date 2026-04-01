# OrCAD Checker -- Feature Documentation

## Design Rule Checkers

OrCAD Checker ships with 7 built-in checkers. Each checker can be enabled/disabled and configured via `rules/default_rules.yaml`.

### duplicate_refdes -- Duplicate Reference Designator

- **Severity**: ERROR
- **Description**: Detects components sharing the same RefDes across schematic pages
- **Output**: Lists each duplicate RefDes and the pages where it appears
- **Parameters**: None

### missing_attributes -- Missing Attributes

- **Severity**: WARNING
- **Description**: Verifies that components have required attributes populated
- **Output**: Lists each component missing one or more required attributes
- **Parameters**:
  - `required_attributes`: List of attribute names to check (default: `["footprint", "value", "part_number"]`)

### unconnected_pins -- Unconnected Pins

- **Severity**: WARNING
- **Description**: Finds pins not connected to any net, excluding designated no-connect pins
- **Output**: Lists each unconnected pin with its component and pin name/number
- **Parameters**:
  - `ignore_pin_names`: Pin names to ignore (default: `["NC", "N/C", "DNC"]`)

### power_net_naming -- Power Net Naming

- **Severity**: WARNING
- **Description**: Validates that power nets follow naming conventions
- **Output**: Lists power nets not matching any allowed pattern
- **Parameters**:
  - `allowed_patterns`: List of regex patterns (default: `["^VCC_.*", "^VDD_.*", "^GND.*", "^VBAT.*", "^VIN.*"]`)

### footprint_validation -- Footprint Validation

- **Severity**: ERROR
- **Description**: Ensures every component has a PCB footprint assigned
- **Output**: Lists components without a footprint
- **Parameters**: None

### net_naming -- Net Naming

- **Severity**: INFO
- **Description**: Identifies auto-generated net names that should be given meaningful names
- **Output**: Lists nets matching forbidden (auto-generated) patterns
- **Parameters**:
  - `forbidden_patterns`: Regex patterns matching auto-generated names (default: `["^N\\d{5,}$"]`)

### single_pin_nets -- Single Pin Nets

- **Severity**: WARNING
- **Description**: Detects nets connected to only one pin, which usually indicates a wiring mistake
- **Output**: Lists single-pin nets with their sole connection
- **Parameters**:
  - `ignore_power_nets`: Whether to skip power nets (default: `true`)

---

## Rule Configuration

Rules are defined in `rules/default_rules.yaml`. The YAML format:

```yaml
schema_version: "1.0"

rules:
  - id: duplicate_refdes
    enabled: true
    severity: error

  - id: missing_attributes
    enabled: true
    severity: warning
    params:
      required_attributes:
        - footprint
        - value
        - part_number

  - id: unconnected_pins
    enabled: true
    severity: warning
    params:
      ignore_pin_names: ["NC", "N/C", "DNC"]
```

Each rule entry supports:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Must match the checker's registered rule ID |
| `enabled` | boolean | Whether the checker runs (default: `true`) |
| `severity` | string | Override: `error`, `warning`, or `info` |
| `params` | object | Checker-specific parameters passed to the constructor |

Rules can be edited via the web UI at the Rules tab, or by directly editing the YAML file.

---

## Script Marketplace

The script marketplace enables sharing and distributing TCL scripts across the organization.

### Browsing Scripts

The Script Market tab in the frontend (and `GET /api/v1/scripts`) lets users browse all scripts with filtering by:
- **Status**: `draft`, `published`, `deprecated`
- **Category**: `extraction`, `validation`, `automation`, `utility`, `custom`
- **Search**: Full-text search across name, description, and tags

### Creating Scripts

Scripts can be created through:
1. **Web UI**: The ScriptMarket component provides a form for name, description, category, tags, and code
2. **AI Agent**: Generate scripts via conversation, then save to the repository
3. **CLI**: Push a local TCL file with `orcad-check scripts push file.tcl --name "My Script"`
4. **API**: `POST /api/v1/scripts` with a `CreateScriptRequest` body

### Versioning

Every script update automatically:
- Bumps the patch version (e.g., `1.0.0` -> `1.0.1`)
- Creates a snapshot in the `script_versions` table with optional changelog
- Computes and stores a SHA-256 checksum

Version history is accessible via `GET /api/v1/scripts/{id}/versions`.

### Publishing

Scripts start in `draft` status. Publishing (`POST /api/v1/scripts/{id}/publish`) sets status to `published`, making them available for OTA distribution to clients.

### OTA Updates

The OTA (Over-The-Air) update system distributes published scripts to OrCAD clients:

1. **Manifest**: `GET /api/v1/scripts/ota/manifest?client_id=xxx` returns all published scripts (filtered to those updated since the client's last sync)
2. **Download**: `GET /api/v1/scripts/ota/download/{id}` returns the full script content
3. **Client sync**: The CLI `orcad-check ota check` / `orcad-check ota update` commands check and pull updates

Scripts are installed locally to `~/.orcad_checker/scripts/{id}/` with `meta.json` and the `.tcl` file. They can be deployed to OrCAD's auto-load directory via `orcad-check scripts deploy {id}`.

---

## Knowledge Base

The knowledge base stores TCL API documentation and examples that are used as context for the AI agent.

### Categories

- **api**: OrCAD Capture TCL API reference (e.g., `GetActiveDesign`, `GetPartInsts`, `GetPropValue`)
- **example**: Complete working TCL scripts (e.g., BOM export, batch property update)
- **guide**: Best practices and patterns

### Seed Data

On first run, the knowledge base is populated from `data/seed_knowledge.json` with 7 documents covering:
- Design Access API
- Component Access API
- Net Access API
- Design Modification API
- TCL Best Practices guide
- BOM Export example
- Batch Property Update example

### Management

Docs can be managed via the web UI KnowledgeBase component or the REST API:
- Create, read, update, delete individual docs
- Filter by category or search by keyword
- Documents are searchable and automatically provided as context to the AI agent

---

## AI Agent

The AI agent generates TCL scripts through natural language conversation.

### How It Works

1. User sends a message describing what they want (e.g., "Create a script that exports all resistor values to a CSV file")
2. The agent searches the knowledge base for relevant API docs and examples
3. A system prompt is built with the knowledge context injected
4. The conversation history + system prompt is sent to the configured LLM provider
5. The response is returned with any TCL code blocks automatically extracted

### Features

- **Multi-turn conversation**: Session history is maintained for follow-up questions and refinements
- **Knowledge-augmented**: Relevant API docs and examples are automatically included as context
- **Code extraction**: TCL code blocks (` ```tcl ... ``` `) are extracted from responses and made available separately
- **Save to repository**: Generated scripts can be saved to the script marketplace directly
- **Execute in OrCAD**: From the TCL GUI, generated code can be executed immediately in OrCAD (with confirmation prompt)
- **Bilingual**: Responds in the same language as the user's input (Chinese or English)

### Sessions

Sessions are stored in-memory on the server. Each session has:
- A unique `session_id`
- Full message history (user + assistant turns)
- Can be retrieved via `GET /api/v1/agent/sessions/{id}` or cleared via `DELETE`

---

## AI Summarization

Check results can be summarized by AI via the "AI Summary" feature:

1. After checks complete, the report JSON is sent to `POST /api/v1/summarize`
2. The summarizer sends the report to the LLM with a system prompt instructing it to:
   - Prioritize findings (critical errors first)
   - Explain root causes
   - Provide actionable fix recommendations
   - Highlight systemic patterns
3. The summary is displayed below the result dashboard in the frontend

---

## Client Management

### Registration

OrCAD clients register with the server via `POST /api/v1/clients/register`, providing:
- `client_id`: Unique identifier (auto-generated UUID on first run)
- `hostname`: Machine hostname
- `username`: OS username
- `orcad_version`: Detected from `CDS_ROOT` environment variable
- `installed_scripts`: List of locally installed script IDs

Registration uses `INSERT OR REPLACE`, so re-registering updates the existing record.

### Sync Tracking

Each registration updates `last_sync` timestamp. The OTA manifest endpoint uses this to filter scripts that have changed since the client's last sync.

### Client Configuration

Clients store configuration at `~/.orcad_checker/config.json`:

```json
{
  "client_id": "a1b2c3d4",
  "server_url": "http://localhost:8000",
  "auto_update": true,
  "check_interval_minutes": 30
}
```

---

## Check Results Upload

The TCL client can upload check results to the server for centralized tracking.

### Upload Format

```json
{
  "design_name": "MyBoard",
  "source": "orcad_tcl",
  "results": [
    {
      "rule_id": "duplicate_refdes",
      "severity": "ERROR",
      "status": "PASS",
      "findings": []
    }
  ]
}
```

### Storage

Results are stored in-memory (up to 100 most recent uploads). Each upload receives a unique `result_id` and timestamp.

### History

- `GET /api/v1/check-results/history?limit=20` returns recent uploads
- `GET /api/v1/check-results/{id}` returns a specific result

---

## CLI Commands

The `orcad-check` CLI provides these commands:

### `orcad-check run <design_file>`

Run checkers against a design JSON export.

```
Options:
  --rules PATH       Path to YAML rules config file
  --checkers IDS     Comma-separated checker IDs (default: all)
  --json             Output results as JSON
```

Example:
```bash
orcad-check run design.json --rules rules/default_rules.yaml --json
```

### `orcad-check list`

List all available checkers with their severity and description.

### `orcad-check serve`

Start the FastAPI web server.

```
Options:
  --host HOST    Bind host (default: 0.0.0.0)
  --port PORT    Bind port (default: 8000)
```

### `orcad-check scripts {list|install|remove|deploy|push}`

Local script management:
- `list`: Show locally installed scripts
- `install <script_id>`: Download and install from server
- `remove <script_id>`: Remove local script
- `deploy <script_id>`: Copy to OrCAD's auto-load directory
- `push <file> --name "Name"`: Upload local TCL file to server

### `orcad-check ota {check|update|register}`

OTA update management:
- `check`: Check server for available updates
- `update`: Pull all available updates
- `register`: Register this client with the server

---

## Frontend Features

The Vue 2 frontend has four main tabs:

### Design Check Tab

1. **FileUpload**: Drag-and-drop or file picker for design JSON files
2. **CheckerSelector**: Checkbox grid of available checkers with run button
3. **ResultDashboard**: Summary statistics (pass/error/warning counts) and detailed per-check results with color-coded findings
4. **AiSummary**: Generates and displays an AI-powered summary of check results

### Script Market Tab

**ScriptMarket** component:
- Browse all scripts with category/status filters
- Create new scripts with code editor
- View script code, version history
- Publish scripts for OTA distribution
- Delete scripts

### AI Assistant Tab

**AiChat** component:
- Chat interface for conversational TCL script generation
- Displays conversation history with styled messages
- Shows extracted TCL code blocks
- Save generated scripts to the repository

### Knowledge Base Tab

**KnowledgeBase** component:
- Browse and search knowledge documents
- Create/edit documents with category and tag management
- View formatted document content
