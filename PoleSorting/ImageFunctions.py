import os
from exiftool import ExifToolHelper
import math
from shapely.geometry import Polygon, Point
import shutil
import csv
from geopy.distance import geodesic

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

def extract_image_metadata(folder_path):
    #initialize as dictionary
    image_metadata = {}
    #find images, get their metadata, find the xy coords, ensure it exists, store in dictionary under the filename
    with ExifToolHelper() as et:
        for filename in os.listdir(folder_path):
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.tiff')):
                image_path = os.path.join(folder_path, filename)

                metadata = et.get_metadata(image_path)
                for data in metadata:
                    if data.get('EXIF:Make') == "DJI":
                        gps_lat = data.get('XMP:GPSLatitude')
                        gps_lon = data.get('XMP:GPSLongitude')
                        gimbal_yaw = data.get('XMP:GimbalYawDegree')
                        gimbal_tilt = data.get('XMP:GimbalPitchDegree')

                        if gps_lat is not None and gps_lon is not None and gimbal_yaw is not None and gimbal_tilt is not None:
                            image_metadata[filename] = {
                                'XMP:GPSLatitude': gps_lat,
                                'XMP:GPSLongitude': gps_lon,
                                'XMP:GimbalYawDegree': gimbal_yaw,
                                'XMP:GimbalPitchDegree': gimbal_tilt}

                    elif data.get('EXIF:Make') == "Skydio":
                        gps_lat = data.get('XMP:LatitudeRaw')
                        gps_lon = data.get('XMP:LongitudeRaw')
                        gimbal_yaw = data.get('XMP:VehicleOrientationNEDYaw')
                        gimbal_tilt = data.get('XMP:CameraOrientationNEDPitch')

                        if gps_lat is not None and gps_lon is not None and gimbal_yaw is not None and gimbal_tilt is not None:
                            image_metadata[filename] = {
                                'XMP:GPSLatitude': gps_lat,
                                'XMP:GPSLongitude': gps_lon,
                                'XMP:GimbalYawDegree': gimbal_yaw,
                                'XMP:GimbalPitchDegree:': gimbal_tilt}
    return image_metadata

#if yaw below X, use this
def create_trapezoid(metadata_dict):
    trapezoid_data = {}
    for filename, data in metadata_dict.items():
        gps_lat = float(data['XMP:GPSLatitude'])
        gps_lon = float(data['XMP:GPSLongitude'])
        yaw_degree = float(data['XMP:GimbalYawDegree'])
        yaw_rad = math.radians(yaw_degree)

        dx = math.cos(yaw_rad)
        dy = math.sin(yaw_rad)
        perp_dx = -dy
        perp_dy = dx
        point1 = geodesic(meters=10).destination((gps_lat, gps_lon), math.degrees(math.atan2(perp_dy, perp_dx)))
        point2 = geodesic(meters=10).destination((gps_lat, gps_lon), math.degrees(math.atan2(-perp_dy, -perp_dx)))
        forward_point = geodesic(meters=20).destination((gps_lat, gps_lon), yaw_degree)
        point4 = geodesic(meters=20).destination((forward_point.latitude, forward_point.longitude), math.degrees(math.atan2(perp_dy, perp_dx)))
        point3 = geodesic(meters=20).destination((forward_point.latitude, forward_point.longitude), math.degrees(math.atan2(-perp_dy, -perp_dx)))
        trapezoid_data[filename] = [(point1.latitude, point1.longitude), (point2.latitude, point2.longitude),
                                    (point3.latitude, point3.longitude), (point4.latitude, point4.longitude)]
    return trapezoid_data

#for images that are looking practically straight down, if yaw above y, use this
def create_square(metadata_dict):
    square_data = {}

def match_pole_to_trapezoid(trapezoids, pole_data):
    inside_poles = {trapezoid_name: [] for trapezoid_name in trapezoids}
    no_poles = []
    multiple_poles = {}

    #for each trapezoid,
    for trapezoid_name, trapezoid_points in trapezoids.items():
        #make a polygon
        trapezoid = Polygon(trapezoid_points)

        #for each pole,
        for pole_id, pole_point in pole_data.items():
            #create a point
            point = Point(pole_point)

            #see if that point is in the polygon, if yes, append the pole name to the list
            if trapezoid.contains(point):
                inside_poles[trapezoid_name].append(pole_id)

        #if there's no poles attached, move it to no_poles
        if not inside_poles[trapezoid_name]:
            no_poles.append(trapezoid_name)
            del inside_poles[trapezoid_name]

        #same for multiple, multiple_poles

        elif len(inside_poles[trapezoid_name]) > 1:
            multiple_poles[trapezoid_name] = inside_poles.pop(trapezoid_name)

    return inside_poles, no_poles, multiple_poles

def sort_into_folders(inside_poles, no_poles, multiple_poles, sorted_destination_folder, destination_folder, folder_path):
    #for each image trapezoid, if it has a match,
    for trapezoid_name, pole_ids in inside_poles.items():
        if pole_ids:
            for pole_id in pole_ids:
                #make a pole folder if there isnt one
                pole_folder = os.path.join(sorted_destination_folder, pole_id)
                os.makedirs(pole_folder, exist_ok=True)

                #move image to that folder
                source_path = os.path.join(folder_path, trapezoid_name)
                destination_path = os.path.join(pole_folder, trapezoid_name)

                try:
                    shutil.move(source_path, destination_path)
                    #print(f'Moved {source_path} to {destination_path}')
                except FileNotFoundError as e:
                    print(f'Error: {e}. Source: {source_path}')

    for trapezoid_name in no_poles:
        source_path = os.path.join(folder_path, trapezoid_name)
        destination_path = os.path.join(destination_folder, 'no_pole', trapezoid_name)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        try:
            shutil.move(source_path, destination_path)
        except FileNotFoundError as e:
            print(f'Error: {e}. Source: {source_path}')

    for trapezoid_name, pole_ids in multiple_poles.items():
        source_path = os.path.join(folder_path, trapezoid_name)
        destination_path = os.path.join(destination_folder, 'multiple_poles', trapezoid_name)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        try:
            shutil.move(source_path, destination_path)
        except FileNotFoundError as e:
            print(f'Error: {e}. Source: {source_path}')