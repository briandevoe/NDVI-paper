import ee
import os
import time
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive

# ---------------------------------------------------------------------
# Initialize Earth Engine
# ---------------------------------------------------------------------
ee.Initialize(project="ee-testing-458522")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
START_YEAR = 2020
END_YEAR = 2023
DRIVE_FOLDER_NAME = "US_MODIS_NDVI_2025"  # Update automatically if needed
LOCAL_ROOT_DIR = r"E:\EE_modis_ndvi"
SCALE = 250
MAX_PIXELS = 1e13

# ---------------------------------------------------------------------
# Define US boundary
# ---------------------------------------------------------------------
us_geom = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
    .filter(ee.Filter.eq("country_na", "United States")) \
    .geometry()

# ---------------------------------------------------------------------
# Composite calculation for MODIS NDVI (scaled by 0.0001)
# ---------------------------------------------------------------------
def get_modis_ndvi(start_date, end_date):
    col = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start_date, end_date) \
        .filterBounds(us_geom) \
        .select("NDVI") \
        .map(lambda img: img.multiply(0.0001).copyProperties(img, img.propertyNames()))  # scale factor
    return col.mean().clip(us_geom)

# ---------------------------------------------------------------------
# Create and submit exports for each year
# ---------------------------------------------------------------------
export_tasks = []

for year in range(START_YEAR, END_YEAR + 1):
    # Annual NDVI
    annual = get_modis_ndvi(f"{year}-01-01", f"{year}-12-31")
    task_annual = ee.batch.Export.image.toDrive(
        image=annual,
        description=f"MODIS_NDVI_Annual_{year}",
        folder=DRIVE_FOLDER_NAME,
        fileNamePrefix=f"modis_ndvi_annual_{year}_us",
        region=us_geom,
        scale=SCALE,
        maxPixels=MAX_PIXELS
    )
    task_annual.start()
    export_tasks.append((task_annual, f"annual_{year}"))

    # JJA NDVI
    jja = get_modis_ndvi(f"{year}-06-01", f"{year}-08-31")
    task_jja = ee.batch.Export.image.toDrive(
        image=jja,
        description=f"MODIS_NDVI_JJA_{year}",
        folder=DRIVE_FOLDER_NAME,
        fileNamePrefix=f"modis_ndvi_jja_{year}_us",
        region=us_geom,
        scale=SCALE,
        maxPixels=MAX_PIXELS
    )
    task_jja.start()
    export_tasks.append((task_jja, f"jja_{year}"))

print("📤 Export tasks submitted. Waiting for them to complete...\n")

# ---------------------------------------------------------------------
# Wait for all tasks to complete
# ---------------------------------------------------------------------
while True:
    all_done = True
    for task, label in export_tasks:
        state = task.status()["state"]
        print(f"{label}: {state}")
        if state not in ['COMPLETED', 'FAILED', 'CANCELLED']:
            all_done = False
    if all_done:
        print("\n✅ All export tasks finished.")
        break
    print("⏳ Waiting 30 seconds...\n")
    time.sleep(30)

# ---------------------------------------------------------------------
# Google Drive Auth
# ---------------------------------------------------------------------
gauth = GoogleAuth()
gauth.LocalWebserverAuth()
drive = GoogleDrive(gauth)

# ---------------------------------------------------------------------
# Download and delete files
# ---------------------------------------------------------------------
folder_list = drive.ListFile({
    'q': f"title='{DRIVE_FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
}).GetList()
if not folder_list:
    raise Exception(f"Drive folder '{DRIVE_FOLDER_NAME}' not found.")
folder_id = folder_list[0]['id']

file_list = drive.ListFile({
    'q': f"'{folder_id}' in parents and trashed=false"
}).GetList()

for file in file_list:
    title = file['title']
    print(f"⬇️ Downloading: {title}")
    label = "unknown"
    if "jja" in title:
        label = f"JJA_{[s for s in title.split('_') if s.isdigit()][0]}"
    elif "annual" in title:
        label = f"Annual_{[s for s in title.split('_') if s.isdigit()][0]}"
    local_dir = os.path.join(LOCAL_ROOT_DIR, label)
    os.makedirs(local_dir, exist_ok=True)
    file_path = os.path.join(local_dir, title)
    file.GetContentFile(file_path)
    print(f"🗑️ Deleting from Drive: {title}")
    file.Delete()

print("🎉 All MODIS NDVI exports downloaded and Drive cleaned.")
