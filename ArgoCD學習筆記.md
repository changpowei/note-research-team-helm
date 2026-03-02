# Argo CD 學習實戰指南

這份指南將帶你一步步操作 Argo CD，從安裝、登入到體驗 GitOps 的核心威力：**自動修復（Self-Healing）**。

## 階段 0：安裝與啟動 (若是全新環境)

如果你還沒安裝 Argo CD，請在 `ops-tool` container 內執行以下指令：

```bash
# 1. 建立 namespace
kubectl create namespace argocd

# 2. 安裝 Argo CD (使用官方 manifest)
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# 3. 確認 Pods 都有跑起來 (Running)
kubectl get pods -n argocd
```

---

## 階段 1：初次登入與訪問

Argo CD 安裝好後，預設會有一個 `admin` 帳號。

### 1. 啟動 Port Forwarding
Argo CD 服務跑在 Cluster 內，外部無法直接訪問。你需要開一個通道：

```bash
# 在 ops-tool 內執行 (這會佔用一個終端視窗)
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

> 💡 **提示**：保持這個指令執行，不要關閉它。你可以開一個新的終端視窗來做後續操作。

### 2. 取得 admin 密碼
開啟新的終端，進入 `ops-tool` 或在 host 端 (如果有 kubectl)：

```bash
# 取得初始密碼（base64 解碼）
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
```

### 3. 登入 UI
1. 回到瀏覽器開啟 [https://localhost:8080](https://localhost:8080)
   - (因為是自簽憑證，瀏覽器會警告不安全，請選擇繼續前往)
2. **Username**: `admin`
3. **Password**: 上面指令顯示的字串
4. 登入後應該會看到 "No applications yet" 的空畫面。

---

## 階段 2：準備 Git 倉庫（GitOps 的核心）

**Argo CD 需要監控一個 Git 倉庫**。

### Q: 我要在哪裡執行 git 指令？ Container 還是 Host？
**A: 建議在 Host 端！**
- 你的程式碼編輯、修改通常都在 Host 端。
- Host 端通常已經設定好 GitHub SSH Key 或帳號密碼，推送比較方便。

### Q: 我的 Git Repository 應該包含什麼？
**A: 包含 `helm/` 目錄即可（這是 GitOps 的重點）**

雖然你的應用程式碼（app.py 等）已經打包在 Docker Image (`note-research-team:v1.1`) 中，並且該 Image 已經在 `k8s-lab` 中，**但 Argo CD 不需要知道 Image 的內容，它只需要知道「如何部署」這個 Image**。

「如何部署」的定義就在 **Helm Charts** 中。

所以，你的 Git Repository 結構應該長這樣（Host 端 `/home/c95cpw/antigravity/note-research-team-k8s`）：

```
.
├── helm/                <-- Argo CD 重點關注這裡！
│   ├── Chart.yaml       <-- 描述 Chart 資訊
│   ├── values.yaml      <-- 定義 image tag (v1.1) 和環境變數
│   └── templates/       <-- K8s 資源模板
└── ... (其他 app.py 等原始碼，雖然 Argo CD 不用，但通常會一起版控)
```

**GitOps 流程是：**
1. 你修改 `app.py` -> Build 新 Image (`v1.2`) -> Push Image
2. 你修改 `helm/values.yaml` (把 tag 改成 `v1.2`) -> **Git Commit & Push**
3. **Argo CD 偵測到 Git 變更** -> 自動更新 K8s 中的 Deployment

### Q: 我的 Git Repository 應該在哪裡？
**A: 根據你的環境，應該是 `/home/c95cpw/k8s/ops-tool/note-research-team-helm`**

我們確認過該目錄下有：
- `Chart.yaml`
- `values.yaml`
- `templates/`
- `.env` (注意！機敏檔案不要上傳)
- `helm-deploy.sh`

這就是標準的 Helm Chart 結構。

### 1. 初始化 Git 並推送 (在 Host 端執行)

因為這個目錄可能還不是 Git Repository，我們來初始化它：

```bash
# 1. 進入目錄
cd /home/c95cpw/k8s/ops-tool/note-research-team-helm

# 2. 初始化 Git
git init

# 3. 建立 .gitignore (非常重要！忽略 .env)
echo ".env" > .gitignore

# 4. 加入檔案並提交
git add .
git commit -m "feat: initial helm charts for argocd"

# 5. 推送到 GitHub (請先在 GitHub 建立一個空專案)
# git remote add origin <你的-repo-url>
# git branch -M main
# git push -u origin main
```

---

---

## 階段 2.5：緊急修復！機敏檔案外洩處理

> 🚨 **注意**：如果你不小心將 `.env` 或 `tls.key` 推送到 GitHub，請立即執行以下步驟！

### 1. 更新 .gitignore
確保 `.gitignore` 包含以下內容：

```gitignore
.env
.env.*
! .env.example
tls.key
tls.crt
*.pem
```

### 2. 從 Git 移除檔案（但保留本地檔案）
在你的 Host 端專案目錄執行：

```bash
# 移除追蹤（不會刪除本地檔案）
git rm --cached .env
git rm --cached tls.key tls.crt

# 提交變更
git commit -m "fix: remove sensitive files from git"
git push origin main
```

> **資安提醒**：如果你的 Repo 是公開的，這些 Key 可能已經洩漏。建議 rotate (更換) 你的 API Keys。

---

## 階段 3：建立第一個 Application (UI 操作教學)

現在讓 Argo CD 接管你的 `research-team` 部署。請跟著以下步驟操作：

### 1. 登入 Argo CD
- 網址：[https://localhost:8080](https://localhost:8080)
- 帳號：`admin`
- 密碼：(使用階段 1 取得的密碼)


### 2. 建立新應用
點擊左上角的 **+ NEW APP** 按鈕。


### 3. 填寫 Application 資訊
請依照下圖填寫資訊：


**詳細設定值**：

**GENERAL（基本資訊）**
- **Application Name**: `research-team`
- **Project Name**: `default`
- **Sync Policy**: `Manual`
- **Sync Options**: 勾選 `Auto-Create Namespace`

**SOURCE（來源 - 你的 Git）**
- **Repository URL**: `你的 GitHub Repo URL` (例如 https://github.com/your/repo.git)
- **Revision**: `HEAD`
- **Path**: `.` (因為我們是在 helm 專用 repo 的根目錄)

**DESTINATION（目標 - 你的 K8s）**
- **Cluster URL**: `https://kubernetes.default.svc` 

> **Q: 這個網址是什麼？**
> 這不是外部網址，而是 K8s 內部的 DNS 名稱。因為 Argo CD 本身就跑在同一個 K8s Cluster 裡面，所以它可以用這個內部網址直接跟 K8s API Server 溝通。
> 如果你只有一個 Cluster（像現在），選單通常只會有這一個選項，選它就對了。

- **Namespace**: `default`

### 4. 點擊 CREATE
點擊上方的 **CREATE** 按鈕。
- 如果成功：會看到一個新的 Application 卡片
- 如果失敗（如下圖）：通常是 Git Repo URL 錯誤或無法存取


> **故障排除**：如果遇到 "Repository not found"，請確認你的 GitHub Repo 是 Public 的，或者需要在 Argo CD Settings > Repositories 設定驗證資訊。

---

## 階段 4：觀察與同步 (Sync)

建立後，你應該會看到一個卡片 `research-team`。
點擊進入後，你會看到類似這樣的資源拓撲圖：



### 畫面元件解析：這是什麼？

1.  **Application (research-team)**: 最左邊的圖示。這是 Argo CD 管理的應用程式單元。它包含了整個 Helm Chart 的定義。
    - **狀態 (Synced/Healthy)**: 綠色愛心代表健康，綠色勾勾代表同步。
2.  **Service (research-team)**: 負責內網負載平衡，將流量分發給 Pods。
3.  **Deployment (note-research-team)**: 管理 Pod 的副本數量和版本更新。這是我們等一下要「惡搞」的對象。
4.  **ReplicaSet**: Deployment 創造出來的實體，負責確保 Pod 數量正確。
5.  **Pod**: 最右邊的小方塊，也就是實際運行的容器。目前有一個。
6.  **Ingress (research-team)**: 負責外部訪問入口。
7.  **Secret (research-tls)**: 我們手動建立的 TLS 憑證。

> **為什麼有紅色的？**
> 如果你是剛建立，狀態可能是 **Missing** (黃色) 或 **OutOfSync**。
> 點擊上方的 **SYNC** 按鈕 -> **SYNCHRONIZE**，讓 Argo CD 把 Git 的定義套用到 K8s，它們就會變綠色了。

---

## 階段 5：實作 Drift（配置漂移與修復）

這是 GitOps 最精彩的部分。我們來模擬「有人手動亂改 K8s 設定」，看 Argo CD 如何發現並修復。

### 1. 製造 Drift (手動惡作劇)
我們不用 Git 改，而是直接去 K8s 改壞它。
在 `ops-tool` 執行：

```bash
# 手動把 Pod 數量改成 3 個 (原本可能是 1 個)
kubectl scale deployment note-research-team --replicas=3
```

**如何驗證真的改壞了？**
在 Argo CD 還沒發現之前，你可以在 `ops-tool` 快速檢查：

```bash
kubectl get pods
# 你應該會看到 3 個 Pod 正在 Running 或 Creating
# 這證明你的手動修改已經生效了！
```

### 2. 觀察 Argo CD
1. 回到 Argo CD UI，點擊 **REFRESH** (雖然它會定期檢查，但我們手動加速)。
2. 你會看到狀態變成了 **OutOfSync** (黃色)。
3. 點擊 **APP DIFF** (上方按鈕)，它會告訴你：
   - Git 說： replicas: 1
   - Live (K8s) 說： replicas: 3
    *Argo CD 偵測到有人偷改設定！*

### 3. 自動修復 (Sync)
GitOps 的原則是「以 Git 為準」。
1. 點擊 **SYNC**。
2. 觀察 Pod 數量，它會被 Argo CD 強制殺回 1 個。
3. 狀態回到 **Synced** (綠色)。

這就是 GitOps 的威力：**防止配置漂移，確保環境永遠與 Git 一致**。
