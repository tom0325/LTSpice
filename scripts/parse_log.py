from pathlib import Path
import argparse
import re
import sys
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 專案根目錄
PROJECT_DIR = Path(__file__).resolve().parent.parent

# LTspice log 路徑
LOG_FILE = PROJECT_DIR / "circuit" / "rc_test.log"

# CSV 輸出路徑
OUTPUT_FILE = PROJECT_DIR / "results" / "simulation_results.csv"

# 五組電阻，順序對應 LTspice .step 的模擬順序
RESISTANCES = [500, 1000, 2000, 5000, 10000]


def extract_section(text, measurement_name):
    """擷取指定 .meas 量測區塊。"""
    pattern = (
        rf"Measurement:\s*{re.escape(measurement_name)}"
        rf"\s*\n(.*?)(?=\n\s*Measurement:|\Z)"
    )

    match = re.search(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL,
    )

    if not match:
        raise ValueError(
            f"找不到量測區塊：{measurement_name}"
        )

    return match.group(1)


def main():
    parser = argparse.ArgumentParser(description="Parse LTspice measurement results.")
    parser.add_argument("--log", type=Path, default=LOG_FILE)
    parser.add_argument("--output", type=Path, default=OUTPUT_FILE)
    parser.add_argument("--resistances", nargs="+", type=float, default=RESISTANCES)
    args = parser.parse_args()

    log_file = args.log.resolve()
    output_file = args.output.resolve()
    resistances = args.resistances

    if not log_file.exists():
        raise FileNotFoundError(
            f"找不到 LTspice log：{log_file}\n"
            "請先執行 run_simulation.py。"
        )

    text = log_file.read_text(
        encoding="utf-8",
        errors="replace",
    )

    # 擷取兩個量測區塊
    voltage_section = extract_section(text, "Vout_5ms")
    result_section = extract_section(text, "Result")

    # 擷取電壓：step、voltage、時間
    voltage_rows = re.findall(
        r"^\s*(\d+)\s+"
        r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s+"
        r"([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*$",
        voltage_section,
        re.MULTILINE,
    )

    # 擷取 PASS/FAIL 數值：step、0 或 1
    result_rows = re.findall(
        r"^\s*(\d+)\s+([01])\s*$",
        result_section,
        re.MULTILINE,
    )

    voltage_by_step = {
        int(step): float(voltage)
        for step, voltage, _time in voltage_rows
    }

    result_by_step = {
        int(step): int(value)
        for step, value in result_rows
    }

    expected_steps = set(range(1, len(resistances) + 1))

    if (
        set(voltage_by_step) != expected_steps
        or set(result_by_step) != expected_steps
    ):
        raise ValueError(
            "擷取到的量測筆數或 step 編號不正確。\n"
            "請檢查 rc_test.log 中的 Measurement 區塊，"
            "確認是否與目前的電路設定一致。"
        )

    # 整理成 DataFrame
    records = []

    for step, resistance in enumerate(resistances, start=1):
        records.append({
            "R_ohm": resistance,
            "Vout_5ms_V": voltage_by_step[step],
            "PASS": result_by_step[step] == 1,
        })

    df = pd.DataFrame(records)

    # 建立輸出資料夾並匯出 CSV
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_csv(
        output_file,
        index=False,
        encoding="utf-8-sig",
    )

    print("LTspice 模擬結果：\n")
    print(df.to_string(index=False))
    print(f"\nCSV 已輸出至：{output_file}")


if __name__ == "__main__":
    main()
