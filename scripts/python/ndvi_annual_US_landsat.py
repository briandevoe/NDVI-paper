import ee
import os
import time
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ---------------------------------------------------------------------
# Step 1: Initialize Earth Engine
# ---------------------------------------------------------------------
ee.Initialize(project="ee-testing-458522")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
START_YEAR = 2020
END_YEAR = 2023
DRIVE_FOLDER_NAME = "US_NDVI_NDBI_Annual"
LOCAL_ROOT_DIR = r"E:\EE_ndvi_ndbi"
SCALE = 30
MAX_PIXELS = 1e13

# ---------------------------------------------------------------------
# Define US Geometry
# ---------------------------------------------------------------------
us_geom = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
    .filter(ee.Filter.eq("country_na", "United States")) \
    .geometry()

# ---------------------------------------------------------------------
# NDVI and NDBI Calculation
# ---------------------------------------------------------------------
def add_indices(image):
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')  # NIR, Red
    ndbi = image.normalizedDifference(['SR_B6', 'SR_B5']).rename('NDBI')  # SWIR, NIR
    return image.addBands([ndvi, ndbi])

# ---------------------------------------------------------------------
# Step 2: Export Earth Engine Data
# ---------------------------------------------------------------------
export_tasks = []

for year in range(START_YEAR, END_YEAR + 1):
    print(f"🌎 Starting processing for {year}...")

    collection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
        .filterDate(f"{year}-01-01", f"{year}-12-31") \
        .filterBounds(us_geom) \
        .map(lambda img: img.updateMask(img.select("QA_PIXEL").bitwiseAnd(1 << 3).eq(0))) \
        .map(add_indices)

    composite = collection.select(['NDVI', 'NDBI']).mean().clip(us_geom)

    for metric in ['NDVI', 'NDBI']:
        task = ee.batch.Export.image.toDrive(
            image=composite.select(metric),
            description=f"{metric}_{year}_US",
            folder=DRIVE_FOLDER_NAME,
            fileNamePrefix=f"{metric.lower()}_{year}_us",
            region=us_geom,
            scale=SCALE,
            maxPixels=MAX_PIXELS
        )
        task.start()
        export_tasks.append((task, metric, year))

print("📤 Export tasks submitted. Waiting for them to complete...")

# ---------------------------------------------------------------------
# Step 3: Wait for All Exports to Finish
# ---------------------------------------------------------------------
all_done = False
while not all_done:
    all_done = True
    for task, metric, year in export_tasks:
        status = task.status()['state']
        print(f"{metric}_{year}: {status}")
        if status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
            all_done = False
    if not all_done:
        print("⏳ Waiting 30 seconds before next check...\n")
        time.sleep(30)

print("✅ All Earth Engine exports are done. Beginning download...")

# ---------------------------------------------------------------------
# Step 4: Authenticate Google Drive
# ---------------------------------------------------------------------
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# ---------------------------------------------------------------------
# Step 5: Download and Delete Files
# ---------------------------------------------------------------------
# Find export folder
folder_list = drive.ListFile({
    'q': f"title='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
}).GetList()
if not folder_list:
    raise Exception(f"Folder '{DRIVE_FOLDER_NAME}' not found in Google Drive.")
folder_id = folder_list[0]['id']

# Download each .tif and delete
file_list = drive.ListFile({
    'q': f"'{folder_id}' in parents and trashed=false"
}).GetList()

for file in file_list:
    title = file['title']
    if title.endswith('.tif'):
        print(f"⬇️ Downloading: {title}")
        # Extract year from filename
        year_part = [s for s in title.split('_') if s.isdigit()]
        year = year_part[0] if year_part else 'unknown'
        local_dir = os.path.join(LOCAL_ROOT_DIR, year)
        os.makedirs(local_dir, exist_ok=True)
        file_path = os.path.join(local_dir, title)
        file.GetContentFile(file_path)
        print(f"🗑️ Deleting from Drive: {title}")
        file.Delete()

print("🎉 All files downloaded and cleaned up.")
