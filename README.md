# PoleSorting
By hand, sort pole images into distinct folders separated by pole, but named indistinctly
Insert the folder of folders and the CSV of pole locations into this script

It will, for each pole folder:
- Extract the GPS metadata from each image, and average their locations together
- Find the closest pole to that location
- Rename the folder to that pole's number
