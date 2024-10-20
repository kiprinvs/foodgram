from rest_framework import permissions


class IsAuthorOrIsAuthenticatedOrReadOnly(
    permissions.IsAuthenticatedOrReadOnly
):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user
