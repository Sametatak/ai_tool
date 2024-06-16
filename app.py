from flask import Flask, render_template, request
import os

app = Flask(__name__)

# Define the directory containing the processed files
content_dir = './scraped_content/'

# Function to read the content of the files
def read_content(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Route for the main page
@app.route('/', methods=['GET', 'POST'])
def index():
    products = [
        "Cooking Appliances: Freestanding Oven",
        "Cooking Appliances: Built-In Oven",
        "Cooking Appliances: Cooktop",
        "Cooking Appliances: Cooking Range",
        "Cooling/Freezing: Refrigerator",
        "Cooling/Freezing: Freezer",
        "Cooling/Freezing: Bottle Cooler",
        "Washing Machine: Washing Machine",
        "Dishwasher: Dishwasher",
        "Dryer: Dryer",
        "Television: Television"
    ]
    
    selected_product = request.form.get('product') if request.method == 'POST' else None
    content = ""
    
    if selected_product:
        category, subcategory = selected_product.split(": ")
        file_name = f"{category.replace(' ', '_')}_{subcategory.replace(' ', '_')}_relevant_info.txt"
        print(file_name)
        file_path = os.path.join(content_dir, file_name)
        print(file_path)
        if os.path.exists(file_path):
            content = read_content(file_path)
        else:
            content = "No content available for the selected product."

    return render_template('index.html', products=products, content=content)

if __name__ == '__main__':
    app.run(debug=True)
