from django.conf import settings
from django.db import models

# Create your models here.
class Task(models.Model):
	title = models.CharField(max_length=200)
	complete = models.BooleanField(default=False)
	priority = models.BooleanField(default=False)
	created = models.DateTimeField(auto_now_add=True)
	tmdb_id = models.IntegerField(null=True, blank=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=['user', 'tmdb_id'], name='unique_user_tmdb')
		]

	def __str__(self):
		return self.title
