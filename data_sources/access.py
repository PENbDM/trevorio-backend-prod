from .models import DataSource, DataSourceMembership


def accessible_datasources(user):
    if not user or not user.is_authenticated:
        return DataSource.objects.none()
    return DataSource.objects.filter(memberships__user=user).distinct()


def membership_for(user, datasource):
    if not user or not user.is_authenticated:
        return None
    return datasource.memberships.filter(user=user).first()


def user_can_access(user, datasource):
    return membership_for(user, datasource) is not None


def user_is_owner(user, datasource):
    membership = membership_for(user, datasource)
    return bool(membership and str(membership.role).lower() == DataSourceMembership.Role.OWNER)


def user_can_admin(user, datasource):
    membership = membership_for(user, datasource)
    if not membership:
        return False
    return str(membership.role).lower() in (
        DataSourceMembership.Role.OWNER,
        DataSourceMembership.Role.ADMIN,
    )
