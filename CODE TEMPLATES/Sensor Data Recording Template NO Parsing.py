import requests
import csv
import time
from datetime import datetime
#This is for grabbing sensor data that requires parsing 
#Please read the How do document if you have questions on how to use the script: https://docs.google.com/presentation/d/1iMbYS8Qr2FzbVCUYkNU6Tmg0gEijqlrd-YdwmXw0os4/edit?usp=sharing

# The URL you input here is the "Request URL" from swagger for the sensor you are trying to pull a request from 
url = "http://test-ela.local:4030/firmwareCom/sensor/microBufferMin" #This example address is for grabbing the Microbuffer Sensor Value 


# CSV file path to write data. PLEASE REPLACE WITH THE FILE PATH TO THE LOCATION WHERE YOU WANT TO CSV TO SAVE, BUT ALSO WRITE THE NAME.CSV OF THE FILE YOU WANT THE SCRIPT TO CREATE
csv_file = r"C:\Users\andre\OneDrive\Desktop\Dell Desktop\Test.csv"


def get_sensor_data_and_write_to_csv():
    try:
        
        response = requests.get(url)
        
        # Check if the request was successful
        if response.status_code == 200:
            sensor_data = response.json()       
            data_to_write = [datetime.now().strftime('%Y-%m-%d %H:%M:%S'), sensor_data]
            
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
    time.sleep(1)  # MODIFY THIS TO MATCH THE INTERVALS THAT YOU WANT TO WRITE THE SENSOR VALUES TO THE CSV. FOR EXAMPLE THE CURRENT INTERVAL IS 1second
