from django.db import models
import os

def upload_image_path(instance, filename):
    # Set a fixed file name to ensure overwriting
    return 'uploaded_images/latest_image.jpg'

class UploadedImage(models.Model):
    image = models.ImageField(upload_to=upload_image_path)
    uploaded_at = models.DateTimeField(auto_now=True)
