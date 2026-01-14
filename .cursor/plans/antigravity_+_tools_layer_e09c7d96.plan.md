---
name: Antigravity + Tools Layer
overview: Integrate Antigravity as the LLM provider, deploy PostgreSQL with pgvector on the remote server, implement Agent Tools system, and configure split deployment (Vercel frontend + server backend).
todos:
  - id: antigravity-integration
    content: Modify env.example and configs/models.yaml for Antigravity, create AntigravityLLMClient in agents/base.py
    status: completed
  - id: schema-extensions
    content: Add agent_memory, memory_approvals, tool_calls, meeting_artifacts tables to storage/schema.sql
    status: completed
  - id: deploy-script
    content: Create scripts/deploy_db.sh for PostgreSQL + pgvector installation on remote server
    status: completed
  - id: backend-deploy-script
    content: Create scripts/deploy_backend.sh for FastAPI backend with systemd service on server
    status: completed
    dependencies:
      - deploy-script
  - id: vercel-config
    content: Configure Next.js for Vercel deployment with environment variables and API proxy
    status: completed
  - id: cors-setup
    content: Add CORS middleware to FastAPI backend for Vercel domain access
    status: completed
  - id: tools-registry
    content: Create tools/ package with registry.py defining OpenAI function-calling schemas for all 7 tools
    status: completed
  - id: market-tools
    content: Implement tools/market.py with get_ohlcv, get_quote, compute_indicators using ccxt
    status: completed
    dependencies:
      - tools-registry
  - id: backtest-tool
    content: Implement tools/backtest.py wrapping existing backtest engine with experiment_id generation
    status: completed
    dependencies:
      - tools-registry
  - id: memory-tools
    content: Implement tools/memory.py with hybrid search (pgvector + keyword) and approval flow
    status: completed
    dependencies:
      - tools-registry
      - schema-extensions
  - id: meeting-tool
    content: Implement tools/meeting.py for presenting cards/plots in meeting context
    status: completed
    dependencies:
      - tools-registry
      - schema-extensions
  - id: tool-router
    content: Create orchestrator/tool_router.py with RBAC, budget control, and audit logging
    status: completed
    dependencies:
      - tools-registry
  - id: permissions-update
    content: Update configs/permissions.yaml with tool-level access rules
    status: completed
    dependencies:
      - tool-router
  - id: agent-prompts
    content: Update agent system prompts to enforce tool-calling discipline (no fabrication)
    status: completed
    dependencies:
      - tool-router
---

# Antigravity Integration + Agent Tools System + Split Deployment

## Deployment Architecture

```mermaid
flowchart TB
    subgraph Vercel[Vercel Cloud]
        FE[Next.js Frontend]
    end
    
    subgraph Server[Your Server 154.26.181.47]
        subgraph Backend[FastAPI Backend :8000]
            API[REST API]
            WS[WebSocket]
            CORS[CORS Middleware]
        end
        
        subgraph Orchestrator[Orchestrator]
            TR[Tool Router]
            PERM[Permission Check]
            BUDGET[Budget Control]
        end
        
        subgraph Tools[Tools Layer]
            MT[market tools]
            BT[backtest tools]
            MEM_T[memory tools]
            MEET_T[meeting tools]
        end
        
        subgraph Database[PostgreSQL + pgvector]
            PG[(aiquant DB)]
        end
    end
    
    subgraph External[External Services]
        AG[Antigravity LLM]
        CCXT[CCXT Exchanges]
    end
    
    FE -->|HTTPS API| CORS
    CORS --> API
    API --> TR
    TR --> PERM --> BUDGET
    BUDGET --> MT & BT & MEM_T & MEET_T
    MT --> CCXT
    MEM_T --> PG
    Backend -.-> AG
```

| Component | Location | URL |

|-----------|----------|-----|

| Frontend | Vercel | `https://aiquant.vercel.app` (or custom domain) |

| Backend API | Server | `http://154.26.181.47:8000` |

| PostgreSQL | Server | `154.26.181.47:5432` |

## Tools System Architecture

```mermaid
flowchart TB
    subgraph Agents
        A1[Research Agent]
        A2[Data Agent]
        A3[Backtest Agent]
    end
    
    subgraph ToolsLayer[Tools Layer]
        TR[Tool Router]
        MT[market.get_ohlcv]
        MQ[market.get_quote]
        MI[market.compute_indicators]
        BT[backtest.run]
        MW[memory.write]
        MS[memory.search]
        MP[meeting.present]
    end
    
    subgraph Controls[Orchestrator Controls]
        PERM[Permission Check]
        BUDGET[Budget Control]
        AUDIT[Audit Logger]
    end
    
    A1 --> TR
    A2 --> TR
    A3 --> TR
    TR --> PERM
    PERM --> BUDGET
    BUDGET --> AUDIT
    AUDIT --> MT & MQ & MI & BT & MW & MS & MP
```

---

## Part 1: Antigravity LLM Integration

### Changes to [env.example](env.example)

Replace individual provider keys with Antigravity configuration:

```bash
# Antigravity AI Service (OpenAI-compatible)
ANTIGRAVITY_API_KEY=your-antigravity-api-key
ANTIGRAVITY_BASE_URL=https://your-antigravity-endpoint.com/v1

# Embedding model for memory vector search
EMBEDDING_MODEL=text-embedding-3-small
```

### Changes to [configs/models.yaml](configs/models.yaml)

Add Antigravity as unified provider, keeping model mapping:

```yaml
providers:
  antigravity:
    base_url_env: "ANTIGRAVITY_BASE_URL"
    api_key_env: "ANTIGRAVITY_API_KEY"
    models:
      - "gpt-4o"
      - "claude-sonnet-4-20250514"
      - "gemini-2.0-flash"
```

### Changes to [agents/base.py](agents/base.py)

Create `AntigravityLLMClient` implementing `LLMClient` interface using OpenAI SDK with custom `base_url`.

---

## Part 2: PostgreSQL + pgvector Deployment

### Target Server

- Host: `154.26.181.47:22`
- User: `root`

### Deployment Script `scripts/deploy_db.sh`

Will create a script that:

1. Installs PostgreSQL 16
2. Installs pgvector extension
3. Configures remote access (bind 0.0.0.0, pg_hba.conf)
4. Creates `aiquant` database and user
5. Runs [storage/schema.sql](storage/schema.sql)

### Schema Additions to [storage/schema.sql](storage/schema.sql)

New tables for Tools system:

| Table | Purpose |

|-------|---------|

| `agent_memory` | Structured memory with pgvector embedding |

| `memory_approvals` | Approval gates for team/org memories |

| `tool_calls` | Audit log for all tool invocations |

| `meeting_artifacts` | Cards/plots presented in meetings |

---

## Part 3: Agent Tools System

### New Package Structure

```
tools/
  __init__.py
  registry.py      # Tool schema registry (OpenAI function calling format)
  market.py        # T1-T3: OHLCV, quote, indicators
  backtest.py      # T4: Backtest execution
  memory.py        # T5-T6: Memory write/search with hybrid ranking
  meeting.py       # T7: Meeting presentation cards
```

### Tool Specifications

| Tool | Cost (CP) | Permission | Returns |

|------|-----------|------------|---------|

| `market.get_ohlcv` | 1-10 (by rows) | research, data | data_version_hash, parquet_path |

| `market.get_quote` | 1 | all | last_price, 24h_stats |

| `market.compute_indicators` | 2-5 | research, backtest | feature_version_hash |

| `backtest.run` | 50-500 | research (Lead approve if >200) | experiment_id, metrics, artifacts |

| `memory.write` | 2 | all (team/org needs approval) | memory_id |

| `memory.search` | 1 | scope-based | ranked results with refs |

| `meeting.present` | 5 | only during active meeting | artifact_ids |

### Orchestrator Integration

New file `orchestrator/tool_router.py`:

```python
class ToolRouter:
    async def execute(self, agent_id, tool_name, args) -> ToolResult:
        # 1. Check permission (RBAC)
        # 2. Estimate & check budget
        # 3. Log tool_call_requested event
        # 4. Execute tool
        # 5. Log tool_call_executed + deduct budget
        # 6. Return result with data_version_hash/experiment_id
```

---

## Part 4: Hybrid Memory System

### Memory Table Schema

```sql
CREATE TABLE agent_memory (
    id UUID PRIMARY KEY,
    agent_id VARCHAR(64) NOT NULL,
    content TEXT CHECK (LENGTH(content) <= 500),
    tags TEXT[] NOT NULL,
    scope TEXT CHECK (scope IN ('private', 'team', 'org')),
    confidence FLOAT CHECK (confidence BETWEEN 0 AND 1),
    ttl INTERVAL,
    expires_at TIMESTAMPTZ,
    embedding vector(1536),
    refs JSONB NOT NULL,  -- {"experiment_id": "...", "data_version_hash": "..."}
    approval_status TEXT DEFAULT 'approved',  -- private auto-approved
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Hybrid Search Implementation

```sql
-- Combines: tag filter + keyword match + vector similarity (RRF ranking)
WITH filtered AS (
    SELECT * FROM agent_memory 
    WHERE tags && $tags AND scope IN ($visible_scopes)
),
vector_ranked AS (
    SELECT id, embedding <=> $query_embedding AS vec_dist,
           ROW_NUMBER() OVER (ORDER BY embedding <=> $query_embedding) AS vec_rank
    FROM filtered
),
text_ranked AS (
    SELECT id, ts_rank(search_vector, to_tsquery($query)) AS text_score,
           ROW_NUMBER() OVER (ORDER BY ts_rank DESC) AS text_rank
    FROM filtered WHERE search_vector @@ to_tsquery($query)
)
SELECT id, 1.0/(60+vec_rank) + 1.0/(60+text_rank) AS rrf_score
FROM vector_ranked v LEFT JOIN text_ranked t USING(id)
ORDER BY rrf_score DESC LIMIT $top_k;
```

### Approval Gates for team/org Memory

- `private`: Auto-approved, no gate
- `team`: Requires Lead approval
- `org`: Requires Chief of Staff + Risk/Skeptic gate

---

## Part 5: Permission Configuration

### Additions to [configs/permissions.yaml](configs/permissions.yaml)

```yaml
tools:
  market.get_ohlcv:
    allowed_agents: ["research_*", "data_*", "backtest_*"]
    max_limit: 10000
    allowed_timeframes: ["1d", "4h", "1h"]
    requires_approval_above: null
    
  backtest.run:
    allowed_agents: ["research_*", "backtest_*"]
    requires_approval_above: 200  # CP cost
    approvers: ["research_lead", "backtest_lead"]
    
  memory.write:
    scope_approval:
      private: null
      team: ["team_lead"]
      org: ["chief_of_staff", "cro"]
```

---

## Implementation Order

1. **Antigravity Integration** - Modify env, models.yaml, base.py
2. **Database Schema** - Add new tables to schema.sql
3. **Deploy Scripts** - Create scripts/deploy_db.sh and scripts/deploy_backend.sh
4. **CORS + Vercel Config** - Update FastAPI CORS, create vercel.json
5. **Tools Package** - registry.py, market.py, memory.py, backtest.py, meeting.py
6. **Tool Router** - orchestrator/tool_router.py with permission/budget
7. **Memory Approval Flow** - Integrate with existing approval system
8. **Agent Prompts Update** - Add tool-calling instructions
9. **Deploy** - Run deploy scripts, then `vercel --prod`

---

---

## Part 6: Split Deployment (Vercel + Server)

### Frontend on Vercel

#### Changes to [dashboard/web/next.config.js](dashboard/web/next.config.js)

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',  // For Vercel deployment
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.BACKEND_URL}/api/:path*`,
      },
    ];
  },
};
```

#### New file: `dashboard/web/.env.production`

```bash
NEXT_PUBLIC_API_URL=http://154.26.181.47:8000
BACKEND_URL=http://154.26.181.47:8000
```

#### New file: `dashboard/web/vercel.json`

```json
{
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "framework": "nextjs",
  "regions": ["hkg1"],
  "env": {
    "NEXT_PUBLIC_API_URL": "@api_url"
  }
}
```

### Backend on Server (154.26.181.47)

#### Changes to [dashboard/api/main.py](dashboard/api/main.py)

Add CORS middleware for Vercel domain:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://aiquant.vercel.app",
        "https://*.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### New file: `scripts/deploy_backend.sh`

```bash
#!/bin/bash
# Deploys FastAPI backend as systemd service on server

# 1. Install Python 3.11, pip, virtualenv
# 2. Create /opt/aiquant directory
# 3. Copy code and create venv
# 4. Install dependencies from requirements.txt
# 5. Create systemd service file
# 6. Enable and start service
# 7. Configure firewall (open port 8000)
```

#### New file: `scripts/aiquant.service` (systemd unit)

```ini
[Unit]
Description=AI Quant FastAPI Backend
After=network.target postgresql.service

[Service]
User=aiquant
WorkingDirectory=/opt/aiquant
ExecStart=/opt/aiquant/venv/bin/uvicorn dashboard.api.main:app --host 0.0.0.0 --port 8000
Restart=always
Environment="DATABASE_URL=postgresql+asyncpg://aiquant:password@localhost:5432/aiquant"
Environment="ANTIGRAVITY_API_KEY=your-key"
Environment="ANTIGRAVITY_BASE_URL=https://your-endpoint"

[Install]
WantedBy=multi-user.target
```

### Deployment Commands

```bash
# 1. Deploy database
ssh root@154.26.181.47 'bash -s' < scripts/deploy_db.sh

# 2. Deploy backend
ssh root@154.26.181.47 'bash -s' < scripts/deploy_backend.sh

# 3. Deploy frontend (from dashboard/web directory)
cd dashboard/web
vercel --prod
```

---

## Security Note

The SSH credentials you provided (154.26.181.47, root/siliConforge) are sensitive. The deployment script will be created but you should:

1. Change the password after initial setup
2. Use SSH keys instead of password auth
3. Consider creating a non-root user for the application
4. Use HTTPS with Let's Encrypt for the backend API (nginx reverse proxy)
5. Set Vercel environment variables via dashboard, not in code