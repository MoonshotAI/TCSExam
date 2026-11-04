"""Error-classification contract shared with the task-side retry matchers.

The strings in this module are a WIRE CONTRACT: the task-side harnesses
(``tasks/solver/online/*/environment/submit.sh`` and ``tests/fetch_final.py``)
match on them verbatim (for example their transient-failure markers contain
``"please try again"``), so a platform flap is retried instead of scored 0.
Everything here is the single source of those literals — never reword them.
"""
from __future__ import annotations

#: Substring present in the task harnesses' transient-failure markers:
#: appended to transient platform failures so the harness retries them
#: instead of scoring 0.
TRANSIENT_HINT = "please try again"

#: Platform errors that a retry will NOT fix — everything else raised by a
#: platform adapter is treated as transient (safe default: a wasted retry
#: beats an aborted evaluation). Matched by class name so adapter exception
#: hierarchies can live anywhere.
NON_TRANSIENT_ERROR_NAMES = frozenset(
    {
        "AuthenticationError",  # bad platform credentials
        "PermissionDeniedError",
        "InvalidArgumentError",  # bad profile/image spec — a config bug
        "InsufficientCreditsError",
        # The in-worker judge server died at boot or reported the terminal
        # {"status": "error"} health state — the judge IMAGE is broken, so a
        # retry recreates the same failure (boot fail-fast).
        "JudgeBootError",
    }
)


#: 503 body wording when judge traffic (relay / submit / ...) hits a session
#: whose background creation is still running (asynchronous creation).
#: Carries TRANSIENT_HINT so the task-side transient matchers keep retrying
#: until the session flips to ready.
PROVISIONING_MESSAGE = "judge session is still provisioning; please try again"


#: 400 body wording when ``run_id_mode = "required"`` rejects a request whose
#: ``X-TCSEXAM-Run-Id`` header is missing or malformed (the clients surface
#: the body verbatim on evaluation failures, so keep it actionable).
INVALID_RUN_ID_MESSAGE = (
    "invalid or missing X-TCSEXAM-Run-Id header "
    "(required: non-empty, <= 128 chars, printable ASCII)"
)


def is_transient_platform_error(exc: BaseException) -> bool:
    """True when the platform error is worth retrying by the task harness."""
    return type(exc).__name__ not in NON_TRANSIENT_ERROR_NAMES


def transient_suffix() -> str:
    """The standard suffix marking a failure message as retryable task-side."""
    return f" (transient platform error, {TRANSIENT_HINT})"
