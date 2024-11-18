import requests
import csv
import time
from datetime import datetime
#This is for grabbing sensor data that requires parsing 
#Please read the How do document if you have questions on how to use the script: https://docs.google.com/presentation/d/1iMbYS8Qr2FzbVCUYkNU6Tmg0gEijqlrd-YdwmXw0os4/edit?usp=sharing

# The URL you input here is the "Request URL" from swagger for the sensor you are trying to pull a request from 
url = "http://fowx-el.local:4030/state" #This example address is for a Material Pod attached to Test ELA in slot zero, and it is grabbing the enviromental sensor data


# CSV file path to write data. PLEASE REPLACE WITH THE FILE PATH TO THE LOCATION WHERE YOU WANT TO CSV TO SAVE, BUT ALSO WRITE THE NAME.CSV OF THE FILE YOU WANT THE SCRIPT TO CREATE. 
# In this example the script would create a csv file called Humid_data.csv and would write it to a folder on my desktop 
csv_file = r"C:\Users\andre\OneDrive\Desktop\GitHub Code\AndysCodeREPO\PH Thermal Runaway Testing\Sensor Data Log\ThermalRunawaySensorLog.csv"


def get_sensor_data_and_write_to_csv():
    try:
        
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:# Assuming 'response' is the result from the HTTP request
            # Parse JSON response
            sensor_data = response.json()
            
            # Navigate to the specific fields for nozzle, bed, and chamber actual temperatures
            nozzle_actual = sensor_data["data"]["apollo"]["context"]["temperatures"]["nozzle"]["actual"]
            bed_actual = sensor_data["data"]["apollo"]["context"]["temperatures"]["bed"]["actual"]
            chamber_actual = sensor_data["data"]["apollo"]["context"]["temperatures"]["chamber"]["actual"]
            
            # Prepare data to write to CSV
            data_to_write = [
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                nozzle_actual,
                bed_actual,
                chamber_actual
            ]
            
            # Write data to CSV file
            with open(csv_file, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(data_to_write)
            
            print("Data written to CSV successfully.")
        else:
            print(f"Failed to retrieve data. Status code: {response.status_code}")
    except Exception as e:
        print(f"An error occurred: {e}")


while True:
    get_sensor_data_and_write_to_csv()
    time.sleep(5)  # MODIFY THIS TO MATCH THE INTERVALS THAT YOU WANT TO WRITE THE SENSOR VALUES TO THE CSV. FOR EXAMPLE THE CURRENT INTERVAL IS 1800 SECONDS (30 MINUTES)
