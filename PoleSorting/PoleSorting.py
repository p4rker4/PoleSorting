from Functions import get_and_process_folder, export_to_csv, validate_manual_sort, display_validation_results, read_pole_data
from ImageFunctions import sort_into_folders, match_pole_to_trapezoid, extract_image_metadata, create_trapezoid
import geopandas as gpd
from shapely.geometry import Point, Polygon

def returntomenu():
    """Prompts the user to press Enter before returning to the menu."""
    input('\nPress Enter to return to the menu.')

class FolderAnalysis:

    def __init__(self):
        self.folder_matches = {}

    def menu(self):
        print("Folder Based Analysis")
        print("-" * 50)
        print("1. Process Pole Folders")
        print("2. View Results")
        print("3. Export Results to CSV")
        print("4. Validate Manual Sort")
        print("5. Return to Main Menu")
        print('-' * 50)

    def process_folders(self):
        print('\nBeginning Pole Folder Processing.')
        print('-' * 50)
        csv_file = "D:/BearValleyTesting/polelocations.csv"
        self.folder_matches = get_and_process_folder(csv_file)

    def view_results(self):
        if self.folder_matches:
            self.display_results()
        else:
            print("No results. Process pole folders first.")
        returntomenu()

    def export_results(self):
        if self.folder_matches:
            csv_output_file = input('Enter the path to the CSV you wish to write to: ')
            export_to_csv(self.folder_matches, csv_output_file)
        else:
            print("No results to export. Run option 1 first.")

    def validate_manual_sort(self):
        if self.folder_matches:
            correct_matches, incorrect_folders = validate_manual_sort(self.folder_matches)
            display_validation_results(correct_matches, incorrect_folders)
        else:
            print("Process pole folders first.")

    def display_results(self):
        matched, no_gps_or_no_image, over_10m = [], [], []

        for folder, data in self.folder_matches.items():
            if data['average_coordinates'] == (None, None):
                no_gps_or_no_image.append(folder)
            elif data['distance'] is not None and data['distance'] * 111000 > 10:
                over_10m.append(folder)
            else:
                matched.append(folder)

        print('\nFolders matched within 10 meters')
        print('-' * 50)
        for folder in matched:
            matched_pole = self.folder_matches[folder]['closest_pole']
            distance = self.folder_matches[folder]['distance'] * 111000
            print(f"{folder}: Matched to {matched_pole}, Distance = {distance:.2f} m")

        print("\nFolders matched outside of 10 meters")
        print('-' * 50)
        for folder in over_10m:
            matched_pole = self.folder_matches[folder]['closest_pole']
            avg_coords = self.folder_matches[folder]['average_coordinates']
            distance_in_meters = self.folder_matches[folder]['distance'] * 111000
            print(f"{folder}: Closest Pole: {matched_pole}, Distance = {distance_in_meters:.2f} meters, "
                  f"Lat = {avg_coords[0]:.6f}°, Lon = {avg_coords[1]:.6f}°")

        print("\nFolders with no GPS data or no images")
        print('-' * 50)
        for folder in no_gps_or_no_image:
            print(folder)

    def run(self):
        while True:
            self.menu()
            choice = input("Please select an option (1-5): ")

            if choice == '1':
                self.process_folders()
            elif choice == '2':
                self.view_results()
            elif choice == '3':
                self.export_results()
            elif choice == '4':
                self.validate_manual_sort()
            elif choice == '5':
                break
            else:
                print('Select a number from the list.')

class ImageAnalysis:

    def __init__(self):
        self.inside_poles = {}
        self.folder_path = None
        self.trapezoids = None
        self.pole_data = None
        self.image_metadata = None
        self.outside_poles = None

    def menu(self):
        print("Image Based Analysis")
        print("-" * 50)
        print("1. Process Images")
        print("2. View Results")
        print("3. Export Results to CSV")
        print("4. Export to Shapefile")
        print("5. Return to Main Menu")
        print('-' * 50)

    def process_images(self):
        self.folder_path = input('Input folder path: ')
        csv_file = input("Path to pole CSV file: ")
        self.destination_folder = 'Output/Sorted'

        self.image_metadata = extract_image_metadata(self.folder_path)
        self.trapezoids = create_trapezoid(self.image_metadata)
        self.pole_data = read_pole_data(csv_file)

        self.inside_poles, self.outside_poles = match_pole_to_trapezoid(self.trapezoids, self.pole_data)

        print("Outside Poles", self.outside_poles)
        print("Inside Poles", self.inside_poles)

        sort_into_folders(self.inside_poles, self.destination_folder, self.folder_path)

    def export_to_shapefile(self, image_metadata, trapezoids, pole_data):
        image_gdf = gpd.GeoDataFrame(columns=['image', 'geometry'], crs='EPSG:4326')
        trapezoid_gdf = gpd.GeoDataFrame(columns=gpd.GeoDataFrame(columns=['image', 'geometry'], crs='EPSG:4326'))
        pole_gdf = gpd.GeoDataFrame(columns=['pole', 'geometry'], crs='EPSG:4326')

        #image locations
        image_points = []
        image_names = []

        for filename, data in image_metadata.items():
            gps_lat = float(data['XMP:GPSLatitude'])
            gps_lon = float(data['XMP:GPSLongitude'])
            point = Point(gps_lon, gps_lat)
            image_points.append(point)
            image_names.append(filename)

        if image_points:
            image_gdf = gpd.GeoDataFrame({'image': image_names, 'geometry': image_points}, crs='EPSG:4326')

        #trapezoids
        trapezoid_polygons = []
        trapezoid_names = []

        for filename, corners in trapezoids.items():
            corrected_corners = [(lon, lat) for lat, lon in corners]
            polygon = Polygon(corrected_corners)
            trapezoid_polygons.append(polygon)
            trapezoid_names.append(filename)

        if trapezoid_polygons:
            trapezoid_gdf = gpd.GeoDataFrame({'image': trapezoid_names,'geometry': trapezoid_polygons}, crs='EPSG:4326')

        #poles
        pole_points = []
        pole_names = []

        for pole_id, (lat, lon) in pole_data.items():
            point = Point(lon, lat)
            pole_points.append(point)
            pole_names.append(pole_id)

        pole_gdf = gpd.GeoDataFrame({'pole': pole_names, 'geometry': pole_points}, crs='EPSG:4326')

        image_gdf.to_file("image_locations.shp")
        trapezoid_gdf.to_file("trapezoids.shp")
        pole_gdf.to_file("poles.shp")

        print("Shapefiles created successfully.")

    def run(self):
        while True:
            self.menu()
            choice = input("Please select an option (1-5): ")

            if choice == '1':
                self.process_images()
            elif choice == '2':
                print('TBD')
            elif choice == '3':
                print('TBD')
            elif choice == '4':
                self.export_to_shapefile(self.image_metadata, self.trapezoids, self.pole_data)
            elif choice == '5':
                break
            else:
                print('Select a number from the list.')

class MainProgram:

    def __init__(self):
        self.folder_analysis = FolderAnalysis()
        self.image_analysis = ImageAnalysis()

    def menu(self):
        print("Pole Sorting")
        print("-" * 50)
        print("1. Folder Based Analysis")
        print("2. Image Based Analysis")
        print("3. Exit Program")
        print('-' * 50)

    def run(self):
        while True:
            self.menu()
            choice = input("Please select an option (1-3): ")

            if choice == '1':
                self.folder_analysis.run()
            elif choice == '2':
                self.image_analysis.run()
            elif choice == '3':
                break
            else:
                print('Select a number from the list.')

if __name__ == "__main__":
    MainProgram().run()