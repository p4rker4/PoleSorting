from Functions import get_and_process_folder

def menu():
    print("Menu")
    print("-" * 50)
    print("1. Process Pole Folders")
    print("2. View Results")
    print("3. Export Results to CSV")
    print("4. Validate Manual Sort")
    print("5. Exit Program")
    print('-' * 50)

def main():
    folder_matches = {}
    while True:
        menu()
        choice = input("Please select an option (1-5): ")

        if choice == '1':
            print('\nBeginning Pole Folder Processing.')
            print('-' * 50)
            csv_file = input('Enter the path to the CSV file containing pole data: ')
            folder_matches = get_and_process_folder(csv_file)
        elif choice == '2':
            if folder_matches:
                display_results(folder_matches)
            else:
                print("No results. Process pole folders first.")
            returntomenu()
        elif choice == '3':
            print('in progress')
        elif choice == '4':
            print('in progress')
        elif choice == '5':
            break
        else:
            print('Select a number from the list.')

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

if __name__ == "__main__":
    main()