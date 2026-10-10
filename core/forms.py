from django import forms


class ContactForm(forms.Form):
    name = forms.CharField(label='Full name', max_length=120, widget=forms.TextInput(attrs={'placeholder': 'Your full name', 'autocomplete': 'name'}))
    email = forms.EmailField(label='Email address', max_length=254, widget=forms.EmailInput(attrs={'placeholder': 'you@example.com', 'autocomplete': 'email'}))
    phone = forms.CharField(label='Phone number (optional)', max_length=40, required=False, widget=forms.TextInput(attrs={'type': 'tel', 'placeholder': '+234 ...', 'autocomplete': 'tel'}))
    subject = forms.ChoiceField(choices=[('', 'Choose a subject'), ('Course enquiry', 'Course enquiry'), ('Software project', 'Software project'), ('Events & workshops', 'Events & workshops'), ('Payment enquiry', 'Payment enquiry'), ('Technical support', 'Technical support'), ('Partnership', 'Partnership'), ('Other', 'Other')])
    message = forms.CharField(max_length=2000, widget=forms.Textarea(attrs={'placeholder': 'Tell us a little about what you have in mind...', 'rows': 5}))
