import requests
import csv
import time
from datetime import datetime

# URL to make the GET request
url = "http://changeme-f8dc7a9fa43c.local:4030/vanguard/envSensor/5"

# CSV file path to write data
csv_file = r"C:\Users\Andre\OneDrive\Desktop\Material Pod Testing Scripts\Mositure Testing Script\Lid Testing O5 May 2024\InsideMPHumidData.csv"

# Function to make HTTP request and write data to CSV file
def get_sensor_data_and_write_to_csv():
    try:
        # Make GET request
        response = requests.get(url) 
        
        # Check if the request was successful
        if response.status_code == 200:
            # Parse JSON response
            sensor_data = response.json()
            
            # Extract data from JSON response
            # Modify the following line according to the structure of your JSON response
            data_to_write = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), sensor_data["humidity"], sensor_data["temperature"]]
            
            # Write data to CSV file
            with open(csv_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data_to_write)
                
            print("Data written to CSV successfully.")
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the script every minute
while True:
    get_sensor_data_and_write_to_csv()
    time.sleep(1800)  # Sleep for 60 seconds (1 minute)
