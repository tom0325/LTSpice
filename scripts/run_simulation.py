from pathlib import Path
import argparse
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 專案根目錄
PROJECT_DIR = Path(__file__).resolve().parent.parent

# 電路檔路徑
CIRCUIT_FILE = PROJECT_DIR / "circuit" / "rc_test.asc"

# LTspice 執行檔路徑
LTSPICE_EXE = Path(
    r"C:\Users\HSYU096\AppData\Local\Programs\ADI\LTspice\LTspice.exe"
)


def main():
    parser = argparse.ArgumentParser(description="Run an LTspice batch simulation.")
    parser.add_argument(
        "--circuit",
        type=Path,
        default=CIRCUIT_FILE,
        help="ASC circuit file (defaults to circuit/rc_test.asc).",
    )
    args = parser.parse_args()
    circuit_file = args.circuit.resolve()

    # 確認檔案存在
    if not LTSPICE_EXE.exists():
        raise FileNotFoundError(
            f"找不到 LTspice 執行檔：{LTSPICE_EXE}"
        )

    if not circuit_file.exists():
        raise FileNotFoundError(
            f"找不到電路檔：{circuit_file}"
        )

    # 執行 LTspice 批次模擬
    command = [
        str(LTSPICE_EXE),
        "-b",
        str(circuit_file),
    ]

    print("開始執行 LTspice 模擬...")
    print(f"電路檔：{circuit_file}")

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=120,
    )

    print(f"\nLTspice 結束碼：{result.returncode}")

    if result.stdout:
        print("\n標準輸出：")
        print(result.stdout)

    if result.stderr:
        print("\n錯誤輸出：")
        print(result.stderr)

    # 檢查模擬紀錄
    log_file = circuit_file.with_suffix(".log")

    if result.returncode != 0:
        raise RuntimeError(
            f"LTspice 執行失敗，結束碼：{result.returncode}"
        )

    if not log_file.exists():
        raise FileNotFoundError(
            f"沒有找到模擬紀錄：{log_file}"
        )

    log_text = log_file.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if "Measurement:" not in log_text:
        raise RuntimeError(
            "找到 log，但沒有量測結果。請檢查 LTspice 模擬紀錄。"
        )

    print("\n已找到 LTspice log 與量測區塊。")
    print(f"Log 路徑：{log_file}")
    print("下一步可以執行 parse_log.py。")


if __name__ == "__main__":
    main()
