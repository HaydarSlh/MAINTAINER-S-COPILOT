"""Refuse-to-boot guard tests.

Asserts the api refuses to boot when: Vault unreachable, classifier weights
missing, weights SHA != model card, tracing misconfigured, or any committed
eval threshold is zero/disabled.
"""

# TODO: parametrized cases, each asserting create_app() raises


def test_refuses_boot_on_zero_eval_threshold():
    raise NotImplementedError
