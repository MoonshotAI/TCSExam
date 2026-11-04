"""Allow the backend entry point through ``python -m tcsexam.backend``."""
from .server import main

raise SystemExit(main())
