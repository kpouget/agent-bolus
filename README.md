# Agent Bolus 🩺

A collection of AI agents and tools for diabetes monitoring and analysis.

## 📁 Project Structure

```
agent-bolus/
├── carelink_mcp_server.py          # MCP server for Carelink API downloads
├── carelink_data_mcp_server.py     # MCP server for querying CSV/JSON data
├── quickstart/                     # CLI scripts for MCP servers
│   ├── helpers.sh                  #   Bash functions for easy usage
│   ├── basic.sh                    #   Raw JSON-RPC examples
│   ├── workflows.sh                #   Complete monitoring workflows
│   ├── oneliners.sh                #   Copy-paste commands
│   └── testing.sh                  #   Test suite
├── nooa/                           # NOOA agent examples
│   ├── nooa_simple_fixed.py        #   Minimal working example
│   ├── nooa_working_example.py     #   Comprehensive demo
│   ├── diabetes_nooa_fixed.py      #   Diabetes analysis agent
│   └── test_nooa_fixed.py          #   Test runner
├── data/                           # Downloaded Carelink data
└── carelink-python-client/         # Carelink API client library
```

## 🚀 Quick Start

### 1. MCP Servers (Carelink Data Access)
```bash
# Use helper functions
source quickstart/helpers.sh
download_csv 14
get_bg_readings 1

# Or see all CLI examples
bash quickstart/oneliners.sh
```

### 2. NOOA Agents (AI Analysis)
```bash
# Test simple NOOA agent
uv run nooa/nooa_simple_fixed.py

# Test diabetes analysis agent
uv run nooa/diabetes_nooa_fixed.py
```

## 📊 Features

### MCP Servers
- **Download CSV data** from Carelink API (1-90 days)
- **Query glucose readings** by date/age
- **Analyze Time-in-Range** data
- **Web interface data** access
- **Bash helper functions** for easy CLI usage

### NOOA Agents  
- **Object-oriented AI agents** using NVIDIA's NOOA framework
- **Diabetes analysis** with clinical insights
- **Generation methods** implemented by LLM at runtime
- **Type-safe interfaces** with Python annotations

## 🔗 Documentation

| Component | Documentation |
|-----------|---------------|
| **MCP CLI Usage** | [QUICKSTART.md](QUICKSTART.md) |
| **MCP API Reference** | [README_Carelink_API_MCP.md](README_Carelink_API_MCP.md) |
| **NOOA Examples** | [nooa/README.md](nooa/README.md) |
| **Helper Scripts** | [quickstart/README.md](quickstart/README.md) |

## ⚙️ Configuration

Create `.env` file with your credentials:
```bash
MODEL_NAME=your-model-name
ACCESS_KEY=your-api-key  
MODEL_URL=your-endpoint-url
```

## 💉 Use Cases

- **Daily glucose monitoring** with CLI automation
- **Pattern analysis** using AI agents  
- **Time-in-Range tracking** and trends
- **Clinical insights** generation
- **Data pipeline automation** for diabetes management

Built for diabetes self-management and clinical analysis! 📈