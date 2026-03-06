#!/usr/bin/env python
"""
CrewAI Note Research Team - 主程式入口

使用方式:
    python src/note_research_team/main.py
"""

import os
import sys

# 將 src 目錄加入 Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
from note_research_team.crew import NoteResearchTeamCrew


def main():
    """主函數"""
    # 載入環境變數
    load_dotenv()
    
    # 驗證必要的環境變數
    required_env_vars = [
        'GEMINI_API_KEY',
        'SERPER_API_KEY',
        'NOTION_API_KEY',
        'NOTION_PARENT_PAGE_ID'
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        print("❌ 錯誤：缺少必要的環境變數")
        print(f"   請在 .env 文件中設定：{', '.join(missing_vars)}")
        print("\n   參考 .env.example 文件或查看 API 設定指南")
        sys.exit(1)
    
    print("✅ 環境變數已載入")
    print("\n" + "="*60)
    print("CrewAI 筆記研究團隊")
    print("="*60)
    
    # 獲取使用者輸入的議題
    print("\n請輸入要研究的議題：")
    topic = input("> ").strip()
    
    if not topic:
        print("❌ 錯誤：議題不能為空")
        sys.exit(1)
    
    print(f"\n🎯 開始研究議題：「{topic}」")
    print("="*60)
    
    # 創建並執行 crew
    try:
        inputs = {'topic': topic}
        result = NoteResearchTeamCrew().crew().kickoff(inputs=inputs)
        
        print("\n" + "="*60)
        print("✅ 任務完成！")
        print("="*60)
        print("\n最終結果：")
        print(result)
        
    except Exception as e:
        print(f"\n❌ 執行過程中發生錯誤：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
