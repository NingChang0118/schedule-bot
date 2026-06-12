# Schedule Bot v1.4.0

Status:
✅ Production Ready

> 為 Discord 車隊打造的智慧排班管理系統

Schedule Bot 是一套專為 Discord 車隊社群設計的排班管理機器人。

從建立班表、報班、候補管理，到自動遞補、自動招募、自動提醒、S6 提醒與時數統計，全部整合於同一套系統中，讓排班流程不再依賴人工整理與手動計算。

---

# 📖 專案背景

在傳統車隊管理模式下，排班往往仰賴試算表、人工作業與管理員手動協調。

常見問題包括：

* 排班資料分散
* 候補順位難以追蹤
* 臨時砍班需要人工遞補
* 發車前缺額無法即時補齊
* 時數統計耗費大量時間
* 班表資訊更新不即時

Schedule Bot 的目標就是解決這些問題。

---

# ✨ 核心功能

## 📅 班表管理系統

* 建立班表
* 刪除班表
* 強制刪除班表
* 查看班表
* 班表列表
* 重建班表
* 班表圖片同步更新

---

## 🚗 推車手系統

* 推車資料登記
* 推車手報班
* 推車倍率管理
* 推車綜合力管理

---

## 🏃 跑者系統

* 跑者資料登記
* 跑者報班
* 跑者綜合力管理
* 共跑模式

---

## 👤 Profile System

### 推車手資料

* Discord ID
* 名稱
* 倍率
* 綜合力

### 跑者資料

* Discord ID
* 名稱
* 綜合力

支援：

* JSON 永久保存
* 雙身份管理
* 資料同步更新

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

## 📋 候補管理系統

* 候補排隊
* 候補順位保存
* 候補查詢
* 候補自動排序

---

## 🔄 自動遞補系統

當正式班成員砍班時：

1. 偵測空缺
2. 提升候補第一順位
3. 更新班表
4. 發送轉正通知

全程無需管理員介入。

---

## 📈 倍率競爭機制

推車手依倍率排序。

系統自動選出最高倍率組合作為正式班。

---

## 🔀 雙身份支援

同一玩家可同時擁有：

* 推車手身份
* 跑者身份

系統透過：

(user_id, type)

進行身份管理。

---

## 🚨 缺額招募系統

* 整天缺額招募
* Discord 身分組通知
* 缺額人數計算

---

## 🚨 發車前 15 分鐘緊急招募系統

觸發條件：

* 發車前 15 分鐘
* 已有跑者
* 人數未滿 5 人

自動發送緊急招募通知。

---

## 🚗 發車前 5 分鐘上車提醒系統

支援：

* 正式班通知
* 候補第一順位通知
* 防重複提醒
* 多車頻道對應
* 跨年時間判定

---

## 🚗 S6 Priority Reminder System

支援 S6 推車手專用提醒。

功能：

* S6 推車資料登錄
* S6 名單管理
* 發車前 5 分鐘提醒
* 防重複提醒

資料儲存：

* s6_pushers.json

---

## ⏱️ 時數統計系統

支援：

* 個人當期時數
* 個人歷史時數
* 全員當期時數統計

計算方式：

推車時數 - 跑者時數 = 結算時數

---

# 🏗️ 系統架構

## 專案結構

```text
schedule_bot
│
├─ cogs
│   ├─ schedule_cog.py
│   ├─ admin_cog.py
│
├─ core
│   ├─ schedule_service.py
│   ├─ schedule_edit_service.py
│   ├─ slot_service.py
│   ├─ stats_service.py
│   ├─ recruit_service.py
│   ├─ emergency_recruit_service.py
│   ├─ boarding_reminder_service.py
│   ├─ s6_reminder_service.py
│   ├─ pusher_storage.py
│   ├─ runner_storage.py
│   └─ ...
│
└─ data
```

## 技術棧

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

# 🎯 專案成果

## 已完成功能

### 班表系統

* ✅ 建立班表
* ✅ 刪除班表
* ✅ 強制刪除班表
* ✅ 查看班表
* ✅ 班表列表
* ✅ 重建班表

### 報班系統

* ✅ 推車手報班
* ✅ 跑者報班
* ✅ 共跑系統
* ✅ 雙身份支援
* ✅ 推車手砍班
* ✅ 跑者砍班

### 候補系統

* ✅ 候補排隊
* ✅ 候補查詢
* ✅ 自動遞補
* ✅ 候補轉正通知

### 招募系統

* ✅ 缺額招募
* ✅ 緊急招募
* ✅ Discord 身分組通知

### 提醒系統

* ✅ 發車前 5 分鐘提醒
* ✅ 候補第一順位提醒
* ✅ S6 提醒系統
* ✅ 防重複提醒

### 統計系統

* ✅ 個人當期時數
* ✅ 個人歷史時數
* ✅ 全員時數統計

---

# 🚀 版本資訊

## Schedule Bot v1.4.0

### 新增功能

* 推車手綜合值系統
* 跑者綜合值系統
* Profile System
* S6 推車資料系統
* S6 專用提醒系統
* 推車手砍班指令獨立化
* 跑者砍班指令獨立化

### 架構升級

* Service Layer Architecture
* AdminCog 模組化
* Storage Layer 拆分
* Reminder Service 拆分
* Schedule Service 拆分

### 系統規模

* 20+ Python Modules
* Discord Slash Command 架構
* 多背景任務系統
* Pillow Render Engine
* JSON 永久儲存架構

### 狀態

✅ 正式營運中

---

# 📅 開發歷程

### 2026/06/10

* 專案啟動
* Stellar Bot 完成
* Schedule Bot 開發開始

### 2026/06/11

* Schedule Bot v1.0.0
* Schedule Bot v1.3.0

### 2026/06/13

* Schedule Bot v1.4.0
* Architecture Refactor
* Profile System
* S6 Reminder System

---

# 🔮 未來開發規劃

## v1.5

* Discord Button 報班
* Discord Modal 報班
* 操作體驗優化

## v2.0

* SQLite 資料庫
* Web Dashboard
* API 支援
* 管理面板

---

# 📜 License

MIT License
