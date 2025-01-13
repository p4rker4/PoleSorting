from Functions import get_and_process_folder, export_to_csv, validate_manual_sort, display_validation_results, read_pole_data
from ImageFunctions import sort_into_folders, match_pole_to_trapezoid, extract_image_metadata, create_trapezoid


def foldermenu():
    print("Folder Based Analysis")
    print("-" * 50)
    print("1. Process Pole Folders")
    print("2. View Results")
    print("3. Export Results to CSV")
    print("4. Validate Manual Sort")
    print("5. Return to Main Menu")
    print('-' * 50)

def foldermain():
    folder_matches = {}
    while True:
        foldermenu()
        choice = input("Please select an option (1-5): ")

        if choice == '1':
            print('\nBeginning Pole Folder Processing.')
            print('-' * 50)
            #csv_file = input('Enter the path to the CSV file containing pole data: ')
            csv_file = "D:/BearValleyTesting/polelocations.csv"
            folder_matches = get_and_process_folder(csv_file)
        elif choice == '2':
            if folder_matches:
                display_results(folder_matches)
            else:
                print("No results. Process pole folders first.")
            returntomenu()
        elif choice == '3':
            if folder_matches:
                csv_output_file = input('Enter the path to the CSV you wish to write to: ')
                export_to_csv(folder_matches, csv_output_file)
            else:
                print("No results to export. Run option 1 first.")
        elif choice == '4':
            if folder_matches:
                correct_matches, incorrect_folders = validate_manual_sort(folder_matches)
                display_validation_results(correct_matches, incorrect_folders)
            else:
                print("Process pole folders first.")
        elif choice == '5':
            break
        else:
            print('Select a number from the list.')

def imagemain():
    while True:
        imagemenu()
        choice = input("Please select an option (1-4): ")

        if choice == '1':
            folder_path = input('Input folder path: ')
            csv_file = input("Path to pole CSV file:")
            #extract metadata
            image_metadata = extract_image_metadata(folder_path)
            #create approx viewshed trapezoids
            trapezoids = create_trapezoid(image_metadata)
            #get the pole locations
            pole_data = read_pole_data(csv_file)
            #see if any poles are in each viewshed
            inside_poles = match_pole_to_trapezoid(trapezoids, pole_data)

        elif choice == '2':
            print('tbd')
        elif choice == '3':
            print('tbd')
        elif choice == '4':
            destination_folder = input('Input path where you want poles to be exported: ')
            #if a picture has a matching pole, put it in the folder
            sort_into_folders(inside_poles, destination_folder, folder_path)
        elif choice == '5':
            break
        else:
            print('Select a number from the list.')

def imagemenu():
    print("Image Based Analysis")
    print("-" * 50)
    print("1. Process Images")
    print("2. View Results")
    print("3. Export Results to CSV")
    print("4. Export Matches to Pole Folders")
    print("5. Return to Main Menu")
    print('-' * 50)

def returntomenu():
    input('\nPress Enter to return to the menu.')

def display_results(folder_matches):
    matched = []
    no_gps_or_no_image = []
    over_10m = []

    #separate results into matches, no data, or bad matches
    for folder, data in folder_matches.items():
        if data['average_coordinates'] == (None, None):
            no_gps_or_no_image.append(folder)
        elif data['distance'] is not None and data ['distance'] * 111000 > 10:
            over_10m.append(folder)
        else:
            matched.append(folder)

    print('\nFolders matched within 10 meters')
    print('-' * 50)
    for folder in matched:
        matched_pole = folder_matches[folder]['closest_pole']
        distance = folder_matches[folder]['distance'] * 111000
        print(f"{folder}: Matched to {matched_pole}, Distance = {distance:.2f} m")

    print("\nFolders matched outside of 10 meters")
    print('-' * 50)
    for folder in over_10m:
        matched_pole = folder_matches[folder]['closest_pole']
        avg_coords = folder_matches[folder]['average_coordinates']
        dmsdistance = folder_matches[folder]['distance']
        distance_in_meters = dmsdistance * 111000
        print(f"{folder}: Closest Pole: {matched_pole} at a distance of {distance_in_meters:.2f} meters, Lat = {avg_coords[0]:.6f}°, Lon = {avg_coords[1]:.6f}°")

    print("\nFolders with no GPS data or no images")
    print('-' * 50)
    for folder in no_gps_or_no_image:
            print(folder)

def mainmenu():
    print("Pole Sorting")
    print("-" * 50)
    print("1. Folder Based Analysis")
    print("2. Image Based Analysis")
    print("3. Exit Program")
    print('-' * 50)

def main():
    while True:
        mainmenu()
        choice = input("Please select an option (1-3): ")

        if choice == '1':
            foldermain()
        elif choice == '2':
            imagemain()
        elif choice == '3':
            break
        else:
            print('Select a number from the list.')

if __name__ == "__main__":
    main()