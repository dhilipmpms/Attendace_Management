from django.db import models
from django.db.models import Q

class Space(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='members',
        null=True,
        blank=True
    )
    name = models.CharField(max_length=100)
    work = models.CharField(max_length=100, blank=True, null=True)
    phone = models.CharField(max_length=100, blank=True, null=True)

    extra_member_value = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.title()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['space', 'phone'],
                condition=Q(phone__isnull=False),
                name='unique_phone_per_space'
            )
        ]


class Session(models.Model):
    space = models.ForeignKey(
        Space,
        on_delete=models.CASCADE,
        related_name='sessions',
        null=True,
        blank=True
    )
    date = models.DateField()
    name = models.CharField(max_length=255)  # e.g., "Intro to Python"

    def __str__(self):
        return f"{self.name} ({self.date})"


class Attendance(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    is_present = models.BooleanField(default=False)

    def __str__(self):
        return str(self.member)
    
