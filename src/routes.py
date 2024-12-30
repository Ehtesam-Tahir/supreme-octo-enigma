import os
import requests
from flask import render_template, request, redirect, url_for, flash
from lapp import app, service  # Import the app and service from __init__.py
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import threading

# Function to fetch images asynchronously
def fetch_image(img_src, images_list):
    try:
        img_response = requests.get(img_src, timeout=5)
        img_response.raise_for_status()
        img_data = Image.open(BytesIO(img_response.content))
        width, height = img_data.size
        if width > 600 or height > 600:  # Include only images with resolution greater than 600
            images_list.append(img_src)
    except requests.RequestException as e:
        print(f"Error fetching {img_src}: {e}")
    except Exception as e:
        print(f"Error processing image {img_src}: {e}")

# Fetch images based on their resolution from a URL
def fetch_images_from_url(url):
    images = []
    threads = []

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        img_tags = soup.find_all('img')

        for img in img_tags:
            img_src = img.get('src')
            if img_src:
                if "logo" in img_src.lower():  # Exclude images containing "logo"
                    continue
                if img_src.startswith('data:image'):
                    continue
                if img_src.startswith('//'):
                    img_src = 'https:' + img_src
                elif not img_src.startswith(('http://', 'https://')):
                    img_src = 'https://' + img_src
                
                if not img_src.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):  # Image file formats
                    continue

                # Use a thread to fetch the image
                thread = threading.Thread(target=fetch_image, args=(img_src, images))
                thread.start()
                threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")

    return images

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/set_sheet_id', methods=['POST'])
def set_sheet_id():
    global SPREADSHEET_ID
    SPREADSHEET_ID = request.form.get('sheet_id')
    return redirect(url_for('view_images'))

@app.route('/view_images', methods=['GET', 'POST'])
def view_images():
    global current_row
    if not SPREADSHEET_ID:
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'navigate_to_row' in request.form:  # Handle navigation to a specific row
            new_row = request.form.get('row_navigation')
            if new_row.isdigit():
                current_row = int(new_row)
                return redirect(url_for('view_images'))

        selected_links = request.form.to_dict()
        product_name = request.form.get('product_name', '').strip()
        row_data = [''] * 10  # Exactly 10 columns: C to L

        # Map selections to columns
        for img, value in selected_links.items():
            if value.startswith('p'):
                col_index = int(value[1]) - 1  # p1 -> 0, p2 -> 1
                row_data[col_index] = img
            elif value.startswith('l'):
                col_index = int(value[1]) + 4  # l1 -> 5, l2 -> 6
                row_data[col_index] = img

        # Ensure the row_data length matches the range
        row_data = row_data[:10]  # Truncate if too long
        while len(row_data) < 10:
            row_data.append('')  # Fill missing entries with empty strings

        # Push row data to Google Sheets
        sheet = service.spreadsheets().values()
        range_to_update = f'Sheet1!C{current_row}:L{current_row}'
        body = {"values": [row_data]}
        sheet.update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_to_update,
            valueInputOption="RAW",
            body=body
        ).execute()

        # Update product name in column B
        if product_name:
            product_range = f'Sheet1!B{current_row}'
            product_body = {"values": [[product_name]]}
            sheet.update(
                spreadsheetId=SPREADSHEET_ID,
                range=product_range,
                valueInputOption="RAW",
                body=product_body
            ).execute()

        # Handle row navigation
        new_row = request.form.get('row_navigation', '')
        if new_row.isdigit():
            current_row = int(new_row)
        else:
            current_row += 1  # Default to next row if invalid or empty input

        return redirect(url_for('view_images'))  # Redirect to prevent re-submission

    # Back button logic: Go to previous row
    if request.args.get('action') == 'back':
        current_row = max(current_row - 1, 2)  # Ensure the row is >= 2

    # Fetch the current link to process (column A)
    sheet = service.spreadsheets().values()
    result = sheet.get(spreadsheetId=SPREADSHEET_ID, range=f'Sheet1!A{current_row}').execute()
    links = result.get('values', [[]])[0]

    if not links:
        return render_template('no_link.html', current_row=current_row, no_link=True)

    # Fetch image links from the URL
    url = links[0]
    images = fetch_images_from_url(url)

    # Check if there is a next link
    next_row_data = sheet.get(spreadsheetId=SPREADSHEET_ID, range=f'Sheet1!A{current_row + 1}').execute()
    next_link = next_row_data.get('values', [[]])[0]

    return render_template('view_images.html', images=images, current_row=current_row, next_link=next_link)

@app.route('/no_link', methods=['GET', 'POST'])
def no_link():
    if request.method == 'POST':
        # If user enters a row number to go to
        new_row = request.form.get('row_number')
        if new_row.isdigit():
            global current_row
            current_row = int(new_row)
        return redirect(url_for('view_images'))

    return render_template('no_link.html', current_row=current_row)
