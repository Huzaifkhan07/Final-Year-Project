from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, redirect
from .forms import AnalysisForm
from .models import UploadedImage
import os
import io
from io import BytesIO
import base64
import google.generativeai as genai
from PIL import Image
from django.conf import settings
import pandas as pd
import markdown

import matplotlib
matplotlib.use('Agg')  # Use the non-interactive backend for script usage
import matplotlib.pyplot as plt  # type: ignore

import json

# Initialize the Gemini model
model = genai.GenerativeModel("gemini-1.5-flash")

def get_gemini_response(input_prompt, image):
    response = model.generate_content([input_prompt, image[0]])
    return response.text


# Function to handle uploaded images
def input_image_setup(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.read()  # Use .read() instead of .getvalue()
        image_parts = [
            {
                "mime_type": "image/jpeg",  # Specify the correct MIME type (e.g., 'image/jpeg' or 'image/png')
                "data": bytes_data
            }
        ]
        return image_parts
    else:
        raise FileNotFoundError("No file uploaded")


def create_pie_chart(data):
    # Extract 'Item' and 'Value' into separate lists
    items = [entry['Item'] for entry in data]
    values = [entry['Value'] for entry in data]

    # Convert values to numeric
    values = pd.to_numeric(values, errors='coerce')  # Converts values to floats, setting errors to NaN

    # Create a DataFrame
    df = pd.DataFrame({'Item': items, 'Value': values})

    # Create a pie chart with a larger figure size
    fig, ax = plt.subplots(figsize=(10, 6))  # Adjust the size as needed
    wedges, texts = ax.pie(df['Value'], labels=None, startangle=90)

    # Add the legend with labels and percentages
    legend_labels = [f"{item}: {value:.1f}%" for item, value in zip(df['Item'], 100 * df['Value'] / df['Value'].sum())]
    ax.legend(wedges, legend_labels, title="Nutritional Info", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1), fontsize='large')  # Set fontsize here

    ax.axis('equal')  # Equal aspect ratio ensures that pie chart is circular.
    
    # Use tight layout to adjust subplots
    fig.tight_layout()

    return fig


def home(request):
    analysis_result = None
    uploaded_image = None
    pie_chart_image = None
    html_content = ""  # Initialize html_content to an empty string

    if request.method == "POST":
        form = AnalysisForm(request.POST, request.FILES)
        if form.is_valid():
            age = form.cleaned_data['age']
            weight = form.cleaned_data['weight']
            disease = form.cleaned_data['disease']
            my_disease = disease if disease else "I don't have any disease"

            # Delete old image if it exists
            if UploadedImage.objects.exists():
                old_image = UploadedImage.objects.first()
                old_image_path = old_image.image.path
                if os.path.exists(old_image_path):
                    os.remove(old_image_path)
                old_image.delete()

            # Save new image
            uploaded_image = UploadedImage(image=form.cleaned_data['image'])
            uploaded_image.save()

            # Path to the uploaded image
            image_path = uploaded_image.image.path

            # Open the image using PIL
            with open(image_path, 'rb') as f:
                image_data = input_image_setup(f)

            # Define the input prompt for the Gemini model
            input_prompt = """
            Analyze the nutritional information of the food items from the image. You need to extract the following details: nutrition content, calories per unit, levels of fat, salt, sugar, added sugar, etc.
            
            Note: Some values may be in different units such as grams, kcal, mg, or percentages. Convert all values to grams.
            
            Please provide the extracted information in the following format only:
            [{"Item": "Ingredient 1", "Value": X}, {"Item": "Ingredient 2", "Value": Y}, {"Item": "Ingredient 3", "Value": Z}]
            """

            # Call the Gemini model with the input prompt and image
            analysis_result = get_gemini_response(input_prompt, image_data)

            try:
                # Parse analysis_result only if it's valid JSON
                data = json.loads(analysis_result)
                fig = create_pie_chart(data)

                # Convert plot to base64 for rendering in HTML
                buffer = BytesIO()
                fig.savefig(buffer, format='png')
                buffer.seek(0)
                pie_chart_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
                buffer.close()

            except json.JSONDecodeError:
                # Handle invalid JSON response here
                print("Error: Response from Gemini model is not valid JSON.")
                analysis_result = None
                pie_chart_image = None


            # # Convert plot to base64 for rendering in HTML
            # buffer = BytesIO()
            # fig.savefig(buffer, format='png')
            # buffer.seek(0)
            # pie_chart_image = base64.b64encode(buffer.getvalue()).decode('utf-8')
            # buffer.close()
        
        # Proceed with additional analysis or response handling
        input_prompt_2 = f"""
            You are an expert nutritionist.  You need to analyze the packaged food item by the list of ingredients & nutritional values i.e {analysis_result} and calculate the total calories. Provide details of each food item with calorie intake in the following format:
            1. Item 1 - number of calories
            2. Item 2 - number of calories
            ---

            As an an expert nutritionist, please provide me a detailed analysis of the nutritional value and health impacts in line-by-line, bullet-point format. 
            Finally, You must have mention whether the food is healthy or not for me as my Age is {age} years, my Weight is  {weight} kg and disease: {my_disease}. Also whether this product is suitable for daily, weekly, or monthly consumption.
        """ 

        response2 = model.generate_content(input_prompt_2)

        # Assuming 'response2' is the object returned from 'model.generate_content'
        if response2 and hasattr(response2, '_result'):
            # Extract the text content from the response object
            content = response2._result.candidates[0].content.parts[0].text
        else:
            content = "No response generated."

        # Convert Markdown to HTML
        html_content = markdown.markdown(content)

    else:
        form = AnalysisForm()
        uploaded_image = UploadedImage.objects.first()

    return render(request, 'home.html', {
        'form': form,
        # 'analysis_result': analysis_result,
        'uploaded_image': uploaded_image,
        'pie_chart_image': pie_chart_image,
        'response2' : html_content,
    })





# clear_data view
import shutil

def clear_data(request):
    if request.method == "POST":
        # Delete the database entry
        UploadedImage.objects.all().delete()

        # Delete all images in the uploaded_images directory
        image_dir = os.path.join(settings.MEDIA_ROOT, 'uploaded_images')
        if os.path.exists(image_dir):
            shutil.rmtree(image_dir)  # Deletes the folder and its contents
            os.makedirs(image_dir)  # Recreate the folder to allow future uploads

        return redirect('home')  # Redirect back to the main page

    return redirect('home')


Team_Members = [
    {'name' : 'Khan Mohammad Huzaif Javeed', 'role' : 'Team Lead' ,'domain': 'Backend', 'TechStack': 'Django'},
    {'name' : 'Shaikh Raees Ahmed Iqbal Ahmed', 'role' : 'Team member' ,'domain': 'Backend', 'TechStack': 'Django'},
    {'name' : 'Akshay Vikram Patil', 'role' : 'Team member' ,'domain': 'Frontend', 'TechStack': 'React'},
    {'name' : 'Rohan Ravindra Chaudhari', 'role' : 'Team member' ,'domain': 'Frontend', 'TechStack': 'React'},
]
def about(request):
    return render(request, 'about.html', context = {'Team_Members' : Team_Members})
