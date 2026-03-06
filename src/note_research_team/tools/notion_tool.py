"""
Notion integration tool for CrewAI

使用 Notion MCP server 創建和發佈筆記
"""

import os
import re
from typing import Type
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class NotionToolInput(BaseModel):
    """Input schema for NotionTool."""
    title: str = Field(..., description="筆記標題")
    content: str = Field(..., description="筆記內容（Markdown 格式）")


class NotionTool(BaseTool):
    name: str = "Notion 發佈工具"
    description: str = "將 Markdown 格式的筆記發佈到 Notion 的「CrewAI筆記」頁面"
    args_schema: Type[BaseModel] = NotionToolInput

    def _run(self, title: str, content: str) -> str:
        """
        將筆記發佈到 Notion
        
        Args:
            title: 筆記標題
            content: Markdown 格式的筆記內容
            
        Returns:
            成功訊息和 Notion 頁面連結
        """
        try:
            import requests
            
            # 從環境變數獲取配置
            api_key = os.getenv("NOTION_API_KEY")
            parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
            
            if not api_key:
                return "❌ 錯誤：未設定 NOTION_API_KEY 環境變數"
            if not parent_page_id:
                return "❌ 錯誤：未設定 NOTION_PARENT_PAGE_ID 環境變數"
            
            # Notion API 設定
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28"
            }
            
            # 將 markdown 轉換為 Notion blocks
            blocks = self._markdown_to_notion_blocks(content)
            
            # 在開頭插入 Table of Contents
            toc_block = {
                "type": "table_of_contents",
                "table_of_contents": {
                    "color": "default"
                }
            }
            
            # 創建頁面
            page_data = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [
                            {
                                "text": {
                                    "content": title
                                }
                            }
                        ]
                    }
                },
                # 第一個 block 是 ToC，後面是內容（限制100個）
                "children": [toc_block] + blocks[:99]  # ToC + 99 blocks = 100 total
            }
            
            # 調用 Notion API
            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=page_data,
                timeout=30
            )
            
            if response.status_code == 200:
                page_url = response.json().get("url", "")
                print(f"\n[DEBUG] Notion 頁面創建成功！")
                print(f"[DEBUG] URL: {page_url}\n")
                
                # 清晰的成功訊息，URL 單獨一行
                return (
                    f"✅ 成功發佈筆記「{title}」到 Notion！\n\n"
                    f"頁面連結：{page_url}\n"
                )
            else:
                error_msg = response.json().get("message", response.text)
                return f"❌ Notion API 錯誤 ({response.status_code})：{error_msg}\n\n請檢查：\n1. NOTION_API_KEY 是否正確\n2. 「CrewAI筆記」頁面是否已 Share 給你的 integration\n3. NOTION_PARENT_PAGE_ID 是否正確"
            
        except requests.exceptions.Timeout:
            return "❌ Notion API 請求超時，請檢查網路連線"
        except Exception as e:
            return f"❌ 發佈失敗：{str(e)}"
    
    def _markdown_to_notion_blocks(self, markdown: str) -> list:
        """
        將 Markdown 轉換為 Notion blocks 格式
        支援：標題、粗體、超連結、列表、段落
        
        Args:
            markdown: Markdown 文本
            
        Returns:
            Notion blocks 列表
        """
        blocks = []
        lines = markdown.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].rstrip()
            
            # 跳過空行
            if not line.strip():
                i += 1
                continue
            
            # 檢查標題
            if line.startswith('# '):
                blocks.append(self._create_heading(line[2:], 1))
            elif line.startswith('## '):
                blocks.append(self._create_heading(line[3:], 2))
            elif line.startswith('### '):
                blocks.append(self._create_heading(line[4:], 3))
            # 檢查列表
            elif line.strip().startswith('- ') or line.strip().startswith('* '):
                blocks.append(self._create_list_item(line.strip()[2:]))
            elif line.strip().startswith('1. ') or line.strip().startswith('2. '):
                # 數字列表（Notion 中也用 bulleted_list_item）
                content = line.strip()[3:]
                blocks.append(self._create_list_item(content))
            # 普通段落
            else:
                blocks.append(self._create_paragraph(line))
            
            i += 1
        
        return blocks
    
    def _create_heading(self, text: str, level: int) -> dict:
        """創建標題 block"""
        heading_type = f"heading_{level}"
        return {
            "type": heading_type,
            heading_type: {
                "rich_text": self._parse_rich_text(text)
            }
        }
    
    def _create_paragraph(self, text: str) -> dict:
        """創建段落 block"""
        return {
            "type": "paragraph",
            "paragraph": {
                "rich_text": self._parse_rich_text(text)
            }
        }
    
    def _create_list_item(self, text: str) -> dict:
        """創建列表項 block"""
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {
                "rich_text": self._parse_rich_text(text)
            }
        }
    
    def _parse_rich_text(self, text: str) -> list:
        """
        解析文本中的格式（粗體、超連結）
        支援：**粗體** 和 [文字](URL)
        
        Returns:
            Notion rich_text 格式的列表
        """
        import re
        
        rich_text = []
        current_pos = 0
        
        # 同時匹配粗體和超連結
        # 粗體：**text**
        # 超連結：[text](url)
        pattern = r'\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)'
        
        for match in re.finditer(pattern, text):
            # 添加匹配前的普通文本
            if match.start() > current_pos:
                plain_text = text[current_pos:match.start()]
                if plain_text:
                    rich_text.append({
                        "type": "text",
                        "text": {"content": plain_text}
                    })
            
            # 處理粗體
            if match.group(1):
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(1)},
                    "annotations": {"bold": True}
                })
            # 處理超連結
            elif match.group(2) and match.group(3):
                url = match.group(3).strip()
                
                # 驗證 URL 格式（必須是 http:// 或 https://）
                if url.startswith('http://') or url.startswith('https://'):
                    rich_text.append({
                        "type": "text",
                        "text": {
                            "content": match.group(2),
                            "link": {"url": url}
                        }
                    })
                else:
                    # 如果不是有效 URL，顯示為純文本
                    rich_text.append({
                        "type": "text",
                        "text": {"content": f"[{match.group(2)}]({url})"}
                    })
            
            current_pos = match.end()
        
        # 添加剩餘的普通文本
        if current_pos < len(text):
            remaining_text = text[current_pos:]
            if remaining_text:
                rich_text.append({
                    "type": "text",
                    "text": {"content": remaining_text}
                })
        
        # 如果沒有任何格式，返回純文本
        if not rich_text:
            rich_text = [{"type": "text", "text": {"content": text}}]
        
        return rich_text

