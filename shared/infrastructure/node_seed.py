"""Bootstrap the IAM device registry from a local node seed file.

On edge start-up, reads a JSON list of nodes and registers
any that are not yet present in SQLite.  Each node is identified by
``device_id`` and ``mac_address`` — the MAC is read at runtime by the ESP32 and
is not flashed as a secret on the device.

The seed file is optional.  When absent or disabled via ``NODE_SEED_ENABLED``,
this module is a no-op.
"""
import json
import logging
import os
from typing import Any

from iam.application.services import DeviceApplicationService
from iam.domain.exceptions import DeviceAlreadyExistsError
from iam.infrastructure.repositories import DeviceRepository
from shared.infrastructure.config import EdgeConfig
from shared.infrastructure.database import db

logger = logging.getLogger(__name__)

_REQUIRED_FIELDS = ("device_id", "mac_address", "device_type")


def _load_nodes(path: str) -> list[dict[str, Any]]:
    with open(path, encoding="utf-8") as seed_file:
        payload = json.load(seed_file)

    if not isinstance(payload, dict):
        raise ValueError("Node seed file must be a JSON object")
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        raise ValueError("Node seed file must contain a 'nodes' array")
    return nodes


def seed_registered_nodes() -> None:
    """Register nodes from the configured seed file (idempotent).

    Existing ``device_id`` values are skipped.  Invalid entries are logged and
    skipped without aborting the rest of the list.
    """
    if not EdgeConfig.NODE_SEED_ENABLED:
        logger.debug("Node seed disabled (NODE_SEED_ENABLED=false)")
        return

    path = EdgeConfig.NODE_SEED_PATH
    if not os.path.isfile(path):
        logger.info("No node seed file at %s — skipping bootstrap", path)
        return

    try:
        nodes = _load_nodes(path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.error("Failed to load node seed from %s: %s", path, exc)
        return

    device_service = DeviceApplicationService()
    repository = DeviceRepository()
    created = 0
    skipped = 0
    failed = 0

    db.connect()
    try:
        for index, node in enumerate(nodes):
            if not isinstance(node, dict):
                logger.warning("Node seed entry %s is not an object — skipping", index)
                failed += 1
                continue

            missing = [field for field in _REQUIRED_FIELDS if field not in node]
            if missing:
                logger.warning(
                    "Node seed entry %s missing fields %s — skipping",
                    index,
                    ", ".join(missing),
                )
                failed += 1
                continue

            device_id = str(node["device_id"]).strip()
            if repository.find_by_device_id(device_id):
                skipped += 1
                continue

            try:
                device_service.register_device(
                    device_id=device_id,
                    device_type=node["device_type"],
                    mac_address=str(node["mac_address"]),
                )
                created += 1
                logger.info("Seeded node '%s' from %s", device_id, path)
            except (ValueError, DeviceAlreadyExistsError) as exc:
                logger.warning("Could not seed node '%s': %s", device_id, exc)
                failed += 1
    finally:
        db.close()

    logger.info(
        "Node seed complete: %s created, %s already registered, %s failed",
        created,
        skipped,
        failed,
    )
