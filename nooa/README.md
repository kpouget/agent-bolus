# NOOA (NVIDIA Object Oriented Agents) Examples

Working examples of NOOA agents using your Red Hat AI Services endpoint.

## 📁 Files

| File | Purpose |
|------|---------|
| `nooa_simple_fixed.py` | ✅ Minimal working example |
| `nooa_working_example.py` | ✅ Comprehensive demo with multiple features |
| `diabetes_nooa_fixed.py` | ✅ Diabetes analysis agent |
| `test_nooa_fixed.py` | ✅ Test runner for all examples |

## 🚀 Quick Start

```bash
# Test individual examples
uv run nooa/nooa_simple_fixed.py
uv run nooa/diabetes_nooa_fixed.py

# Test all examples
uv run nooa/test_nooa_fixed.py all
```

## 🔑 Key Pattern

NOOA requires this specific configuration pattern:

```python
from nooa import Agent
from nooa.unifiedllm.registry import get_llm_client

# Create LLM client
llm = get_llm_client(
    f"openai/{os.getenv('MODEL_NAME')}",
    api_base=os.getenv('MODEL_URL'),
    api_key=os.getenv('ACCESS_KEY')
)

# Agent class with LLM as class parameter
class MyAgent(Agent, llm=llm):
    """Agent description becomes context."""
    
    # State (typed fields)
    counter: int = 0
    
    # Regular Python method
    def increment(self):
        self.counter += 1
    
    # Generation method (LLM implements this)
    async def say_hello(self, name: str) -> str:
        """Docstring becomes the prompt for LLM."""
        ...  # LLM implements this at runtime

# Simple usage
agent = MyAgent()
result = await agent.say_hello("Kevin")
```

## 💡 Key Concepts

- **Generation methods**: Methods with `...` bodies get implemented by LLM
- **Type contracts**: Method signatures define input/output contracts
- **Mixed paradigm**: Combine deterministic Python with LLM-driven methods
- **State management**: Regular Python object state with typed fields

## ✅ Verified Working

All examples have been tested with your Red Hat AI Services endpoint and work correctly.

Configuration automatically uses `.env` file:
- `MODEL_NAME=wFcOyREEbF7J`
- `ACCESS_KEY=sk-wFcOyREEbF7J-aj0kOojUg`  
- `MODEL_URL=https://litemaas.rhoai.rh-aiservices-bu.com`