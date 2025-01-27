import os
from exiftool import ExifToolHelper
import math
import geopandas as gpd
from shapely.geometry import Polygon, Point
import shutil
from geopy.distance import geodesic

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

def match_pole_to_trapezoid(trapezoids, pole_data):
    inside_poles = {trapezoid_name: [] for trapezoid_name in trapezoids}
    outside_poles = []

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

        if not inside_poles[trapezoid_name]:
            outside_poles.append(trapezoid_name)

    return inside_poles, outside_poles

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

                shutil.move(source_path, destination_path)

