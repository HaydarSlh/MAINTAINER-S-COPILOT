"""The MANDATORY redaction test.

Per the brief: a test asserts that a message containing a fake API key never
appears unredacted in logs, traces, OR memory. This runs in CI on every push.
"""

# TODO: feed a fake API key through log / trace / memory write paths and
#       assert the raw key never appears, only the redacted form.


def test_fake_api_key_never_appears_unredacted():
    raise NotImplementedError
