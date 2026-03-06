"""
CrewAI Note Research Team

Crew 編排邏輯
"""

import os
from typing import List
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import SerperDevTool
from .tools import NotionTool
import yaml


@CrewBase
class NoteResearchTeamCrew():
    """Note Research Team crew"""
    
    def __init__(self):
        # 載入配置文件
        config_dir = os.path.join(os.path.dirname(__file__), 'config')
        
        with open(os.path.join(config_dir, 'agents.yaml'), 'r', encoding='utf-8') as f:
            self.agents_config = yaml.safe_load(f)
        
        with open(os.path.join(config_dir, 'tasks.yaml'), 'r', encoding='utf-8') as f:
            self.tasks_config = yaml.safe_load(f)
    
    @agent
    def researcher(self) -> Agent:
        """資料搜查與彙整專員"""
        return Agent(
            role=self.agents_config['researcher']['role'],
            goal=self.agents_config['researcher']['goal'],
            backstory=self.agents_config['researcher']['backstory'],
            verbose=True,
            tools=[SerperDevTool()],  # 網路搜索工具
            llm=os.getenv("RESEARCHER_LLM", "gemini/gemini-2.5-flash")
        )
    
    @agent
    def note_writer(self) -> Agent:
        """筆記撰寫與發佈專員"""
        return Agent(
            role=self.agents_config['note_writer']['role'],
            goal=self.agents_config['note_writer']['goal'],
            backstory=self.agents_config['note_writer']['backstory'],
            verbose=True,
            tools=[NotionTool()],  # Notion 發佈工具
            llm=os.getenv("WRITER_LLM", "gemini/gemini-2.5-flash")
        )
    
    @task
    def research_task(self) -> Task:
        """資料搜索任務"""
        return Task(
            description=self.tasks_config['research_task']['description'],
            expected_output=self.tasks_config['research_task']['expected_output'],
            agent=self.researcher()
        )
    
    @task
    def organize_task(self) -> Task:
        """資料整理任務"""
        return Task(
            description=self.tasks_config['organize_task']['description'],
            expected_output=self.tasks_config['organize_task']['expected_output'],
            agent=self.researcher(),
            context=[self.research_task()]
        )
    
    @task
    def write_and_publish_task(self) -> Task:
        """撰寫並發佈任務"""
        return Task(
            description=self.tasks_config['write_and_publish_task']['description'],
            expected_output=self.tasks_config['write_and_publish_task']['expected_output'],
            agent=self.note_writer(),
            context=[self.organize_task()]
        )
    
    @crew
    def crew(self) -> Crew:
        """創建 Note Research Team crew"""
        return Crew(
            agents=[self.researcher(), self.note_writer()],
            tasks=[self.research_task(), self.organize_task(), self.write_and_publish_task()],
            process=Process.sequential,  # 順序執行
            verbose=True
        )
