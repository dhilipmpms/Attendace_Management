from django.db import models

class Member(models.Model):
    name = models.CharField(max_length=100)
    work = models.CharField(max_length=100, blank=True, null =True)
    phone = models.CharField(max_length=100 ,blank=True, null =True)
    
    def save(self, *args, **kwargs):
        self.name = self.name.title()  # Capitalize First Letter Of Each Word
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Session(models.Model):
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
