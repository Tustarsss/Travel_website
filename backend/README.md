# Travel Backend

FastAPI backend service for the personalized travel system.

## Getting Started

1. Install dependencies with [uv](https://github.com/astral-sh/uv):

```bash
uv sync --all-extras
```

2. Run the development server:

```bash
uv run uvicorn app.main:app --reload
```

3. Execute tests:

```bash
uv run pytest
```

## Data Pipeline

The backend ships with scripts that cover the dataset lifecycle described in the project plan:

1. **Generate synthetic data** (uses Faker/Numpy):

	```bash
	uv run python scripts/generate_data.py --seed 42
	```

	Outputs JSON files under `data/generated/`.

2. **Seed the SQLite database** (also creates placeholder index files):

	```bash
	uv run python scripts/seed_demo.py --drop
	```

	The `--drop` flag clears existing rows before inserting the new dataset.

3. **Validate dataset constraints** (counts, required files):

	```bash
	uv run python scripts/validate_data.py
	```

	Expect a summary that meets the minimum thresholds (≥200 regions, ≥200 edges, etc.).

All commands assume you installed the `data` extra (e.g. `uv sync --extra data --extra dev`) so that Faker and Numpy are available.
