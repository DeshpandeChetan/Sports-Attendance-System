from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import datetime, time

from .models import AttendanceRecord, Feedback, Membership, Session, Sport, Team, UserProfile, Venue

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


class VenueForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Venue
        fields = ["name", "location", "is_active"]


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


class ProfileForm(BootstrapFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(disabled=True, required=False)

    class Meta:
        model = UserProfile
        fields = ["department", "class_name", "phone", "dob", "address", "register_no", "gender"]
        widgets = {
            "dob": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user_instance = kwargs.pop("user_instance")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user_instance.first_name
        self.fields["last_name"].initial = self.user_instance.last_name
        self.fields["email"].initial = self.user_instance.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user_instance.first_name = self.cleaned_data["first_name"]
        self.user_instance.last_name = self.cleaned_data["last_name"]
        if commit:
            self.user_instance.save(update_fields=["first_name", "last_name"])
            profile.save()
        return profile


class SessionForm(BootstrapFormMixin, forms.ModelForm):
    start_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    venue_choice = forms.ChoiceField(choices=(), required=True)
    other_venue = forms.CharField(max_length=160, required=False)

    class Meta:
        model = Session
        fields = ["team", "title", "schedule_slot", "notes"]
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["title"].required = False
        venue_choices = [(venue.name, venue.name) for venue in Venue.objects.filter(is_active=True)]
        self.fields["venue_choice"].choices = venue_choices + [("OTHER", "Other")]
        if self.instance and self.instance.pk:
            self.fields["start_date"].initial = timezone.localtime(self.instance.start_at).date()
            self.fields["end_date"].initial = timezone.localtime(self.instance.end_at).date()
            self.fields["venue_choice"].initial = self.instance.venue
            if self.instance.venue.startswith("Other - "):
                self.fields["venue_choice"].initial = "OTHER"
                self.fields["other_venue"].initial = self.instance.venue.replace("Other - ", "", 1)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("venue_choice") == "OTHER" and not cleaned.get("other_venue"):
            self.add_error("other_venue", "Enter the venue name.")
        start_date = cleaned.get("start_date")
        end_date = cleaned.get("end_date")
        if start_date and end_date and end_date < start_date:
            self.add_error("end_date", "End date cannot be before start date.")
        return cleaned

    def save(self, commit=True):
        session = super().save(commit=False)
        slot = self.cleaned_data["schedule_slot"]
        start_clock = time(6, 30) if slot == Session.ScheduleSlot.MORNING else time(16, 0)
        end_clock = time(8, 30) if slot == Session.ScheduleSlot.MORNING else time(18, 0)
        session.start_at = timezone.make_aware(datetime.combine(self.cleaned_data["start_date"], start_clock))
        session.end_at = timezone.make_aware(datetime.combine(self.cleaned_data["end_date"], end_clock))
        session.title = self.cleaned_data.get("title") or "Practice session"
        session.venue = f"Other - {self.cleaned_data['other_venue']}" if self.cleaned_data["venue_choice"] == "OTHER" else self.cleaned_data["venue_choice"]
        if commit:
            session.save()
        return session


class DelegateForm(BootstrapFormMixin, forms.Form):
    assigned_to = forms.ModelChoiceField(queryset=User.objects.none())
    reason = forms.CharField(max_length=255, required=False)

    def __init__(self, *args, **kwargs):
        session = kwargs.pop("session")
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            memberships__team__sport=session.team.sport,
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
