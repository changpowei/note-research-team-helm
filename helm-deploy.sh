#!/bin/bash

# Helm 部署腳本 - 從 .env 讀取環境變數

set -e

# 腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 載入 .env 檔案
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo "載入 .env 檔案..."
    export $(grep -v '^#' "$SCRIPT_DIR/.env" | xargs)
else
    echo "錯誤：找不到 .env 檔案"
    exit 1
fi

# 檢查必要的環境變數
if [ -z "$NOTION_API_KEY" ] || [ -z "$GEMINI_API_KEY" ] || [ -z "$SERPER_API_KEY" ]; then
    echo "錯誤：缺少必要的環境變數"
    exit 1
fi

# 部署模式：install 或 upgrade
ACTION="${1:-install}"
RELEASE_NAME="research-team"

echo "執行 helm $ACTION..."

if [ "$ACTION" = "install" ]; then
    helm install $RELEASE_NAME . \
        --set env.notionApiKey="$NOTION_API_KEY" \
        --set env.geminiApiKey="$GEMINI_API_KEY" \
        --set env.serperApiKey="$SERPER_API_KEY" \
        --set env.notionParentPageId="$NOTION_PARENT_PAGE_ID" \
        --set env.notionParentPageUrl="$NOTION_PARENT_PAGE_URL"
elif [ "$ACTION" = "upgrade" ]; then
    IMAGE_TAG="${2:-v1.0}"
    helm upgrade $RELEASE_NAME . \
        --set image.tag="$IMAGE_TAG" \
        --set env.notionApiKey="$NOTION_API_KEY" \
        --set env.geminiApiKey="$GEMINI_API_KEY" \
        --set env.serperApiKey="$SERPER_API_KEY" \
        --set env.notionParentPageId="$NOTION_PARENT_PAGE_ID" \
        --set env.notionParentPageUrl="$NOTION_PARENT_PAGE_URL"
else
    echo "用法: $0 {install|upgrade} [image_tag]"
    exit 1
fi

echo "部署完成！"
