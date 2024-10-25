from rest_framework import permissions


class IsAuthorOrAuthenticatedOrReadOnly(
    permissions.IsAuthenticatedOrReadOnly
):
    def has_object_permission(self, request, view, obj):
        return obj.author == request.user
