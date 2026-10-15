# LTspice 自動批次模擬操作說明

本專案用 LTspice 執行 RC 電路的電阻 sweep，並將 `Vout` 在 5 ms 的電壓與 PASS/FAIL 結果輸出為 CSV。

## 平常如何執行

在專案根目錄開啟 PowerShell，執行：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_all.py
```

`run_all.py` 會依序：

1. 讀取 `simulation_config.json`。
2. 以 `circuit/rc_test.asc` 作為模板，生成本次專用的電路檔。
3. 對生成的電路檔執行 LTspice 批次模擬。
4. 解析本次新產生的 log，輸出 CSV。

原始 `circuit/rc_test.asc` 不會被此流程修改。每次執行會建立一個新的結果資料夾，因此不會讀取或覆寫前一輪的 log 與 CSV。

## 修改電阻與元件參數

請編輯專案根目錄的 `simulation_config.json`。例如：

```json
{
  "resistances_ohm": [750, 1500, 3300, 6800, 15000],
  "components": {
    "C1": "1u"
  }
}
```

- `resistances_ohm`：要 sweep 的 R1 電阻值，單位為 Ω；可放任意數量的正數。
- `components`：以 LTspice 元件實例名稱指定固定值。目前電路中的 `C1` 可例如設為 `"470n"`、`"1u"`、`"2.2u"`。

元件名稱要與 `rc_test.asc` 內的 `InstName` 相同。現有電路含有 `V1`、`R1`、`C1`；`R1` 由 `resistances_ohm` sweep 控制，因此不要同時在 `components` 中設定 `R1`。

範例：改成三組電阻並將電容改為 2.2 µF：

```json
{
  "resistances_ohm": [1000, 4700, 10000],
  "components": {
    "C1": "2.2u"
  }
}
```

修改 JSON 後，直接重新執行 `run_all.py` 即可，不需要手動修改 `.step` 指令或 `parse_log.py` 的 `RESISTANCES`。

## 結果在哪裡

每次成功執行後會在 `results/runs/` 建立時間戳記資料夾，例如：

```text
results/runs/20261015_152023_161176/
├─ simulation_config.json    本次實際使用的設定副本
├─ rc_test.asc               本次實際模擬的電路檔
├─ rc_test.log               LTspice 量測記錄
├─ simulation_results.csv    整理後的結果
├─ rc_test.raw               波形資料
└─ rc_test.net、*.raw、*.db  LTspice 其他輸出
```

最常查看的是 `simulation_results.csv`，其中欄位為：

- `R_ohm`：該 step 的電阻值。
- `Vout_5ms_V`：5 ms 時的輸出電壓。
- `PASS`：`Vout_5ms >= 4.5 V` 時為 `True`。

## Windows 工作排程器

開啟方式：按 `Win + R`，輸入 `taskschd.msc`，再按 Enter；也可從開始功能表搜尋「工作排程器」。

目前已建立一次性工作：

```text
LTspice_Automation_RunAll_20261015_1600
```

它會在 2026/10/15 16:00 執行 `run_all.py`。在工作排程器左側選「工作排程器程式庫」後，可在中間清單找到此工作。

常用操作：

- 查看下次執行時間與上次結果：在清單中選取工作，查看下方「一般」與「歷程記錄」頁籤。
- 立即測試：右鍵工作，選「執行」。
- 更改時間：右鍵工作，選「內容」→「觸發程序」→ 選取觸發程序後按「編輯」。
- 暫停：右鍵工作，選「停用」。
- 刪除：右鍵工作，選「刪除」。

這個工作以「僅在使用者登入時執行」建立，因此排定時間到達時，Windows 必須保持登入。工作執行後請到 `results/runs/` 檢查新的時間戳記資料夾及 CSV。

## 保留的舊流程

下列指令仍可單獨執行：

```powershell
.\.venv\Scripts\python.exe .\scripts\run_simulation.py
.\.venv\Scripts\python.exe .\scripts\parse_log.py
```

它們會使用原始 `circuit/rc_test.asc`、`circuit/rc_test.log` 和 `results/simulation_results.csv`。日常批次模擬請使用 `run_all.py`，讓每次設定、電路、log 與 CSV 都保存在同一個執行資料夾。

## 發生錯誤時

- 找不到 LTspice：確認 `scripts/run_simulation.py` 中的 `LTSPICE_EXE` 路徑符合電腦上的安裝位置。
- JSON 格式錯誤：確認逗號、雙引號與陣列格式正確。
- 元件找不到：確認 `components` 的名稱與電路檔中的 `InstName` 完全相同。
- 沒有新 CSV：先開啟本次執行資料夾的 `rc_test.log`，確認 LTspice 是否成功完成量測。
