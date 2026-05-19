"""User persistence (fastapi-users compatible). SQL only.

Maps UserORM <-> domain.User. Role lookups for authorization happen here;
the authorization DECISION happens in the service layer.
"""

# TODO: get_by_id, get_by_email, create, set_role
