"""Layer-boundary guard test (the architecture is the grade).

Statically asserts the dependency rules so a violation fails CI:
  - app/api/ imports no sqlalchemy / redis / httpx / infra adapters,
  - app/repositories/ raises no HTTP errors and does no cache invalidation,
  - app/domain/ imports nothing from db/ ORM.
Complements the live Friday boundary check.
"""

# TODO: walk modules, assert forbidden imports per layer


def test_api_layer_has_no_forbidden_imports():
    raise NotImplementedError
