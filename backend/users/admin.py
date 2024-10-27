from django.contrib import admin

from .models import Subscribe, User


class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'username',
        'email',
        'first_name',
        'last_name',
    )
    search_fields = ('username', 'email')
    list_display_links = ('username',)
    empty_value_display = 'Не задано'


class SubscribeAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'subscribed_user',
    )
    search_fields = ('user',)
    empty_value_display = 'Не задано'


admin.site.register(User, UserAdmin)
admin.site.register(Subscribe, SubscribeAdmin)
