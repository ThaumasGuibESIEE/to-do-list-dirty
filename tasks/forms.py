from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Add new task",
                "id": "task-title",
                "class": "form-control",
            },
        ),
    )
    priority = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "id": "task-priority",
                "class": "form-check-input",
            }
        ),
        label="Mark as priority",
    )

    class Meta:
        model = Task
        fields = ["title", "priority", "complete"]
