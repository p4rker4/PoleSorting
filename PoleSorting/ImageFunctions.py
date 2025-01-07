import os
from exiftool import ExifToolHelper
import math
import geopandas as gpd
from shapely.geometry import Polygon

def extract_image_metadata(folder_path):
    image_metadata = {}
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


#create a trapezoid that estimates the drone's view at the time of image capture
def create_trapezoid(metadata_dict, distance=15, width_factor=1.5):
    trapezoid_data = {}

    for filename, data in metadata_dict.items():
        # Convert gps_lat and gps_lon to float before using in calculations
        gps_lat = float(data['XMP:GPSLatitude'])
        gps_lon = float(data['XMP:GPSLongitude'])
        yaw_degree = float(data['XMP:GimbalYawDegree'])

        # Convert yaw from degrees to radians for trigonometric calculations
        yaw_rad = math.radians(yaw_degree)

        # Convert distance to degrees (approximate conversions)
        lat_offset = distance / 111000  # Approximate meters per degree latitude
        lon_offset = distance / (111000 * math.cos(math.radians(gps_lat)))  # Longitude adjustment

        # Generate the trapezoid corners with width scaling
        corners = []
        for i, angle in enumerate([yaw_rad - math.pi / 4, yaw_rad + math.pi / 4, yaw_rad + 3 * math.pi / 4, yaw_rad - 3 * math.pi / 4]):
            # Apply a width scaling factor to the outward-facing angles (for front-facing corners)
            if i < 2:  # Adjust front-facing corners
                lat_offset_scaled = lat_offset * width_factor
                lon_offset_scaled = lon_offset * width_factor
            else:  # Keep back-facing corners the same
                lat_offset_scaled = lat_offset
                lon_offset_scaled = lon_offset

            lat_change = math.sin(angle) * lat_offset_scaled
            lon_change = math.cos(angle) * lon_offset_scaled

            # Compute new corner position
            new_lat = gps_lat + lat_change
            new_lon = gps_lon + lon_change

            corners.append((new_lat, new_lon))

        # Print the XY corners of the trapezoid for debugging
        print(f"Filename: {filename}")
        print("Corners:")
        for i, corner in enumerate(corners):
            print(f"  Corner {i + 1}: Latitude: {corner[0]}, Longitude: {corner[1]}")

        # Store trapezoid data for this image
        trapezoid_data[filename] = corners

    return trapezoid_data