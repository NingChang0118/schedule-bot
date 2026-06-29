# Changelog

All notable changes to this project will be documented in this file.

This changelog starts from **v1.5.10**.
Earlier development history is documented in the project's Discord update log.

## [v1.5.10] - 2026-06-28

### Added

- 新增跑者車種鎖定功能
- 新增班表刪除二次確認
- 新增刪除班表取消功能
- 新增刪除確認逾時自動失效

### Changed

- 第一位跑者決定車種，後續跑者不得修改
- 車種不同時拒絕跑者報班
- 刪除班表同步刪除 Discord 班表訊息
- 僅限指令發送者可確認或取消刪除班表

## [v1.5.11] - 2026-06-28

### Added

新增更新跑者倍率指令
新增更新跑者綜合指令
新增更新推車倍率指令
新增更新推車綜合指令
更新 Profile 後自動同步所有目前班表資料
更新 Profile 後自動同步所有已報班資料

## Changed

登記推車資料成功訊息改為公開
登記跑者資料成功訊息改為公開
登記 S6 資料成功訊息改為公開

## [v1.5.12] - 2026-06-28

### Changed

* 跑者報班車種改為選填
* 第一位填寫車種的跑者將鎖定該時段車種
* 未填寫車種不會鎖定車種
* 已鎖定車種後，後續填寫車種需與已鎖定車種一致

##　[v1.5.13] - 2026-06-30

### Added

新增推車手雙開報班功能
推車報班新增雙開倍率選填欄位
支援已報班後補報雙開

### Changed

推車班重整機制支援同一推車手雙開
推車砍班會一次取消同時段所有雙開報班