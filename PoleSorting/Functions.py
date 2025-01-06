import os
import piexif
import csv
from math import sqrt
from concurrent.futures import ThreadPoolExecutor

def get_exif_data(image_file):
    try:
        #take the exif data from the image file
        exif_dict = piexif.load(image_file)
        return exif_dict  #return dictionary with the data
    except Exception as e:
        print(f"Error: {e}")
        return None

def dms_to_dd(d, m, s):
    dd = d + float(m) / 60 + float(s) / 3600
    return dd

def get_dd_coordinates(pole_folder):
    #initialize variables
    total_latitude = 0
    total_longitude = 0
    count = 0

    if not os.path.exists(pole_folder):
        print(f"Error: Folder '{pole_folder}' does not exist.")
    else:
        for file_name in os.listdir(pole_folder):
            image_file = os.path.join(pole_folder, file_name)

            if os.path.isfile(image_file) and image_file.lower().endswith(('.jpg', '.jpeg', '.png')):
                exif_dict = get_exif_data(image_file)

                if exif_dict and "GPS" in exif_dict:
                    try:
                        #extracting latlong values
                        latitude_dms = exif_dict["GPS"][2]  # ((degrees, 1), (minutes, 1), (seconds, 10000))
                        longitude_dms = exif_dict["GPS"][4]  # ((degrees, 1), (minutes, 1), (seconds, 10000))

                        #separate D M S
                        latitude_deg = latitude_dms[0][0]  # d
                        latitude_min = latitude_dms[1][0]  # m
                        latitude_sec = latitude_dms[2][0] / latitude_dms[2][1]  # s

                        longitude_deg = longitude_dms[0][0]  # d
                        longitude_min = longitude_dms[1][0]  # m
                        longitude_sec = longitude_dms[2][0] / longitude_dms[2][1]  # s

                        #convert DMS to decimal degrees
                        latitude_dd = dms_to_dd(latitude_deg, latitude_min, latitude_sec)
                        longitude_dd = dms_to_dd(longitude_deg, longitude_min, longitude_sec)

                        #apply the directionality (N/E = +, S/W = -)
                        latitude_dd = latitude_dd if exif_dict["GPS"][1] == b'N' else -latitude_dd
                        longitude_dd = longitude_dd if exif_dict["GPS"][3] == b'E' else -longitude_dd

                        #add latlong, increase count, for use in averaging
                        total_latitude += latitude_dd
                        total_longitude += longitude_dd
                        count += 1
                    except Exception as e:
                        print(f"Error while processing GPS data in {image_file}: {e}")
                else:
                    print(f"No GPS data found in {image_file}.")

    #calculate average coordinates
    if count > 0:
        avg_latitude = total_latitude / count
        avg_longitude = total_longitude / count
        return avg_latitude, avg_longitude
    else:
        return None, None

def get_and_process_folder(csv_file):
    #root_folder = input("Enter the root folder location: ")
    root_folder = "D:/BVES2024"

    if not os.path.exists(root_folder):
        print(f"Error: Path '{root_folder}' does not exist.")
    else:
        pole_data = read_pole_data(csv_file)
        if not pole_data:
            print("No valid pole data found in the CSV file.")
            return

        folder_matches = {}
        for subfolder in os.listdir(root_folder):
            subfolder_path = os.path.join(root_folder, subfolder)
            if os.path.isdir(subfolder_path):
                print(f"Processing folder: {os.path.basename(subfolder_path)}")
                avg_latitude, avg_longitude = get_dd_coordinates(subfolder_path)
                if avg_latitude is not None and avg_longitude is not None:
                    closest_pole, closest_distance = find_closest_pole(avg_latitude, avg_longitude, pole_data)
                    folder_matches[subfolder] = {
                        "average_coordinates": (avg_latitude, avg_longitude),
                        "closest_pole": closest_pole,
                        "distance": closest_distance
                    }
                else:
                    folder_matches[subfolder] = {
                    'average_coordinates': (None, None),
                    'closest_pole': None,
                    'distance': None}

        return folder_matches

def calc_distance(lat1, lon1, lat2, lon2):
    return sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)

def read_pole_data(csv_file):
    pole_data = {}
    pole_count = {}
    try:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  #skip header
            for row in reader:
                pole_num = row[0]
                latitude = float(row[1])
                longitude = float(row[2])

                #check if the pole has a prior instance of the name, if it does, add 1 to its count and append it to the name
                if pole_num in pole_count:
                    pole_count[pole_num] += 1
                    pole_num = f"{pole_num}-{pole_count[pole_num]}"
                else:
                    pole_count[pole_num] = 1

                pole_data[pole_num] = (latitude, longitude)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
    return pole_data

def find_closest_pole(avg_lat, avg_lon, pole_data):
    closest_pole = None
    closest_distance = float('inf')
    for pole_num, (pole_lat, pole_lon) in pole_data.items():
        distance = calc_distance(avg_lat, avg_lon, pole_lat, pole_lon)
        if distance < closest_distance:
            closest_pole = pole_num
            closest_distance = distance
    return closest_pole, closest_distance

def export_to_csv(folder_matches, csv_output_file):
    with open(csv_output_file, mode ='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Folder Name', 'Matched Pole', 'Distance','Latitude', 'Longitude', 'Status'])

        for folder, data in folder_matches.items():
            folder_name = folder
            matched_pole = data['closest_pole']
            distance = (data['distance'] * 111000) if data['distance'] is not None else None
            latitude, longitude = data['average_coordinates']

            if latitude is None and longitude is None:
                status = 'No GPS data'
            elif distance is not None and distance > 10:
                status = 'Matched outside 10m'
            else:
                status = 'Matched'

            writer.writerow([folder_name, matched_pole, distance, latitude, longitude, status])

def extract_pole_from_folder(folder_name):
    # Folder name is expected to be the pole number directly, e.g., 'pole123'
    return folder_name

def validate_manual_sort(folder_matches):
    correct_matches = 0
    incorrect_folders = []

    # Compare the folder name (manual pole) with the auto-assigned pole
    for folder, data in folder_matches.items():
        # Extract the manual pole directly from the folder name
        manual_pole = extract_pole_from_folder(folder)

        # Get the automatically assigned closest pole
        auto_matched_pole = data['closest_pole']

        # If the manual pole is extracted successfully and matches the auto-assigned pole
        if manual_pole and auto_matched_pole:
            if manual_pole == auto_matched_pole:
                correct_matches += 1
            else:
                incorrect_folders.append({
                    'folder': folder,
                    'manual_pole': manual_pole,
                    'auto_matched_pole': auto_matched_pole
                })

    return correct_matches, incorrect_folders

def display_validation_results(correct_matches, incorrect_folders):
    print(f"\nTotal correct matches: {correct_matches}")

    if incorrect_folders:
        print("\nIncorrect matches:")
        for item in incorrect_folders:
            print(f"Manual: {item['manual_pole']} / Auto: {item['auto_matched_pole']}")
    else:
        print("No incorrect matches.")