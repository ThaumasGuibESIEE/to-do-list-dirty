from django import forms

from .models import Task


class TaskForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                "placeholder": "Add new task",
                "id": "task-title",
                "class": "form-control",
                "aria-label": "Task title",
                "aria-required": "true",
            },
        ),
    )
    priority = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(
            attrs={
                "id": "task-priority",
                "class": "form-check-input",
                "aria-label": "Mark as priority",
            }
        ),
        label="Mark as priority",
    )

    class Meta:
        model = Task
        fields = ["title", "priority", "complete"]
