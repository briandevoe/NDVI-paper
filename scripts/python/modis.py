import ee

# -----------------------------------------------
# Initialize Earth Engine
# -----------------------------------------------
ee.Initialize(project="ee-testing-458522")

# -----------------------------------------------
# Parameters
# -----------------------------------------------
YEAR = 2021   # Change this to any year you want

# Google Drive folder (under your drive root)
DRIVE_FOLDER = "MODIS/NDVI"

# Image export scale (meters)
SCALE = 250

# Max pixels for export
MAX_PIXELS = 1e13

# -----------------------------------------------
# Define US boundary (CONUS only)
# (Here we keep entire US for simplicity)
# -----------------------------------------------
us_geom = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
    .filter(ee.Filter.eq("country_na", "United States")) \
    .geometry()

# -----------------------------------------------
# Function to get MODIS NDVI mean image
# -----------------------------------------------
def get_modis_ndvi(start_date, end_date):
    collection = ee.ImageCollection("MODIS/061/MOD13Q1") \
        .filterDate(start_date, end_date) \
        .filterBounds(us_geom) \
        .select("NDVI") \
        .map(lambda img: img.multiply(0.0001).copyProperties(img, img.propertyNames()))
    return collection.mean().clip(us_geom)

# -----------------------------------------------
# Export annual average NDVI
# -----------------------------------------------
annual_image = get_modis_ndvi(
    f"{YEAR}-01-01",
    f"{YEAR}-12-31"
)

annual_task = ee.batch.Export.image.toDrive(
    image=annual_image,
    description=f"MODIS_NDVI_Annual_{YEAR}",
    folder=DRIVE_FOLDER,
    fileNamePrefix=f"{YEAR}_annual",
    region=us_geom,
    scale=SCALE,
    maxPixels=MAX_PIXELS
)

annual_task.start()

# -----------------------------------------------
# Export summer (June-July-August) average NDVI
# -----------------------------------------------
summer_image = get_modis_ndvi(
    f"{YEAR}-06-01",
    f"{YEAR}-08-31"
)

summer_task = ee.batch.Export.image.toDrive(
    image=summer_image,
    description=f"MODIS_NDVI_Summer_{YEAR}",
    folder=DRIVE_FOLDER,
    fileNamePrefix=f"{YEAR}_summer",
    region=us_geom,
    scale=SCALE,
    maxPixels=MAX_PIXELS
)

summer_task.start()

print("running")


