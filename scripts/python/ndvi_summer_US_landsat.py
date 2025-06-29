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
DRIVE_FOLDER_NAME = "US_NDVI_JJA"
LOCAL_ROOT_DIR = r"E:\EE_ndvi_ndbi"
SCALE = 30
MAX_PIXELS = 1e13

# ---------------------------------------------------------------------
# Define U.S. boundary
# ---------------------------------------------------------------------
us_geom = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
    .filter(ee.Filter.eq("country_na", "United States")) \
    .geometry()

# ---------------------------------------------------------------------
# NDVI calculation
# ---------------------------------------------------------------------
def add_ndvi(image):
    ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')  # NIR, Red
    return image.addBands(ndvi)

# ---------------------------------------------------------------------
# Step 2: Submit NDVI export tasks (June–August)
# ---------------------------------------------------------------------
export_tasks = []

for year in range(START_YEAR, END_YEAR + 1):
    print(f"🌱 Submitting NDVI export for peak season (JJA) {year}...")

    collection = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2") \
        .filterDate(f"{year}-06-01", f"{year}-08-31") \
        .filterBounds(us_geom) \
        .map(lambda img: img.updateMask(img.select("QA_PIXEL").bitwiseAnd(1 << 3).eq(0))) \
        .map(add_ndvi)

    ndvi_composite = collection.select('NDVI').mean().clip(us_geom)

    task = ee.batch.Export.image.toDrive(
        image=ndvi_composite,
        description=f"NDVI_JJA_{year}_US",
        folder=DRIVE_FOLDER_NAME,
        fileNamePrefix=f"ndvi_jja_{year}_us",
        region=us_geom,
        scale=SCALE,
        maxPixels=MAX_PIXELS
    )
    task.start()
    export_tasks.append((task, year))

# ---------------------------------------------------------------------
# Step 3: Monitor export progress
# ---------------------------------------------------------------------
print("\n⏳ Waiting for Earth Engine exports to complete...\n")
while True:
    all_done = True
    for task, year in export_tasks:
        status = task.status()['state']
        print(f"NDVI_JJA_{year}: {status}")
        if status not in ['COMPLETED', 'FAILED', 'CANCELLED']:
            all_done = False
    if all_done:
        print("\n✅ All Earth Engine export tasks finished.")
        break
    time.sleep(30)

# ---------------------------------------------------------------------
# Step 4: Authenticate Google Drive
# ---------------------------------------------------------------------
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# ---------------------------------------------------------------------
# Step 5: Download and delete exported files
# ---------------------------------------------------------------------
folder_list = drive.ListFile({
    'q': f"title='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
}).GetList()

if not folder_list:
    raise Exception(f"Folder '{DRIVE_FOLDER_NAME}' not found in Google Drive.")
folder_id = folder_list[0]['id']

file_list = drive.ListFile({
    'q': f"'{folder_id}' in parents and trashed=false"
}).GetList()

for file in file_list:
    title = file['title']
    if title.endswith('.tif'):
        print(f"⬇️ Downloading: {title}")
        # Extract year
        year_part = [s for s in title.split('_') if s.isdigit()]
        year = year_part[0] if year_part else 'unknown'
        local_dir = os.path.join(LOCAL_ROOT_DIR, f"NDVI_JJA_{year}")
        os.makedirs(local_dir, exist_ok=True)
        file_path = os.path.join(local_dir, title)
        file.GetContentFile(file_path)
        print(f"🗑️ Deleting from Drive: {title}")
        file.Delete()

print("🎉 All NDVI JJA data downloaded and cleaned up from Drive.")
