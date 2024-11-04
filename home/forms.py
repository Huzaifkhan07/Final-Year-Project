# forms.py
from django import forms
from .models import UploadedImage

class AnalysisForm(forms.ModelForm):
    age = forms.IntegerField(required=True)
    weight = forms.FloatField(required=True)
    disease = forms.CharField(required=False)
    
    
    class Meta:
        model = UploadedImage
        fields = ['image']  # Only bind the image field to the model
