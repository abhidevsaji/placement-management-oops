"""Role-based access control. Each class says which roles may enter."""
from rest_framework.permissions import BasePermission


class RolePermission(BasePermission):
    allowed_roles = ()
    message = 'You do not have permission for this action.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_approved and user.role in self.allowed_roles)


class IsStudent(RolePermission):
    allowed_roles = ('student',)


class IsPlacementOfficer(RolePermission):
    allowed_roles = ('officer',)


class IsAdminRole(RolePermission):
    allowed_roles = ('admin',)


class IsOfficerOrAdmin(RolePermission):
    allowed_roles = ('officer', 'admin')


class IsAnyApprovedUser(RolePermission):
    allowed_roles = ('student', 'officer', 'admin')
