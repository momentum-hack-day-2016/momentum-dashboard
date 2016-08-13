from django import forms

class MomentumSignupForm(forms.Form):
    name = forms.CharField()
    email = forms.CharField()
    area = forms.CharField()
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
