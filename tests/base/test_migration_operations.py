import pytest
from django_test_migrations.migrator import Migrator


@pytest.mark.django_db
def test_reset_sequences_completes_without_crashing(migrator: Migrator):
    # Smoke test for the reset sequences operation
    migrator.apply_initial_migration(("testapp", None))

    try:
        migrator.apply_tested_migration(("testapp", "0001_reset_sequences"))
    except Exception:  # noqa: BLE001
        pytest.fail("Expected operation to not crash")
