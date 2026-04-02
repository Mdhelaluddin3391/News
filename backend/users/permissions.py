from rest_framework import permissions

class IsAdminUser(permissions.BasePermission):
    """Allows access only to Admin users."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'admin')

class IsEditorOrAdmin(permissions.BasePermission):
    """Allows access to Editors and Admins."""
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role in ['admin', 'editor'])

class IsReporterAuthorOrAbove(permissions.BasePermission):
    """Allows access to Reporters, Authors, Editors, and Admins to create articles."""
    def has_permission(self, request, view):
        allowed_roles = ['admin', 'editor', 'reporter', 'author']
        return bool(request.user and request.user.is_authenticated and request.user.role in allowed_roles)

class IsOwnerOrEditorOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow authors/reporters to edit their OWN articles.
    Editors and Admins can edit ANY article.
    """
    def has_object_permission(self, request, view, obj):
        # Admins and Editors can edit anything
        if request.user.role in ['admin', 'editor']:
            return True

        if obj.author is None or obj.author.user_id is None:
            return False

        # Reporters and Authors can only edit if they are the author of the article.
        return obj.author.user_id == request.user.id
