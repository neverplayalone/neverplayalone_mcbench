# Never Play Alone Benchmark

NPABench is a Minecraft benchmark harness for protocol agents.

## Quick Start

```bash
pip install -e .
(cd tools/recorder && npm install)
(cd examples/agents/log_gatherer && npm install)

npabench run log_gatherer=examples/agents/log_gatherer \
  --mission resource_gathering \
  --seed 42
```

Multiple agents on the same generated task:

```bash
npabench run \
  agent_a=/path/to/agent_a \
  agent_b=/path/to/agent_b \
  --mission resource_gathering \
  --seed 42 \
  --max-parallel 2
```

Host subprocess mode for trusted local debugging:

```bash
npabench run log_gatherer=examples/agents/log_gatherer --no-sandbox
```

## Python API

```python
from npabench import AgentSpec, evaluate_single_agent

report = evaluate_single_agent(
    AgentSpec(name="log_gatherer", path="examples/agents/log_gatherer"),
    mission_id="resource_gathering",
    seed=42,
)
print(report.score, report.status)
```

## Layout

```text
npabench/
  config.py
  cli.py
  missions/
  evaluation/
  agents/
  minecraft/
  recording/
tools/
  recorder/
examples/
  agents/
tests/
  unit/
  integration/
```
