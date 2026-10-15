from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


PROJECT_DIR = Path(__file__).resolve().parent.parent
VENV_PYTHON = PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
CIRCUIT_TEMPLATE = PROJECT_DIR / "circuit" / "rc_test.asc"
CONFIG_FILE = PROJECT_DIR / "simulation_config.json"
RUNS_DIR = PROJECT_DIR / "results" / "runs"
SIMULATION_SCRIPT = PROJECT_DIR / "scripts" / "run_simulation.py"
PARSER_SCRIPT = PROJECT_DIR / "scripts" / "parse_log.py"


def ensure_venv_python():
    """Restart this script with the project interpreter when needed."""
    if Path(sys.executable).resolve() != VENV_PYTHON.resolve():
        if not VENV_PYTHON.exists():
            raise FileNotFoundError(f"找不到專案虛擬環境 Python：{VENV_PYTHON}")
        result = subprocess.run(
            [str(VENV_PYTHON), str(Path(__file__).resolve()), *sys.argv[1:]]
        )
        raise SystemExit(result.returncode)


def validate_ltspice_value(value):
    """Accept simple LTspice numbers with an optional engineering suffix."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?(?:meg|[tgkmunpf])?",
        value.strip(),
        re.IGNORECASE,
    ):
        raise ValueError(f"元件值必須是數字或帶工程單位的字串：{value!r}")
    return value.strip()


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"找不到批次模擬設定：{CONFIG_FILE}")
    config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    resistances = config.get("resistances_ohm")
    components = config.get("components", {})

    if not isinstance(resistances, list) or not resistances:
        raise ValueError("設定中的 resistances_ohm 必須是非空陣列。")
    if any(
        not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0
        for value in resistances
    ):
        raise ValueError("resistances_ohm 必須只包含正數。")
    if not isinstance(components, dict):
        raise ValueError("設定中的 components 必須是元件名稱和值組成的物件。")
    for value in components.values():
        validate_ltspice_value(value)
    return config


def make_run_circuit(config, run_dir):
    """Create a run-specific ASC from the circuit template and JSON values."""
    if not CIRCUIT_TEMPLATE.exists():
        raise FileNotFoundError(f"找不到電路模板：{CIRCUIT_TEMPLATE}")

    # LTspice ASC files here are Windows-1252 (the micro sign is byte 0xB5).
    text = CIRCUIT_TEMPLATE.read_bytes().decode("cp1252")
    step_pattern = re.compile(
        r"(?im)^(\s*TEXT\s+.*?!\.step\s+param\s+Rval\s+list\s+)[^\r\n]+"
    )
    step_values = " ".join(format(value, ".15g") for value in config["resistances_ohm"])
    text, count = step_pattern.subn(rf"\g<1>{step_values}", text)
    if count != 1:
        raise ValueError("電路模板必須且只能有一條 Rval .step list 指令。")

    for instance, value in config.get("components", {}).items():
        instance_pattern = re.compile(
            rf"(?ms)(SYMATTR InstName\s+{re.escape(instance)}\s*\r?\n"
            rf"(?:(?!SYMBOL\s).)*?SYMATTR Value\s+)[^\r\n]+"
        )
        text, count = instance_pattern.subn(
            lambda match: match.group(1) + validate_ltspice_value(value), text
        )
        if count != 1:
            raise ValueError(f"電路模板中找不到唯一元件 {instance}，無法套用設定值。")

    run_dir.mkdir(parents=True, exist_ok=False)
    circuit_file = run_dir / "rc_test.asc"
    circuit_file.write_bytes(text.encode("cp1252"))
    (run_dir / "simulation_config.json").write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return circuit_file


def run_script(script_path, *args, cwd):
    if not script_path.exists():
        raise FileNotFoundError(f"找不到腳本：{script_path}")
    print(f"\n執行：{script_path.name}", flush=True)
    result = subprocess.run(
        [sys.executable, str(script_path), *map(str, args)], cwd=cwd
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script_path.name} 執行失敗，結束碼：{result.returncode}")


def main():
    ensure_venv_python()

    try:
        import pandas  # noqa: F401

        config = load_config()
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        run_dir = RUNS_DIR / timestamp
        circuit_file = make_run_circuit(config, run_dir)
        log_file = circuit_file.with_suffix(".log")
        csv_file = run_dir / "simulation_results.csv"

        run_script(SIMULATION_SCRIPT, "--circuit", circuit_file, cwd=run_dir)
        if not log_file.exists():
            raise FileNotFoundError(f"模擬後沒有產生本次 log：{log_file}")
        run_script(
            PARSER_SCRIPT,
            "--log",
            log_file,
            "--output",
            csv_file,
            "--resistances",
            *config["resistances_ohm"],
            cwd=run_dir,
        )
        print(f"\n本次執行資料夾：{run_dir}")
    except SystemExit:
        raise
    except Exception as exc:
        print(f"\n流程失敗：{exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
