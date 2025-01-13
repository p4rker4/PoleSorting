import os
from exiftool import ExifToolHelper
import math
import geopandas as gpd
from shapely.geometry import Polygon, Point
from Functions import read_pole_data
import shutil

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
                    gps_lat = data.get('XMP:GPSLatitude')
                    gps_lon = data.get('XMP:GPSLongitude')
                    gimbal_yaw = data.get('XMP:GimbalYawDegree')

                    if gps_lat is not None and gps_lon is not None and gimbal_yaw is not None:
                        image_metadata[filename] = {
                            'XMP:GPSLatitude': gps_lat,
                            'XMP:GPSLongitude': gps_lon,
                            'XMP:GimbalYawDegree': gimbal_yaw
                        }
    return image_metadata

def create_trapezoid(metadata_dict, distance_outward=25, short_side_length=20, long_side_length=50):
    #initialize blank dictionary
    trapezoid_data = {}

    for filename, data in metadata_dict.items():
        #convert from str to float
        gps_lat = float(data['XMP:GPSLatitude'])
        gps_lon = float(data['XMP:GPSLongitude'])
        yaw_degree = float(data['XMP:GimbalYawDegree'])

        #convert yaw to radians
        yaw_rad = math.radians(yaw_degree)

        lat_offset_outward = distance_outward / 111000
        lon_offset_outward = distance_outward / 111000

        lat_offset_short = (short_side_length / 2) / 111000
        lon_offset_short = (short_side_length / 2) / (111000 * math.cos(math.radians(gps_lat)))

        lat_offset_long = (long_side_length / 2) / 111000
        lon_offset_long = (long_side_length / 2) / (111000 * math.cos(math.radians(gps_lat)))

        corners =[
        (gps_lat + lat_offset_short * math.cos(yaw_rad) -lat_offset_outward * math.sin(yaw_rad),
        gps_lon + lon_offset_short * math.sin(yaw_rad) - lon_offset_outward * math.cos(yaw_rad)),
        (gps_lat - lat_offset_short * math.cos(yaw_rad) - lat_offset_outward * math.sin(yaw_rad),
        gps_lon - lon_offset_short * math.sin(yaw_rad) - lon_offset_outward * math.cos(yaw_rad)),
        (gps_lat - lat_offset_long * math.cos(yaw_rad) + lat_offset_outward * math.sin(yaw_rad),
        gps_lon - lon_offset_long * math.sin(yaw_rad) + lon_offset_outward * math.cos(yaw_rad)),
        (gps_lat + lat_offset_long * math.cos(yaw_rad) + lat_offset_outward * math.sin(yaw_rad),
         gps_lon + lon_offset_long * math.sin(yaw_rad) + lon_offset_outward * math.cos(yaw_rad))
        ]

        trapezoid_data[filename] = corners


    return trapezoid_data

def match_pole_to_trapezoid(trapezoids, pole_data):
    inside_poles = {trapezoid_name: [] for trapezoid_name in trapezoids}
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
    return inside_poles

def sort_into_folders(inside_poles, destination_folder, folder_path):
    #for each image trapezoid, if it has a match,
    for trapezoid_name, pole_ids in inside_poles.items():
        if pole_ids:
            for pole_id in pole_ids:
                #make a pole folder if there isnt one
                pole_folder = os.path.join(destination_folder, pole_id)
                os.makedirs(pole_folder, exist_ok=True)

                #move image to that folder
                source_path = os.path.join(folder_path, trapezoid_name)
                destination_path = os.path.join(pole_folder, trapezoid_name)

                #error if the image doesn't exist for some reason
                if os.path.exists(source_path):
                    shutil.move(source_path, destination_path)
                    print(f"Moved {trapezoid_name} to {pole_folder}")
                else:
                    print(f"Warning: {trapezoid_name} not found in {source_folder}")