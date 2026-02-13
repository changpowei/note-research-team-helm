# CrewAI Custom Tools

## 使用 @tool 裝飾器創建工具

最簡單的方式是使用 `@tool` 裝飾器：

```python
from crewai.tools import tool

@tool("Search Tool")
def search_tool(query: str) -> str:
    """Search the web for information about a query."""
    # 實作搜索邏輯
    return f"Search results for: {query}"
```

## 使用 BaseTool 子類

更進階的工具可以繼承 `BaseTool`：

```python
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

class SearchInput(BaseModel):
    """Input schema for SearchTool."""
    query: str = Field(..., description="Search query")

class SearchTool(BaseTool):
    name: str = "Search Tool"
    description: str = "Searches the web for information"
    args_schema: Type[BaseModel] = SearchInput

    def _run(self, query: str) -> str:
        # 實作搜索邏輯
        return f"Search results for: {query}"
```

## 異步工具

支援異步操作的工具：

```python
from crewai.tools import BaseTool

class AsyncSearchTool(BaseTool):
    name: str = "Async Search"
    description: str = "Async web search"

    async def _arun(self, query: str) -> str:
        # 異步搜索實作
        await some_async_operation()
        return results
```

使用方式：

```python
agent = Agent(
    role="Researcher",
    tools=[AsyncSearchTool()],
    # ...
)
```

## 工具快取

CrewAI 自動快取工具結果。自定義快取行為：

```python
@tool("Custom Cache Tool")
def custom_cache_tool(query: str) -> str:
    """Tool with custom caching."""
    return expensive_operation(query)

# 使用快取
tool_instance = custom_cache_tool
result1 = tool_instance("query")  # 執行
result2 = tool_instance("query")  # 使用快取
```

## 常用內建工具

### SerperDevTool - Web 搜索

```python
from crewai_tools import SerperDevTool

search_tool = SerperDevTool()
# 需要設定 SERPER_API_KEY 環境變數
```

### FileReadTool - 讀取文件

```python
from crewai_tools import FileReadTool

file_tool = FileReadTool(
    file_path='path/to/file.txt'
)
```

### DirectoryReadTool - 讀取目錄

```python
from crewai_tools import DirectoryReadTool

dir_tool = DirectoryReadTool(
    directory='path/to/directory'
)
```

### WebsiteSearchTool - 網站搜索

```python
from crewai_tools import WebsiteSearchTool

website_tool = WebsiteSearchTool(
    website='https://example.com'
)
```

### ScrapeWebsiteTool - 網站爬取

```python
from crewai_tools import ScrapeWebsiteTool

scrape_tool = ScrapeWebsiteTool(
    website_url='https://example.com'
)
```

## 將工具附加到 Agent

### 方法 1：Agent 級別工具

```python
from crewai import Agent
from crewai_tools import SerperDevTool, FileReadTool

agent = Agent(
    role="Researcher",
    goal="Research topics",
    tools=[SerperDevTool(), FileReadTool()]
)
```

### 方法 2：Task 級別工具

```python
task = Task(
    description="Research AI trends",
    agent=researcher,
    tools=[SerperDevTool()]  # 僅此任務使用
)
```

## 工具錯誤處理

```python
from crewai.tools import BaseTool

class SafeTool(BaseTool):
    name: str = "Safe Tool"
    description: str = "Tool with error handling"

    def _run(self, input_data: str) -> str:
        try:
            result = risky_operation(input_data)
            return result
        except Exception as e:
            return f"Error occurred: {str(e)}"
```

## 工具最佳實踐

1. **清晰的描述** - Tool 的 `description` 會被 agent 用來決定何時使用
2. **明確的輸入 schema** - 使用 Pydantic 模型定義輸入
3. **錯誤處理** - 妥善處理異常情況
4. **適當的工具粒度** - 每個工具專注於單一職責
5. **文檔字串** - 提供詳細的 docstring 說明用法

## 集成外部 API

```python
import requests
from crewai.tools import tool

@tool("Weather Tool")
def get_weather(city: str) -> str:
    """Get weather information for a city."""
    api_key = os.getenv("WEATHER_API_KEY")
    response = requests.get(
        f"https://api.weather.com/v1/current?city={city}&key={api_key}"
    )
    return response.json()
```

## 工具與 Knowledge Sources

CrewAI 也支援 Knowledge Sources 作為另一種為 agent 提供資訊的方式：

```python
from crewai import Agent
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

content = "Important company information..."
string_source = StringKnowledgeSource(
    content=content,
    metadata={"source": "company_docs"}
)

agent = Agent(
    role="Assistant",
    knowledge_sources=[string_source]
)
```

Knowledge sources 與 tools 的區別：
- **Tools** - Agent 主動調用執行操作
- **Knowledge Sources** - 被動提供背景資訊給 agent
