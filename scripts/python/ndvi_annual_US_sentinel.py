import ee
import time

# ---------------------------------------------------------------------
# Initialize Earth Engine
# ---------------------------------------------------------------------
ee.Initialize(project="ee-testing-458522")

# ---------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------
YEAR = 2020
STATE_NAME = "Massachusetts"
DRIVE_FOLDER_NAME = "NDVI_S2_MA_2020"
SCALE = 10  # Sentinel-2 resolution
MAX_PIXELS = 1e13

# ---------------------------------------------------------------------
# Define Massachusetts geometry
# ---------------------------------------------------------------------
states_fc = ee.FeatureCollection("TIGER/2018/States")
ma_feature = states_fc.filter(ee.Filter.eq('NAME', STATE_NAME)).first()
ma_geom = ma_feature.geometry()

# ---------------------------------------------------------------------
# Function to calculate NDVI
# ---------------------------------------------------------------------
def add_ndvi(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    return image.addBands(ndvi)

# ---------------------------------------------------------------------
# Load Sentinel-2 data and compute NDVI composite
# ---------------------------------------------------------------------
s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
    .filterDate(f"{YEAR}-01-01", f"{YEAR}-12-31") \
    .filterBounds(ma_geom) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .map(add_ndvi)

composite = s2.select("NDVI").median().clip(ma_geom)

# ---------------------------------------------------------------------
# Export to Google Drive
# ---------------------------------------------------------------------
task = ee.batch.Export.image.toDrive(
    image=composite,
    description=f"NDVI_{STATE_NAME}_{YEAR}",
    folder=DRIVE_FOLDER_NAME,
    fileNamePrefix=f"ndvi_s2_{STATE_NAME.lower().replace(' ', '_')}_{YEAR}",
    region=ma_geom.bounds().getInfo()['coordinates'],
    scale=SCALE,
    maxPixels=MAX_PIXELS
)

print(f"🌱 Submitting export task for {STATE_NAME} ({YEAR})...")
task.start()

# ---------------------------------------------------------------------
# Monitor progress
# ---------------------------------------------------------------------
while True:
    status = task.status()['state']
    print(f"{STATE_NAME}: {status}")
    if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
        break
    time.sleep(30)

print(f"✅ Export task for {STATE_NAME} is {status}.")

