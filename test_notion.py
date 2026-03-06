#!/usr/bin/env python3
"""
Notion API 診斷工具

測試 Notion API 連接和權限
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_notion_connection():
    """測試 Notion API 連接"""
    
    api_key = os.getenv("NOTION_API_KEY")
    parent_page_id = os.getenv("NOTION_PARENT_PAGE_ID")
    
    print("="*60)
    print("🔍 Notion API 診斷工具")
    print("="*60)
    
    # 檢查環境變數
    print("\n1️⃣  檢查環境變數...")
    if not api_key:
        print("❌ NOTION_API_KEY 未設定！")
        return
    if not parent_page_id:
        print("❌ NOTION_PARENT_PAGE_ID 未設定！")
        return
    
    print(f"✅ NOTION_API_KEY: {api_key[:10]}... (長度: {len(api_key)})")
    print(f"✅ NOTION_PARENT_PAGE_ID: {parent_page_id}")
    
    # 測試 API 連接
    print("\n2️⃣  測試 API 連接...")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28"
    }
    
    try:
        # 嘗試讀取父頁面
        response = requests.get(
            f"https://api.notion.com/v1/pages/{parent_page_id}",
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            page_data = response.json()
            print(f"✅ 成功連接到 Notion！")
            print(f"   頁面標題: {page_data.get('properties', {}).get('title', {})}")
        elif response.status_code == 404:
            print(f"❌ 找不到頁面！")
            print(f"   可能原因：")
            print(f"   1. Page ID 不正確")
            print(f"   2. 頁面未分享給 Integration")
            print(f"\n   請確認：")
            print(f"   - 打開 Notion 頁面")
            print(f"   - 點擊右上角「...」")
            print(f"   - 選擇「Connect to」")
            print(f"   - 選擇你的 Integration")
        elif response.status_code == 401:
            print(f"❌ API Key 無效！")
            print(f"   請檢查 NOTION_API_KEY 是否正確")
        else:
            print(f"❌ API 錯誤 ({response.status_code})")
            print(f"   訊息: {response.text}")
    
    except requests.exceptions.Timeout:
        print("❌ 連接超時")
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
    
    # 測試創建頁面
    print("\n3️⃣  測試創建測試頁面...")
    test_page_data = {
        "parent": {"page_id": parent_page_id},
        "properties": {
            "title": {
                "title": [
                    {
                        "text": {
                            "content": "🧪 Notion API 測試頁面"
                        }
                    }
                ]
            }
        },
        "children": [
            {
                "type": "table_of_contents",
                "table_of_contents": {"color": "default"}
            },
            {
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "測試標題"}}]
                }
            },
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {"type": "text", "text": {"content": "這是一個"}},
                        {"type": "text", "text": {"content": "粗體測試"}, "annotations": {"bold": True}},
                        {"type": "text", "text": {"content": "和"}},
                        {
                            "type": "text",
                            "text": {
                                "content": "超連結測試",
                                "link": {"url": "https://www.google.com"}
                            }
                        }
                    ]
                }
            }
        ]
    }
    
    try:
        response = requests.post(
            "https://api.notion.com/v1/pages",
            headers=headers,
            json=test_page_data,
            timeout=30
        )
        
        if response.status_code == 200:
            page_url = response.json().get("url", "")
            print(f"✅ 測試頁面創建成功！")
            print(f"   URL: {page_url}")
            print(f"\n   請檢查頁面是否包含：")
            print(f"   - Table of Contents")
            print(f"   - 粗體文字")
            print(f"   - 超連結")
        else:
            print(f"❌ 創建失敗 ({response.status_code})")
            error_data = response.json()
            print(f"   錯誤: {error_data.get('message', response.text)}")
    
    except Exception as e:
        print(f"❌ 錯誤: {str(e)}")
    
    print("\n" + "="*60)
    print("診斷完成")
    print("="*60)


if __name__ == "__main__":
    test_notion_connection()
