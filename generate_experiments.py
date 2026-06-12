import argparse
import importlib.util
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
WEB_DATA_DIR = ROOT_DIR / "web" / "data"
DEFAULT_COUNTS = [3, 5, 8, 10]


def load_module(file_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def parse_counts(raw_value):
    return [int(item.strip()) for item in raw_value.split(",") if item.strip()]


def main():
    parser = argparse.ArgumentParser(description="批量生成多车辆实验数据")
    parser.add_argument(
        "--vehicle-counts",
        default=",".join(str(count) for count in DEFAULT_COUNTS),
        help="逗号分隔的车辆数，例如 3,5,8,10",
    )
    args = parser.parse_args()

    vehicle_counts = parse_counts(args.vehicle_counts)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

    first_module = load_module(
        ROOT_DIR / "目标一" / "multi_agent_A_star_first_objective.py",
        "first_objective_module",
    )
    second_module = load_module(
        ROOT_DIR / "目标二" / "multi_agent_A_star_second_objective.py",
        "second_objective_module",
    )

    manifest = {"generatedAt": None, "datasets": []}

    for vehicle_count in vehicle_counts:
        for algorithm_key, module in (
            ("first_objective", first_module),
            ("second_objective", second_module),
        ):
            payload, _, _, _ = module.run_experiment(vehicle_count=vehicle_count)
            file_name = f"{algorithm_key}_{vehicle_count}_vehicles.json"
            output_path = WEB_DATA_DIR / file_name
            output_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            manifest["datasets"].append(
                {
                    "key": f"{algorithm_key}_{vehicle_count}",
                    "file": file_name,
                    "algorithm": payload["algorithm"],
                    "description": payload["description"],
                    "vehicleCount": payload["metrics"]["vehicleCount"],
                    "scenario": payload["scenario"]["label"],
                    "label": f"{payload['description']} - {payload['metrics']['vehicleCount']}辆车",
                }
            )

    manifest["generatedAt"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    (WEB_DATA_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
