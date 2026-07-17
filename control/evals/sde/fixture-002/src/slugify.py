# Seeded-failure fixture (SDE-GT-002-SEEDED): naive implementation and no
# tests shipped — the case's file_exists check on tests/test_slugify.py MUST
# miss, proving the harness blocks incomplete work.


def slugify(title):
    return title.lower().replace(" ", "-")
