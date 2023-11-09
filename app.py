import os
import random
import string
import subprocess
import logging
import csv
from io import TextIOWrapper
from flask import Flask, request, flash, render_template, redirect, jsonify, session, send_from_directory, url_for
from werkzeug.utils import secure_filename
import io
import zipfile
import sqlite3
import shutil
from datetime import datetime

app = Flask(__name__)
app.debug = True
app.secret_key = 'Is1S3cr3tk3y'

logging.basicConfig(level=logging.INFO)

# Database Configuration
DATABASE = './static/projectdb.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_clients_table():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_number TEXT,
            client_name TEXT,
            address_line_1 TEXT,
            address_line_2 TEXT,
            town_city TEXT,
            county TEXT,
            postcode TEXT,
            phone_number TEXT,
            status TEXT,
            date_stamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_equipment_table():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_number TEXT,
            client_account_number TEXT,
            equipment_type TEXT,
            equipment_sub_type TEXT,
            serial_number TEXT,
            client_asset_id TEXT,
            sub_location TEXT,
            safe_working_load REAL,
            inspection_frequency TEXT,
            year_of_manufacture INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_client_details(account_number):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM clients WHERE account_number = ?', (account_number,))
    client_details = cursor.fetchone()
    conn.close()
    return dict(client_details) if client_details else None

def get_equipment_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment')
    equipment_list = cursor.fetchall()
    conn.close()
    return equipment_list

def generate_equipment_number():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(equipment_number) FROM equipment')
    last_equipment_number = cursor.fetchone()[0]

    if last_equipment_number is not None:
        numeric_part = int(last_equipment_number[3:])
        new_numeric_part = numeric_part + 1
        new_equipment_number = f'EQP{str(new_numeric_part).zfill(3)}'
    else:
        new_equipment_number = 'EQP000'

    conn.close()
    return new_equipment_number

def get_all_clients():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, client_name FROM clients')
    clients = cursor.fetchall()
    conn.close()
    return clients

@app.route('/', methods=['GET'])
def root():
    return render_template('index.html')

# Client Functions
@app.route('/clients')
def clients():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    success_message = request.args.get('success', '')
    error_message = request.args.get('error', '')
    clients_per_page = 25  # Number of clients to show per page

    conn = get_db()

    if search_query:
        # Implement filtering based on the search query
        query = '''
            SELECT * FROM clients
            WHERE account_number LIKE ? OR client_name LIKE ? OR address_line_1 LIKE ?
            OR address_line_2 LIKE ? OR town_city LIKE ? OR county LIKE ?
            OR postcode LIKE ? OR phone_number LIKE ? OR status LIKE ?
            ORDER BY id
            LIMIT ? OFFSET ?
        '''
        search_params = (f"%{search_query}%",) * 8 + (clients_per_page, (page - 1) * clients_per_page)
        clients = conn.execute(query, search_params).fetchall()
    else:
        clients = conn.execute('''
            SELECT * FROM clients
            ORDER BY id
            LIMIT ? OFFSET ?
        ''', (clients_per_page, (page - 1) * clients_per_page)).fetchall()

    total_clients = conn.execute('SELECT COUNT(*) FROM clients').fetchone()[0]
    total_pages = (total_clients + clients_per_page - 1) // clients_per_page

    conn.close()
    return render_template('clients.html', clients=clients, success_message=success_message, error_message=error_message, total_pages=total_pages, current_page=page)

@app.route('/save-client', methods=['POST'])
def save_client():
    if request.method == 'POST':
        try:
            # Get data from the form
            account_number = request.form['account_number']
            client_name = request.form['client_name']
            address_line_1 = request.form['address_line_1']
            address_line_2 = request.form['address_line_2']
            town_city = request.form['town_city']
            county = request.form['county']
            postcode = request.form['postcode']
            phone_number = request.form['phone_number']
            status = request.form['status']
            date_stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Save the client data to the database
            conn = get_db()
            conn.execute('''
                INSERT INTO clients (account_number, client_name, address_line_1, address_line_2, town_city, county, postcode, phone_number, status, date_stamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (account_number, client_name, address_line_1, address_line_2, town_city, county, postcode, phone_number, status, date_stamp))
            conn.commit()
            conn.close()

            success_message = "Client added successfully."
            session['success_message'] = success_message
        except Exception as e:
            error_message = str(e)
            session['error_message'] = error_message

    return redirect('/clients')

@app.route('/client-details/<account_number>')
def client_details(account_number):
    # Fetch client details for the specified account_number
    client_details = get_client_details(account_number)  # Implement this function

    # Render the client details page with the client_details data
    return render_template('client_details.html', client_details=client_details)

@app.route('/update-client', methods=['POST'])
def update_client():
    if request.method == 'POST':
        try:
            # Get data from the form
            account_number = request.form['account_number']
            client_name = request.form['client_name']
            address_line_1 = request.form['address_line_1']
            address_line_2 = request.form['address_line_2']
            town_city = request.form['town_city']
            county = request.form['county']
            postcode = request.form['postcode']
            phone_number = request.form['phone_number']
            status = request.form['status']

            # Update the client data in the database
            conn = get_db()
            conn.execute('''
                UPDATE clients
                SET client_name=?, address_line_1=?, address_line_2=?, town_city=?, county=?, postcode=?, phone_number=?, status=?
                WHERE account_number=?
            ''', (client_name, address_line_1, address_line_2, town_city, county, postcode, phone_number, status, account_number))
            conn.commit()
            conn.close()

            success_message = "Client updated successfully."
            session['success_message'] = success_message
        except Exception as e:
            error_message = str(e)
            session['error_message'] = error_message

    return redirect('/clients')

@app.route('/upload-equipment', methods=['POST'])
def upload_equipment():
    if 'csv_file' in request.files:
        try:
            # Process the uploaded CSV file
            equipment_data = process_equipment_csv(request.files['csv_file'])
            
            # Insert equipment data into the database
            insert_equipment_from_csv(equipment_data)
            
            flash('CSV file uploaded and equipment details added successfully', 'success')
        except Exception as e:
            flash(f'Error processing CSV file: {str(e)}', 'error')

    return redirect('/equipment')

def insert_equipment_from_csv(equipment_data):
    conn = get_db()
    cursor = conn.cursor()
    
    for equipment in equipment_data:
        cursor.execute('''
            INSERT INTO equipment (equipment_number, client_account_number, equipment_type, equipment_sub_type, serial_number)
            VALUES (?, ?, ?, ?, ?)
        ''', (equipment['equipment_number'], equipment['client_account_number'], equipment['equipment_type'], equipment['equipment_sub_type'], equipment['serial_number']))
    
    conn.commit()
    conn.close()

def process_equipment_csv(file):
    equipment_data = []

    csv_file = TextIOWrapper(file, encoding='utf-8')
    csv_reader = csv.DictReader(csv_file)

    for row in csv_reader:
        print("CSV Row:", row)
        # Check if 'client_account_number' is in the CSV row (without the BOM character)
        if 'client_account_number' not in row:
            raise ValueError("Missing 'client_account_number' in CSV row")

        # Extract Info (use 'client_account_number' as the column name)
        client_account_number = row.get('client_account_number', 'Unknown')
        equipment_number = row.get('equipment_number', 'Unknown')
        equipment_type = row.get('equipment_type', 'Unknown')
        equipment_sub_type = row.get('equipment_sub_type', 'Unknown')
        serial_number = row.get('serial_number', 'Unknown')
        client_asset_id = row.get('client_asset_id', 'Unknown')
        sub_location = row.get('sub_location', 'Unknown')
        safe_working_load = row.get('safe_working_load', 'Unknown')
        inspection_frequency = row.get('inspection_frequency', 'Unknown')
        year_of_manufacture = row.get('year_of_manufacture', 'Unknown')

        equipment_data.append({
            'equipment_number': equipment_number,
            'client_account_number': client_account_number,
            'equipment_type': equipment_type,
            'equipment_sub_type': equipment_sub_type,
            'serial_number': serial_number,
            'client_asset_id': client_asset_id,
            'sub_location': sub_location,
            'safe_working_load': safe_working_load,
            'inspection_frequency': inspection_frequency,
            'year_of_manufacture': year_of_manufacture,
        })


    return equipment_data

# Function to fetch equipment data
def get_equipment_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT equipment.*, clients.client_name
        FROM equipment
        INNER JOIN clients ON equipment.client_account_number = clients.account_number
    ''')
    equipment = cursor.fetchall()
    conn.close()
    return equipment

# Function to fetch equipment details based on equipment_id
def get_equipment_details(equipment_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment WHERE id = ?', (equipment_id,))
    equipment_details = cursor.fetchone()
    conn.close()
    return dict(equipment_details) if equipment_details else None

def get_client_list():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, client_name FROM clients')
    clients = cursor.fetchall()
    conn.close()
    return clients

# Function to insert equipment data
def insert_equipment(equipment_number, client_id, equipment_type, equipment_sub_type, serial_number, client_asset_id, sub_location, safe_working_load, inspection_frequency, year_of_manufacture):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO equipment (equipment_number, client_id, equipment_type, equipment_sub_type, '
                   'serial_number, client_asset_id, sub_location, safe_working_load, inspection_frequency, year_of_manufacture) '
                   'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                   (equipment_number, client_id, equipment_type, equipment_sub_type, serial_number, client_asset_id, sub_location,
                    safe_working_load, inspection_frequency, year_of_manufacture))
    conn.commit()
    cursor.close()

@app.route('/equipment_details/<equipment_number>')
def equipment_details(equipment_number):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM equipment WHERE equipment_number = ?', (equipment_number,))
    equipment_details = cursor.fetchone()

    if equipment_details is None:
        flash('Equipment not found', 'error')
        return redirect('/equipment')

    # Fetch client name using equipment_details['account_number']
    cursor.execute('SELECT client_name FROM clients WHERE account_number = ?', (equipment_details['client_account_number'],))
    client_name = cursor.fetchone()[0]

    conn.close()

    return render_template('equipment_details.html', equipment_details=equipment_details, client_name=client_name)

@app.route('/update-equipment', methods=['POST'])
def update_equipment():
    if request.method == 'POST':
        equipment_number = request.form.get('equipment_number')
        client_id = request.form.get('client_id')
        equipment_type = request.form.get('equipment_type')
        equipment_sub_type = request.form.get('equipment_sub_type')
        serial_number = request.form.get('serial_number')
        client_asset_id = request.form.get('client_asset_id')
        sub_location = request.form.get('sub_location')
        safe_working_load = request.form.get('safe_working_load')
        inspection_frequency = request.form.get('inspection_frequency')
        year_of_manufacture = request.form.get('year_of_manufacture')

        try:
            conn = get_db()
            sql_query = '''
                UPDATE equipment
                SET equipment_type=?, equipment_sub_type=?, serial_number=?, client_asset_id=?, 
                sub_location=?, safe_working_load=?, inspection_frequency=?, year_of_manufacture=?
                WHERE equipment_number=?
            '''
            conn.execute(sql_query, (equipment_type, equipment_sub_type, serial_number, client_asset_id, sub_location,
                safe_working_load, inspection_frequency, year_of_manufacture, equipment_number))
            conn.commit()
            conn.close()

            success_message = "Equipment updated successfully."
            session['success_message'] = success_message
        except Exception as e:
            error_message = str(e)
            session['error_message'] = error_message

    return redirect('/equipment')

@app.route('/equipment')
def equipment():
    equipment = get_equipment_list()
    clients = get_all_clients()

    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str)
    items_per_page = 25

    if search_query:
        equipment = [item for item in equipment if search_query.lower() in str(item).lower()]

    total_items = len(equipment)
    total_pages = (total_items + items_per_page - 1) // items_per_page

    start_index = (page - 1) * items_per_page
    end_index = start_index + items_per_page
    equipment_page = equipment[start_index:end_index]

    return render_template(
        'equipment.html',
        equipment=equipment_page,
        clients=clients,
        total_pages=total_pages,
        current_page=page,
        search_query=search_query
    )

@app.route('/equipment/create', methods=['POST'])
def create_equipment():
    if request.method == 'POST':

        # Process the uploaded CSV file and obtain equipment data
        equipment_data = process_equipment_csv(request.files['csv_file'])

        # Insert equipment data into the database, including client_id from CSV
        for equipment in equipment_data:
            equipment_number = equipment['equipment_number']
            client_id = equipment['client_id']
            equipment_type = equipment['equipment_type']
            equipment_sub_type = equipment['equipment_sub_type']
            serial_number = equipment['serial_number']
            client_asset_id = equipment['client_asset_id']
            sub_location = equipment['sub_location']
            safe_working_load = equipment['safe_working_load']
            inspection_frequency = equipment['inspection_frequency']
            year_of_manufacture = equipment['year_of_manufacture']

            insert_equipment(equipment_number, client_id, equipment_type, equipment_sub_type, serial_number,
                             client_asset_id, sub_location, safe_working_load, inspection_frequency, year_of_manufacture)


        response_data = {"message": "Equipment added successfully."}
        return jsonify(response_data)
        return redirect('/equipment')


@app.route('/equipment/search', methods=['GET'])
def equipment_search():
    search_query = request.args.get('search', '')
    equipment = get_equipment_list()

    if search_query:
        equipment = [item for item in equipment if search_query.lower() in str(item).lower()]

    return jsonify(equipment)

create_equipment_table()
create_clients_table()

if __name__ == "__main__":
    import socket

    def is_valid_ip(ip):
        try:
            socket.inet_aton(ip)
            return True
        except socket.error:
            return False

    ip_address = None
    while True:
        ip_address = input("Enter the IP address to run the app (e.g., 0.0.0.0): ")
        if is_valid_ip(ip_address):
            break
        else:
            print("Invalid IP address. Please enter a valid IP address.")

    print(f"Running the app at IP address: {ip_address}")

    app.secret_key = 'Is1S3cr3tk3y'
    app.run(host=ip_address, port=5000)