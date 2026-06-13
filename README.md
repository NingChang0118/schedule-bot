# Schedule Bot v1.5.0 Beta

Status:
🧪 Closed Beta Testing

> 為 Discord 車隊打造的智慧排班管理與營運系統

Schedule Bot 是一套專為 Discord 車隊社群設計的排班管理機器人。

從建立班表、報班、候補管理、自動遞補、自動招募、自動提醒，到 S6 系統、資料同步與車隊營運管理，全部整合於同一套系統中。

---

# 📖 專案背景

傳統車隊管理通常依賴試算表、人工作業與管理員協調。

常見問題：

* 排班資訊分散
* 候補順位難以管理
* 臨時砍班需人工遞補
* 發車前缺額無法即時補齊
* 時數統計耗時
* 班表更新不即時

Schedule Bot 的目標就是將上述流程自動化。

---

# ✨ 核心功能

## 📅 班表管理

* 建立班表
* 刪除班表
* 強制刪除班表
* 查看班表
* 班表列表
* 重建班表
* 班表圖片同步更新

---

## 🚗 推車手系統

支援：

* 推車資料登記
* 推車手報班
* 推車手砍班
* 倍率管理
* 綜合力管理

資料內容：

* Discord ID
* 名稱
* 倍率
* 綜合力

---

## 🏃 跑者系統

支援：

* 跑者資料登記
* 跑者報班
* 跑者砍班
* 車種登記
* 綜合力管理

資料內容：

* Discord ID
* 名稱
* 綜合力
* 車種

---

## 🟢 S6 系統

支援：

* S6 資料登記
* S6 報班
* S6 砍班
* S6 候選人判定
* S6 自動提醒

資料內容：

* Discord ID
* 名稱
* 倍率
* 綜合力

---

## 👤 Profile Sync

資料更新後自動同步：

* 名稱同步
* 倍率同步
* 綜合同步
* 候補重新排序

---

## 👥 共跑系統

支援：

* 1 跑者 + 4 推車
* 2 跑者 + 3 推車
* 3 跑者 + 2 推車
* 4 跑者 + 1 推車
* 5 跑者

系統自動重新平衡正式班與候補順位。

---

## 📋 候補管理

* 候補排隊
* 候補順位保存
* 候補查詢
* 候補自動排序

---

## 🔄 自動遞補

當正式班出現空缺：

1. 偵測空缺
2. 提升候補第一順位
3. 更新班表
4. 發送轉正通知

---

## 📈 倍率競爭機制

推車手依倍率排序。

系統自動選出最佳正式班組合。

---

## 🔀 雙身份支援

同一玩家可同時擁有：

* 推車手身份
* 跑者身份

系統透過：

```text
(user_id, type)
```

進行身份管理。

---

## 🚨 緊急招募系統

### 一般缺額招募

* 整天缺額招募
* Discord 身分組通知
* 缺額人數計算

### 發車前 15 分鐘緊急招募

觸發條件：

* 已有跑者
* 正式位未滿
* 發車前 15 分鐘

系統自動發送招募通知。

---

## 🚗 上車提醒系統

發車前 5 分鐘：

* 正式班通知
* 候補第一順位通知
* 多車頻道支援
* 防重複提醒

---

## 🟢 S6 Reminder System

系統自動：

* 計算最高綜合跑者
* 篩選符合資格推車手
* 發送提醒通知
* 提供一鍵登記按鈕

支援：

* 防重複提醒
* S6 自動驗證
* 跑者砍班重新檢查
* S6 砍班重新檢查

---

# 📋 班表介面

班表欄位：

* 時間
* 1
* 2
* 3
* 4
* 5
* 候補
* S6
* 車種

顏色：

* 正式位：白色
* 候補：橘色
* S6：綠色

時間格式：

```text
00-01
01-02
23-24
```

---

# ⏱️ 時數統計系統

支援：

### 個人當期時數

顯示：

* 推車時數
* 跑者時數
* 結算時數

### 個人歷史時數

顯示：

* 推車時數
* 跑者時數
* 結算時數

### 全員當期統計

顯示：

* 跑者時數排行
* 推車時數排行

計算方式：

```text
推車時數 - 跑者時數 = 結算時數
```

---

# 🏗️ 系統架構

## Cog 架構

```text
cogs
├─ admin_cog.py
├─ booking_cog.py
├─ cancel_cog.py
├─ profile_cog.py
├─ query_cog.py
├─ recruit_cog.py
├─ reminder_cog.py
└─ test_cog.py
```

## Core Services

```text
core
├─ backup_service.py
├─ boarding_reminder_service.py
├─ discord_message_service.py
├─ emergency_recruit_service.py
├─ models.py
├─ my_schedule_service.py
├─ profile_sync_service.py
├─ rebalance_service.py
├─ recruit_service.py
├─ reminder_scan_service.py
├─ renderer.py
├─ row_service.py
├─ runner_storage.py
├─ pusher_storage.py
├─ s6_pusher_storage.py
├─ s6_reminder_service.py
├─ s6_reminder_view.py
├─ schedule_edit_service.py
├─ schedule_service.py
├─ slot_service.py
├─ slot_utils.py
├─ stats_service.py
└─ storage.py
```

---

# 🛠️ 技術棧

### 開發語言

* Python 3.13

### 核心套件

* discord.py 2.x
* Pillow
* python-dotenv

### 資料儲存

* schedules.json
* pushers.json
* runners.json
* s6_pushers.json

### 圖片生成

* Pillow Render Engine

---

# 🚀 Version 1.5.0 Beta

## 新增

* 跑者車種系統
* S6 報班系統
* S6 砍班系統
* S6 Reminder View
* 登記資料查詢功能
* Profile Sync

## 重構

* ScheduleCog 完全拆分
* BookingCog
* CancelCog
* ProfileCog
* QueryCog
* RecruitCog
* ReminderCog

## 優化

* 跑者報班邏輯重構
* 跑者砍班邏輯重構
* S6 自動重新檢查
* 班表顯示優化
* Reminder Workflow 重構

---

# 📅 開發歷程

### 2026/06/10

* 專案啟動
* Schedule Bot 開發開始

### 2026/06/11

* v1.0.0
* v1.3.0

### 2026/06/13

* v1.4.0
* Profile System
* S6 Reminder System

### 2026/06/14

* v1.5.0 Beta
* Cog 模組化完成
* S6 Workflow 完成
* 跑者車種系統
* 跑者砍班重構

---

# 🔮 未來規劃

## v1.5.1

* 系統穩定性檢查
* Code Review
* Bug Fix
* 封閉測試驗證

## v1.6.0

* 排行榜系統優化
* 車隊營運統計
* 管理查詢工具

## v2.0

* SQLite 資料庫
* Web Dashboard
* API 支援
* 管理面板

---

# 📜 License

MIT License
