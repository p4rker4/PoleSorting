import os
import piexif
import csv
from math import sqrt

def get_exif_data(image_file):
    try:
        # Load the EXIF data from the image file
        exif_dict = piexif.load(image_file)
        return exif_dict  # Return the dictionary to be used later
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
                        latitude_deg = latitude_dms[0][0]  # Degrees
                        latitude_min = latitude_dms[1][0]  # Minutes
                        latitude_sec = latitude_dms[2][0] / latitude_dms[2][1]  # Seconds (converted from fraction)

                        longitude_deg = longitude_dms[0][0]  # Degrees
                        longitude_min = longitude_dms[1][0]  # Minutes
                        longitude_sec = longitude_dms[2][0] / longitude_dms[2][1]  # Seconds (converted from fraction)

                        #convert DMS to decimal degrees
                        latitude_dd = dms_to_dd(latitude_deg, latitude_min, latitude_sec)
                        longitude_dd = dms_to_dd(longitude_deg, longitude_min, longitude_sec)

                        #apply the directionality (N/E +, S/W -)
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
    root_folder = input("Enter the root folder location: ")

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
                print(f"Processing pole: {os.path.basename(subfolder_path)}")
                avg_latitude, avg_longitude = get_dd_coordinates(subfolder_path)
                if avg_latitude is not None and avg_longitude is not None:
                    closest_pole, closest_distance = find_closest_pole(avg_latitude, avg_longitude, pole_data)
                    folder_matches[subfolder] = {
                        "average_coordinates": (avg_latitude, avg_longitude),
                        "closest_pole": closest_pole,
                        "distance": closest_distance
                    }
                else:
                    print(f"No valid GPS data found in {subfolder_path}.")

        # Print the results
        print("\nFolder Matches to Closest Poles:")
        for folder, data in folder_matches.items():
            avg_coords = data["average_coordinates"]
            raw_distance = data["distance"]
            distance_in_meters = raw_distance * 111000  # Convert degrees to meters (approximation)
            print(f"{folder}: Lat = {avg_coords[0]:.6f}°, Lon = {avg_coords[1]:.6f}°")
            print(f"Closest Pole: {data['closest_pole']} (Distance: {distance_in_meters:.2f} meters)")
            print('-' * 60)

def calc_distance(lat1, lon1, lat2, lon2):
    return sqrt((lat2 - lat1)**2 + (lon2 - lon1)**2)

def read_pole_data(csv_file):
    pole_data = {}
    try:
        with open(csv_file, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                pole_num = row[0]
                latitude = float(row[1])
                longitude = float(row[2])
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

if __name__ == "__main__":
    csv_file = input("Enter the path to the CSV file containing pole data: ")
    get_and_process_folder(csv_file)