"""
Notion integration tool for CrewAI

使用 Notion API 創建和發佈筆記
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Notion API 每次建立頁面最多允許 100 個 children blocks
NOTION_MAX_CHILDREN = 100


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
            成功訊息和 Notion 頁面連結，或錯誤訊息
        """
        try:
            api_key = os.getenv("NOTION_API_KEY")
            parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")

            if not api_key:
                return "❌ 錯誤：未設定 NOTION_API_KEY 環境變數"
            if not parent_page_id:
                return "❌ 錯誤：未設定 NOTION_PARENT_PAGE_ID 環境變數"

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Notion-Version": "2022-06-28",
            }

            blocks = self._markdown_to_notion_blocks(content)

            toc_block: dict[str, Any] = {
                "type": "table_of_contents",
                "table_of_contents": {"color": "default"},
            }

            page_data: dict[str, Any] = {
                "parent": {"page_id": parent_page_id},
                "properties": {
                    "title": {
                        "title": [{"text": {"content": title}}]
                    }
                },
                # ToC 佔 1 個，內容最多 NOTION_MAX_CHILDREN - 1 個
                "children": [toc_block] + blocks[: NOTION_MAX_CHILDREN - 1],
            }

            response = requests.post(
                "https://api.notion.com/v1/pages",
                headers=headers,
                json=page_data,
                timeout=30,
            )

            if response.status_code == 200:
                page_url = response.json().get("url", "")
                logger.debug("Notion page created successfully: %s", page_url)
                return (
                    f"✅ 成功發佈筆記「{title}」到 Notion！\n\n"
                    f"頁面連結：{page_url}\n"
                )
            else:
                error_msg = response.json().get("message", response.text)
                logger.error(
                    "Notion API error %d: %s", response.status_code, error_msg
                )
                return (
                    f"❌ Notion API 錯誤 ({response.status_code})：{error_msg}\n\n"
                    f"請檢查：\n"
                    f"1. NOTION_API_KEY 是否正確\n"
                    f"2. 「CrewAI筆記」頁面是否已 Share 給你的 integration\n"
                    f"3. NOTION_PARENT_PAGE_ID 是否正確"
                )

        except requests.exceptions.Timeout:
            return "❌ Notion API 請求超時，請檢查網路連線"
        except Exception:
            logger.exception("NotionTool._run failed")
            return "❌ 發佈失敗，請查看伺服器日誌以取得詳細錯誤"

    def _markdown_to_notion_blocks(self, markdown: str) -> list[dict[str, Any]]:
        """
        將 Markdown 轉換為 Notion blocks 格式
        支援：H1/H2/H3 標題、無序列表、有序列表、粗體、超連結、段落
        """
        blocks: list[dict[str, Any]] = []
        lines = markdown.split("\n")
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            if not line.strip():
                i += 1
                continue

            stripped = line.strip()

            if line.startswith("# "):
                blocks.append(self._create_heading(line[2:], 1))
            elif line.startswith("## "):
                blocks.append(self._create_heading(line[3:], 2))
            elif line.startswith("### "):
                blocks.append(self._create_heading(line[4:], 3))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                blocks.append(self._create_bullet_item(stripped[2:]))
            elif re.match(r"^\d+\.\s", stripped):
                content = re.sub(r"^\d+\.\s", "", stripped)
                blocks.append(self._create_numbered_item(content))
            else:
                blocks.append(self._create_paragraph(line))

            i += 1

        return blocks

    def _create_heading(self, text: str, level: int) -> dict[str, Any]:
        """建立標題 block（H1/H2/H3）"""
        heading_type = f"heading_{level}"
        return {
            "type": heading_type,
            heading_type: {"rich_text": self._parse_rich_text(text)},
        }

    def _create_paragraph(self, text: str) -> dict[str, Any]:
        """建立段落 block"""
        return {
            "type": "paragraph",
            "paragraph": {"rich_text": self._parse_rich_text(text)},
        }

    def _create_bullet_item(self, text: str) -> dict[str, Any]:
        """建立無序列表項 block"""
        return {
            "type": "bulleted_list_item",
            "bulleted_list_item": {"rich_text": self._parse_rich_text(text)},
        }

    def _create_numbered_item(self, text: str) -> dict[str, Any]:
        """建立有序列表項 block"""
        return {
            "type": "numbered_list_item",
            "numbered_list_item": {"rich_text": self._parse_rich_text(text)},
        }

    def _parse_rich_text(self, text: str) -> list[dict[str, Any]]:
        """
        解析文本中的格式（粗體、超連結）
        支援：**粗體** 和 [文字](URL)

        Returns:
            Notion rich_text 格式的列表
        """
        rich_text: list[dict[str, Any]] = []
        current_pos = 0

        pattern = r"\*\*([^*]+)\*\*|\[([^\]]+)\]\(([^)]+)\)"

        for match in re.finditer(pattern, text):
            if match.start() > current_pos:
                plain_text = text[current_pos : match.start()]
                if plain_text:
                    rich_text.append({"type": "text", "text": {"content": plain_text}})

            if match.group(1):
                # 粗體
                rich_text.append({
                    "type": "text",
                    "text": {"content": match.group(1)},
                    "annotations": {"bold": True},
                })
            elif match.group(2) and match.group(3):
                url = match.group(3).strip()
                if url.startswith("http://") or url.startswith("https://"):
                    rich_text.append({
                        "type": "text",
                        "text": {
                            "content": match.group(2),
                            "link": {"url": url},
                        },
                    })
                else:
                    # 非 http(s) URL 顯示為純文字，防止 javascript: 等 URI
                    rich_text.append({
                        "type": "text",
                        "text": {"content": f"[{match.group(2)}]({url})"},
                    })

            current_pos = match.end()

        if current_pos < len(text):
            remaining = text[current_pos:]
            if remaining:
                rich_text.append({"type": "text", "text": {"content": remaining}})

        if not rich_text:
            rich_text = [{"type": "text", "text": {"content": text}}]

        return rich_text
