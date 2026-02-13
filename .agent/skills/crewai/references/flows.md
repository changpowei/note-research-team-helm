# CrewAI Flows

Flows 是 CrewAI 的事件驅動工作流引擎，提供狀態管理、條件邏輯和執行持久化。

## 基礎 Flow

```python
from crewai.flow.flow import Flow, listen, start

class MyFlow(Flow):
    @start()
    def start_method(self):
        print("Flow started")
        return "initial data"

    @listen(start_method)
    def second_method(self, data):
        print(f"Received: {data}")
        return "processed data"

# 執行 flow
flow = MyFlow()
result = flow.kickoff()
```

## Flow 裝飾器

### @start()

標記 flow 的入口點：

```python
@start()
def generate_data(self):
    return {"user_id": 123, "action": "research"}
```

### @listen()

監聽其他方法的輸出：

```python
@listen(generate_data)
def process_data(self, data):
    # data 來自 generate_data 的返回值
    return processed_result
```

### 條件 Listeners

#### OR 邏輯

```python
@listen(or_(method1, method2))
def process_either(self, result):
    # method1 或 method2 任一完成時觸發
    pass
```

#### AND 邏輯

```python
@listen(and_(method1, method2))
def process_both(self, results):
    # 兩個方法都完成時觸發
    # results 是 list: [result1, result2]
    pass
```

## 路由（Router）

根據條件執行不同路徑：

```python
from crewai.flow.flow import Flow, start, listen, router

class ConditionalFlow(Flow):
    @start()
    def start_flow(self):
        return {"type": "urgent"}

    @router(start_flow)
    def route_task(self, data):
        if data["type"] == "urgent":
            return "handle_urgent"
        else:
            return "handle_normal"

    @listen("handle_urgent")
    def handle_urgent_task(self, data):
        print("Handling urgent task")

    @listen("handle_normal")
    def handle_normal_task(self, data):
        print("Handling normal task")
```

## 狀態管理

### 非結構化狀態

```python
class StatefulFlow(Flow):
    @start()
    def start_method(self):
        self.state["counter"] = 0
        self.state["data"] = []

    @listen(start_method)
    def increment(self):
        self.state["counter"] += 1
        self.state["data"].append("item")
```

### 結構化狀態（推薦）

```python
from pydantic import BaseModel

class FlowState(BaseModel):
    counter: int = 0
    data: list[str] = []

class TypedFlow(Flow[FlowState]):
    @start()
    def start_method(self):
        self.state.counter = 0
        self.state.data = []

    @listen(start_method)
    def increment(self):
        self.state.counter += 1  # 類型安全
```

## Flow 持久化

### Class 級別持久化

```python
@Flow(persist=True)
class PersistentFlow(Flow):
    # 整個 flow 狀態會被持久化
    pass
```

### Method 級別持久化

```python
class SelectiveFlow(Flow):
    @start(persist=True)
    def important_step(self):
        return critical_data

    @listen(important_step, persist=False)
    def transient_step(self, data):
        return temporary_result
```

持久化允許：
- 從失敗點恢復
- 暫停和恢復長時間運行的流程
- 審計和重放執行歷史

## 整合 Crews 到 Flows

```python
from crewai import Crew
from crewai.flow.flow import Flow, start, listen

class ResearchFlow(Flow):
    @start()
    def prepare_research(self):
        return {"topic": "AI agents"}

    @listen(prepare_research)
    def run_research_crew(self, data):
        crew = Crew(
            agents=[researcher_agent],
            tasks=[research_task]
        )
        result = crew.kickoff(inputs=data)
        return result

    @listen(run_research_crew)
    def run_writing_crew(self, research_data):
        crew = Crew(
            agents=[writer_agent],
            tasks=[writing_task]
        )
        return crew.kickoff(inputs={"research": research_data})
```

## 專案結構（Flows + Crews）

```
my_flow_project/
├── src/
│   └── my_flow_project/
│       ├── main.py              # Flow 定義
│       ├── crews/
│       │   ├── research_crew/
│       │   │   ├── crew.py
│       │   │   └── config/
│       │   │       ├── agents.yaml
│       │   │       └── tasks.yaml
│       │   └── writing_crew/
│       │       ├── crew.py
│       │       └── config/
│       │           ├── agents.yaml
│       │           └── tasks.yaml
```

範例 main.py：

```python
from crewai.flow.flow import Flow, start, listen
from crews.research_crew.crew import ResearchCrew
from crews.writing_crew.crew import WritingCrew

class ContentFlow(Flow):
    @start()
    def kickoff_research(self):
        result = ResearchCrew().crew().kickoff(
            inputs={"topic": "AI"}
        )
        return result

    @listen(kickoff_research)
    def kickoff_writing(self, research):
        result = WritingCrew().crew().kickoff(
            inputs={"research": research}
        )
        return result

def main():
    flow = ContentFlow()
    flow.kickoff()
```

## Human-in-the-Loop

在 flow 中加入人工審核：

```python
class ReviewFlow(Flow):
    @start()
    def generate_content(self):
        return "Draft content"

    @listen(generate_content)
    def human_review(self, content):
        # 等待人工輸入
        feedback = input(f"Review this content: {content}\nFeedback: ")
        return feedback

    @listen(human_review)
    def revise_content(self, feedback):
        return f"Revised based on: {feedback}"
```

## 執行 Flows

### 使用 Flow API

```python
flow = MyFlow()
result = flow.kickoff()
```

### 使用 CLI

```bash
crewai flow run
```

### Streaming 執行

```python
flow = MyFlow()
for chunk in flow.kickoff_stream():
    print(chunk)
```

## Plot Flows（視覺化）

生成 flow 執行圖表：

```python
flow = MyFlow()
flow.plot()  # 生成 flow 流程圖
```

這會創建一個視覺化圖表顯示：
- Flow 方法及其連接
- 執行順序
- 條件分支

## Flow 最佳實踐

1. **使用結構化狀態** - 使用 Pydantic 模型獲得類型安全
2. **適當的持久化** - 只持久化關鍵步驟，避免性能開銷
3. **錯誤處理** - 在關鍵步驟添加 try/except
4. **清晰的方法命名** - 方法名應描述其功能
5. **模組化** - 將複雜邏輯分解為多個方法
6. **利用路由** - 使用 router 實現複雜決策邏輯

## Flows vs Crews 使用時機

**使用 Crews 當：**
- 任務可以由一組 agents 順序或層級完成
- 不需要複雜的控制流程
- 主要是 agent 之間的協作

**使用 Flows 當：**
- 需要事件驅動的執行
- 有複雜的條件邏輯和分支
- 需要狀態管理和持久化
- 要整合多個 crews
- 需要長時間運行的工作流

**組合使用：**
使用 Flows 作為外層編排，在 flow 步驟中調用 crews 處理特定任務。這是推薦的企業級架構模式。
