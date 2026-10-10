from django import forms


class EventRegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=200, label='Full name', widget=forms.TextInput(attrs={'class': 'form-input', 'autocomplete': 'name', 'placeholder': 'Your full name'}))
    email = forms.EmailField(max_length=254, label='Email address', widget=forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email', 'placeholder': 'you@example.com'}))
    phone = forms.CharField(max_length=30, label='Phone number', widget=forms.TextInput(attrs={'class': 'form-input', 'type': 'tel', 'autocomplete': 'tel', 'placeholder': '+234 ...'}))

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()
