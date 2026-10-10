from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

from .models import Profile
from django import forms


class UniqueEmailMixin:
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email and User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('An account with this email address already exists.')
        return email


class EmailUserChangeForm(UniqueEmailMixin, UserAdmin.form):
    pass


class EmailUserCreationForm(UniqueEmailMixin, UserAdmin.add_form):
    pass


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


class UserWithProfileAdmin(UserAdmin):
    inlines = [ProfileInline]
    form = EmailUserChangeForm
    add_form = EmailUserCreationForm


admin.site.unregister(User)
admin.site.register(User, UserWithProfileAdmin)
