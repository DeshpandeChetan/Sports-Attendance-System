from django import forms
from django.contrib.auth import get_user_model

from .models import AttendanceRecord, Feedback, Membership, Session, Sport, Team, UserProfile

User = get_user_model()


class BootstrapFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            field.widget.attrs.setdefault("class", css)


class SportForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Sport
        fields = ["name", "description", "is_active"]


class TeamForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Team
        fields = ["sport", "name", "team_type", "gender", "captain", "vice_captain", "coordinator", "is_active"]


class MembershipForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Membership
        fields = ["user", "team", "jersey_number", "is_active", "joined_on"]
        widgets = {"joined_on": forms.DateInput(attrs={"type": "date"})}


class UserRoleForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()

    class Meta:
        model = UserProfile
        fields = ["role", "department", "phone"]

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop("user_instance", None)
        super().__init__(*args, **kwargs)
        if self.user_instance:
            self.fields["first_name"].initial = self.user_instance.first_name
            self.fields["last_name"].initial = self.user_instance.last_name
            self.fields["email"].initial = self.user_instance.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        user = profile.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        user.username = self.cleaned_data["email"]
        if commit:
            user.save()
            profile.save()
        return profile


class SessionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Session
        fields = ["team", "title", "start_at", "end_at", "venue", "notes"]
        widgets = {
            "start_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "end_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class DelegateForm(BootstrapFormMixin, forms.Form):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none())
    reason = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        session = kwargs.pop("session")
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            memberships__team=session.team,
            memberships__is_active=True,
        ).distinct()


class AttendanceEditForm(BootstrapFormMixin, forms.ModelForm):
    reason = forms.CharField(max_length=255)

    class Meta:
        model = AttendanceRecord
        fields = ["status", "remarks"]


class FeedbackForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["receiver", "session", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


class SessionFeedbackForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ["session", "message"]
        widgets = {"message": forms.Textarea(attrs={"rows": 4})}


class ReportFilterForm(BootstrapFormMixin, forms.Form):
    sport = forms.ModelChoiceField(queryset=Sport.objects.all(), required=False)
    team = forms.ModelChoiceField(queryset=Team.objects.all(), required=False)
    student = forms.ModelChoiceField(queryset=User.objects.all(), required=False)
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
