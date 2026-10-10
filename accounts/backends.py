from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        # Django admin continues to use its existing username-based staff form.
        if email is None:
            return super().authenticate(request, username=username, password=password, **kwargs)
        if password is None:
            return None
        User = get_user_model()
        try:
            user = User.objects.get(email__iexact=email.strip()) if email.strip() else None
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            user = None
        if user is None:
            User().set_password(password)
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
