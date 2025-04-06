import geopandas as gpd
import simplekml
import zipfile
import os
from shapely.geometry import Point, Polygon
from ImageFunctions import (sort_into_folders, match_pole_to_trapezoid,
                            extract_image_metadata, create_trapezoid, create_square, read_pole_data)

def returntomenu():
    input('\nPress Enter to return to the menu.')

def merge_shapes(square_data, trapezoid_data):
    return {**square_data, **trapezoid_data}

class ImageAnalysis:

    def __init__(self):
        self.inside_poles = None
        self.folder_path = None
        self.trapezoids = None
        self.pole_data = None
        self.image_metadata = None
        self.no_poles = None

    def menu(self):
        print("\nImage Based Analysis")
        print("-" * 50)
        print("1. Process Images")
        print("2. Export to Shapefile")
        print("3. Exit")
        print('-' * 50)

    def process_images(self):
        self.folder_path = input('Input folder path: ')
        csv_file = input("Path to pole CSV file: ")
        self.sorted_destination_folder = 'Output/Sorted'
        self.destination_folder = 'Output'
        self.image_metadata = extract_image_metadata(self.folder_path)
        self.trapezoids = create_trapezoid(self.image_metadata)
        self.squares = create_square(self.image_metadata)
        self.polygons = merge_shapes(self.trapezoids, self.squares)
        self.pole_data = read_pole_data(csv_file)

        self.inside_poles, self.no_poles, self.multiple_poles = (match_pole_to_trapezoid(self.polygons,self.pole_data))

        print(f'{len(self.inside_poles)} matched images.')
        print(f'{len(self.no_poles)} unmatched images.')
        print(f'{len(self.multiple_poles)} pictures with multiple poles.')

        sort_into_folders(self.inside_poles, self.no_poles, self.multiple_poles,
                          self.sorted_destination_folder, self.destination_folder, self.folder_path)

    def export_to_shapefile(self, image_metadata, trapezoids, pole_data, inside_poles, no_poles, multiple_poles):
        image_gdf = gpd.GeoDataFrame(columns=['image', 'geometry'], crs='EPSG:4326')
        trapezoid_gdf = gpd.GeoDataFrame(columns=gpd.GeoDataFrame(columns=['image', 'geometry', 'pole'], crs='EPSG:4326'))
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

        #TRAPEZOIDS
        trapezoid_polygons = []
        trapezoid_names = []
        trapezoid_poles = []

        for filename, corners in trapezoids.items():
            corrected_corners = [(lon, lat) for lat, lon in corners]
            polygon = Polygon(corrected_corners)
            trapezoid_polygons.append(polygon)
            trapezoid_names.append(filename)

            #pole field population
            if filename in inside_poles:
                trapezoid_poles.append(inside_poles[filename])
            elif filename in no_poles:
                trapezoid_poles.append('No Match')
            elif filename in multiple_poles:
                trapezoid_poles.append('Multiple Poles')
            else:
                trapezoid_poles.append('Processing Error')

        if trapezoid_polygons:
            trapezoid_gdf = gpd.GeoDataFrame({'image': trapezoid_names,'geometry': trapezoid_polygons, 'pole': trapezoid_poles}, crs='EPSG:4326')

        #poles
        pole_points = []
        pole_names = []

        for pole_id, (lat, lon) in pole_data.items():
            point = Point(lon, lat)
            pole_points.append(point)
            pole_names.append(pole_id)

        pole_gdf = gpd.GeoDataFrame({'pole': pole_names, 'geometry': pole_points}, crs='EPSG:4326')

        image_gdf.to_file("output/shapefiles/image_locations.shp")
        trapezoid_gdf.to_file("output/shapefiles/trapezoids.shp")
        pole_gdf.to_file("output/shapefiles/poles.shp")

        print("Shapefiles created successfully.")

    def export_to_kml(self, image_metadata, trapezoids, pole_data, inside_poles, no_poles, multiple_poles,
                      output_filename="output.kmz"):
        kml = simplekml.Kml()

        #separate folders for each thing
        poles_folder = kml.newfolder(name="Pole Locations")
        images_folder = kml.newfolder(name="Image Locations")
        trapezoids_folder = kml.newfolder(name="Trapezoids")

        #images
        for filename, data in image_metadata.items():
            gps_lat = float(data['XMP:GPSLatitude'])
            gps_lon = float(data['XMP:GPSLongitude'])
            images_folder.newpoint(name=filename, coords=[(gps_lon, gps_lat)])

        #polygons
        for filename, corners in trapezoids.items():
            corrected_corners = [(lon, lat) for lat, lon in corners]
            corrected_corners.append(corrected_corners[0])  # Close the polygon
            polygon = trapezoids_folder.newpolygon(name=filename, outerboundaryis=corrected_corners)

            #populate pole data field as description
            if filename in inside_poles:
                polygon.description = f"Pole: {inside_poles[filename]}"
            elif filename in no_poles:
                polygon.description = "Pole: No Match"
            elif filename in multiple_poles:
                polygon.description = "Pole: Multiple Poles"
            else:
                polygon.description = "Pole: Processing Error"

        #polelocations
        for pole_id, (lat, lon) in pole_data.items():
            poles_folder.newpoint(name=pole_id, coords=[(lon, lat)])

        #save as kmz
        kml_filename = output_filename.replace(".kmz", ".kml")
        kml.save(kml_filename)
        with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as kmz:
            kmz.write(kml_filename, os.path.basename(kml_filename))
        os.remove(kml_filename)

        print(f"KMZ file created successfully: {output_filename}")

    def run(self):
        while True:
            self.menu()
            choice = input("\nPlease select an option (1-3): ")

            if choice == '1':
                self.process_images()
            elif choice == '2':
                self.export_to_shapefile(self.image_metadata, self.polygons, self.pole_data, self.inside_poles,
                                         self.no_poles, self.multiple_poles)
                self.export_to_kml(self.image_metadata, self.polygons, self.pole_data, self.inside_poles,
                                   self.no_poles, self.multiple_poles)
            elif choice == '3':
                break
            else:
                print('Select a number from the list.')

if __name__ == "__main__":
    ImageAnalysis().run()

