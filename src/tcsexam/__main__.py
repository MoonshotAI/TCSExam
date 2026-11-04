"""Allow the same entry point through python -m tcsexam."""
from .cli import main

raise SystemExit(main())
