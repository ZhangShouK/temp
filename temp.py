import asyncio
import json
from dataclasses import asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pyrit.datasets import SeedDatasetProvider
from pyrit.registry import ScenarioRegistry
from pyrit.registry.components.attack_technique_registry import AttackTechniqueRegistry
from pyrit.setup import IN_MEMORY, initialize_pyrit_async
from pyrit.setup.initializers.techniques.technique_initializer import build_technique_factories


def to_json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, set | frozenset):
        return sorted((to_json_value(item) for item in value), key=str)
    if isinstance(value, tuple):
        return [to_json_value(item) for item in value]
    if isinstance(value, list):
        return [to_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return to_json_value(value.model_dump(mode="python"))
    if hasattr(value, "__dataclass_fields__"):
        return to_json_value(asdict(value))
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


async def build_catalog() -> dict[str, Any]:
    await initialize_pyrit_async(memory_db_type=IN_MEMORY, silent=True)

    technique_registry = AttackTechniqueRegistry.get_registry_singleton()
    technique_registry.register_from_factories(build_technique_factories(groups=["extra"]))

    scenario_registry = ScenarioRegistry.get_registry_singleton()
    scenarios = []
    for metadata in scenario_registry.get_all_registered_class_metadata():
        scenarios.append(to_json_value(metadata))

    techniques = []
    for name, factory in sorted(technique_registry.get_factories_or_raise().items()):
        techniques.append(
            {
                "name": name,
                "description": factory.description,
                "attack_class": f"{factory.attack_class.__module__}.{factory.attack_class.__name__}",
                "tags": sorted(factory.technique_tags),
                "uses_adversarial": factory.uses_adversarial,
                "supports_additional_request_converters": factory.supports_additional_request_converters,
            }
        )

    dataset_names = await SeedDatasetProvider.get_all_dataset_names_async()
    provider_by_name = {
        provider_class().dataset_name: provider_class
        for provider_class in SeedDatasetProvider.get_all_providers().values()
    }
    datasets = []
    for name in dataset_names:
        provider_class = provider_by_name.get(name)
        metadata = await provider_class()._parse_metadata_async() if provider_class else None
        datasets.append(
            {
                "name": name,
                "provider_class": (
                    f"{provider_class.__module__}.{provider_class.__name__}" if provider_class else None
                ),
                "metadata": to_json_value(metadata) if metadata is not None else None,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pyrit_version": __import__("pyrit").__version__,
        "description": (
            "Installed PyRIT scenario, attack-technique, and seed-dataset catalog. "
            "Dataset entries describe available providers; prompt contents are not downloaded."
        ),
        "counts": {
            "scenarios": len(scenarios),
            "techniques": len(techniques),
            "datasets": len(datasets),
        },
        "scenarios": scenarios,
        "techniques": techniques,
        "datasets": datasets,
    }


async def main() -> None:
    catalog = await build_catalog()
    output_path = Path("pyrit_catalog.json")
    output_path.write_text(
        json.dumps(catalog, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {output_path.resolve()} ({catalog['counts']})")


if __name__ == "__main__":
    asyncio.run(main())
