"""Compatibility wrapper for the explicit demo-data seed script.

Normal dashboard refreshes should run ``python src/build_all.py``. That build
reads existing raw carbon/REGO inputs and does not reseed demo data.

Use ``python src/seed_demo_data.py`` only when intentionally resetting the
representative demo inputs.
"""

from __future__ import annotations

from seed_demo_data import main


if __name__ == "__main__":
    main()
