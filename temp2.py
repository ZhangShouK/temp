import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter


BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "pyrit_catalog.json"
OUTPUT_PATH = BASE_DIR / "pyrit_catalog.xlsx"


def add_header(sheet, headers: list[str]) -> None:
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def set_column_widths(sheet, widths: dict[int, float]) -> None:
    for column_index, width in widths.items():
        sheet.column_dimensions[get_column_letter(column_index)].width = width


def main() -> None:
    catalog = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    workbook = Workbook()

    scenarios_sheet = workbook.active
    scenarios_sheet.title = "Scenarios"
    add_header(
        scenarios_sheet,
        [
            "Scenario Name",
            "Default Technique",
            "Other Technique",
            "Technique Description",
            "Global Technique",
        ],
    )

    global_technique_names = {technique["name"] for technique in catalog.get("techniques", [])}
    for scenario in sorted(catalog.get("scenarios", []), key=lambda item: item["registry_name"]):
        scenario_name = scenario["registry_name"]
        default_techniques = set(scenario.get("default_techniques", []))
        all_techniques = set(scenario.get("all_techniques", []))
        summaries = {summary["name"]: summary for summary in scenario.get("technique_summaries", [])}

        for technique_name in sorted(default_techniques | all_techniques):
            description = (summaries.get(technique_name) or {}).get("description") or ""
            is_default = technique_name in default_techniques
            scenarios_sheet.append(
                [
                    scenario_name,
                    technique_name if is_default else "",
                    "" if is_default else technique_name,
                    description,
                    "Yes" if technique_name in global_technique_names else "No",
                ]
            )
    for row in scenarios_sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    set_column_widths(scenarios_sheet, {1: 36, 2: 34, 3: 34, 4: 90, 5: 18})

    datasets_sheet = workbook.create_sheet("Datasets")
    add_header(datasets_sheet, ["Dataset Name", "Harm Categories"])
    for dataset in sorted(catalog.get("datasets", []), key=lambda item: item["name"]):
        metadata = dataset.get("metadata") or {}
        harm_categories = metadata.get("harm_categories") or []
        datasets_sheet.append([dataset["name"], "\n".join(str(value) for value in harm_categories)])
    for row in datasets_sheet.iter_rows(min_row=2):
        row[1].alignment = Alignment(vertical="top", wrap_text=True)
    set_column_widths(datasets_sheet, {1: 46, 2: 32})

    workbook.save(OUTPUT_PATH)
    print(f"Wrote {OUTPUT_PATH} ({len(catalog.get('scenarios', []))} scenarios, "
          f"{len(catalog.get('techniques', []))} techniques, "
          f"{len(catalog.get('datasets', []))} datasets)")


if __name__ == "__main__":
    main()
