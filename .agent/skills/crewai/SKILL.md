---
name: crewai
description: Build multi-agent AI systems with CrewAI framework. Use when creating collaborative AI agents, orchestrating agent crews, managing AI workflows with state management, implementing sequential or hierarchical processes, building event-driven AI automations, or needing role-based AI agents with specialized tools and capabilities.
---

# CrewAI

構建生產級多 agent AI 系統的框架，支援 agent 協作、流程編排和狀態管理。

## 核心架構

CrewAI 由兩個主要組件構成：

1. **Flows（流程）** - 應用主幹，提供事件驅動工作流、狀態管理和控制流程
2. **Crews（團隊）** - 工作單元，由多個協作 agent 組成來完成特定任務

## 快速開始

### 安裝與專案創建

```bash
# 創建新專案
crewai create crew <project_name>

# 進入專案目錄
cd <project_name>

# 安裝依賴
crewai install

# 執行 crew
crewai run
```

### 專案結構

```
my_project/
├── .env                      # API keys 和環境變數
├── pyproject.toml
├── knowledge/                # 知識庫目錄
└── src/
    └── my_project/
        ├── main.py           # 專案入口
        ├── crew.py           # Crew 編排邏輯
        ├── tools/            # 自定義工具
        │   ├── custom_tool.py
        │   └── __init__.py
        └── config/
            ├── agents.yaml   # Agent 定義
            └── tasks.yaml    # Task 定義
```

## 定義 Agents（YAML 推薦）

```yaml
# config/agents.yaml
researcher:
  role: >
    {topic} Senior Data Researcher
  goal: >
    Uncover cutting-edge developments in {topic}
  backstory: >
    You're a seasoned researcher with a knack for uncovering the latest
    developments in {topic}. Known for your ability to find the most relevant
    information and present it clearly.

reporting_analyst:
  role: >
    {topic} Reporting Analyst
  goal: >
    Create detailed reports based on {topic} data analysis
  backstory: >
    You're a meticulous analyst with a keen eye for detail. Known for
    turning complex data into clear and concise reports.
```

**關鍵 Agent 屬性：**
- `role` - Agent 角色
- `goal` - Agent 目標
- `backstory` - 背景故事（影響行為）
- `llm` - 使用的語言模型（可選）
- `tools` - Agent 可用工具
- `allow_delegation` - 是否允許委派任務給其他 agent（預設 false）
- `verbose` - 詳細輸出模式
- `max_iter` - 最大迭代次數（預設 25）
- `memory` - 是否啟用記憶功能
- `allow_code_execution` - 是否允許執行代碼

## 定義 Tasks（YAML 推薦）

```yaml
# config/tasks.yaml
research_task:
  description: >
    Conduct thorough research about {topic}.
    Find interesting and relevant information.
  expected_output: >
    A list with 10 bullet points of the most relevant
    information about {topic}
  agent: researcher

reporting_task:
  description: >
    Review the context and expand each topic into a full
    section for a report with detailed information.
  expected_output: >
    A fully fledged report with main topics, each with a
    full section of information. Formatted as markdown.
  agent: reporting_analyst
  output_file: report.md
```

**關鍵 Task 屬性：**
- `description` - 任務描述
- `expected_output` - 預期輸出
- `agent` - 執行任務的 agent
- `output_file` - 輸出文件路徑（可選）
- `context` - 依賴的其他 task（可選）
- `async_execution` - 異步執行（可選）
- `tools` - 任務專用工具（可選）

## 創建 Crew（Python）

```python
# src/my_project/crew.py
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool

@CrewBase
class MyProjectCrew():
    """MyProject crew"""

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config['researcher'],
            verbose=True,
            tools=[SerperDevTool()]
        )

    @agent
    def reporting_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config['reporting_analyst'],
            verbose=True
        )

    @task
    def research_task(self) -> Task:
        return Task(
            config=self.tasks_config['research_task']
        )

    @task
    def reporting_task(self) -> Task:
        return Task(
            config=self.tasks_config['reporting_task'],
            output_file='output/report.md'
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,  # 或 Process.hierarchical
            verbose=True
        )
```

## 執行 Crew

```python
# src/my_project/main.py
from my_project.crew import MyProjectCrew

def run():
    inputs = {
        'topic': 'AI Agents'
    }
    result = MyProjectCrew().crew().kickoff(inputs=inputs)
    print(result)
```

## Crew 生命週期 Hook

```python
from crewai.project import before_kickoff, after_kickoff

@CrewBase
class MyProjectCrew():
    @before_kickoff
    def before_kickoff_function(self, inputs):
        print(f"Starting with inputs: {inputs}")
        return inputs  # 可修改 inputs

    @after_kickoff
    def after_kickoff_function(self, result):
        print(f"Completed with result: {result}")
        return result  # 可修改 result
```

## Process 類型

1. **Sequential（順序）** - Tasks 按順序執行
2. **Hierarchical（層級）** - 有 manager agent 協調和委派任務

```python
# Hierarchical process
crew = Crew(
    agents=agents,
    tasks=tasks,
    process=Process.hierarchical,
    manager_llm="gpt-4"
)
```

## Tools（工具）

### 使用內建工具

```python
from crewai_tools import (
    SerperDevTool,      # Web 搜索
    WebsiteSearchTool,  # 網站搜索
    FileReadTool,       # 讀取文件
    DirectoryReadTool,  # 讀取目錄
    # ... 更多工具
)

agent = Agent(
    role="Researcher",
    tools=[SerperDevTool(), WebsiteSearchTool()]
)
```

### 創建自定義工具

參見 [references/custom_tools.md](references/custom_tools.md)

## Flows（進階）

參見 [references/flows.md](references/flows.md) 瞭解如何：
- 創建事件驅動工作流
- 管理狀態和持久化
- 使用條件邏輯和路由
- 實現 human-in-the-loop

## 常見模式

### 1. 研究報告生成

```yaml
# agents.yaml
researcher:
  role: Researcher
  goal: Research {topic}
  
writer:
  role: Writer
  goal: Write report on {topic}

# tasks.yaml
research:
  description: Research {topic}
  agent: researcher
  
write_report:
  description: Write comprehensive report
  agent: writer
  context: [research]
  output_file: report.md
```

### 2. 數據分析流程

```python
@task
def analyze_data(self) -> Task:
    return Task(
        description="Analyze dataset",
        expected_output="Analysis results",
        output_pydantic=AnalysisResult  # 結構化輸出
    )
```

### 3. 多階段工作流

使用 `context` 建立 task 依賴關係：

```python
task2 = Task(
    description="Process results from task1",
    context=[task1],  # task2 會接收 task1 的輸出
    agent=processor_agent
)
```

## 結構化輸出

```python
from pydantic import BaseModel

class Report(BaseModel):
    title: str
    sections: list[str]
    conclusion: str

@task
def generate_report(self) -> Task:
    return Task(
        description="Generate report",
        output_pydantic=Report  # 強制結構化輸出
    )
```

## 最佳實踐

1. **使用 YAML 配置** - Agent 和 task 定義更清晰
2. **明確定義角色** - 清晰的 role、goal、backstory
3. **預期輸出要具體** - 詳細描述 expected_output
4. **合理使用工具** - 給 agent 適當的工具
5. **利用 context** - 建立 task 依賴關係
6. **環境變數管理** - 使用 .env 存放 API keys
7. **結構化輸出** - 使用 Pydantic 模型確保輸出格式

## 相關資源

- [API Reference](https://docs.crewai.com/api-reference/introduction)
- [Custom Tools](references/custom_tools.md)
- [Flows Guide](references/flows.md)
- [Official Documentation](https://docs.crewai.com)
