import ee

# -----------------------------------------------
# Initialize Earth Engine
# -----------------------------------------------
ee.Initialize()

# -----------------------------------------------
# Parameters
# -----------------------------------------------
YEAR = 2021   # Change this for other years

DRIVE_FOLDER = "SENTINEL_NDVI"
SCALE = 100  # Export resolution in meters
MAX_PIXELS = 1e13

# -----------------------------------------------
# Define US boundary
# (here entire US; adjust to lower 48 if desired)
# -----------------------------------------------
us_geom = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017") \
    .filter(ee.Filter.eq("country_na", "United States")) \
    .geometry()

# -----------------------------------------------
# Function to compute Sentinel NDVI
# -----------------------------------------------
def get_sentinel_ndvi(start_date, end_date):
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterDate(start_date, end_date)
        .filterBounds(us_geom)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
        .map(
            lambda img: img
            .normalizedDifference(["B8", "B4"])
            .rename("NDVI")
            .copyProperties(img, img.propertyNames())
        )
    )
    return collection.mean().clip(us_geom)

# -----------------------------------------------
# Export annual NDVI
# -----------------------------------------------
annual_img = get_sentinel_ndvi(
    f"{YEAR}-01-01",
    f"{YEAR}-12-31"
)

annual_task = ee.batch.Export.image.toDrive(
    image=annual_img,
    description=f"Sentinel_NDVI_Annual_{YEAR}",
    folder=DRIVE_FOLDER,
    fileNamePrefix=f"{YEAR}_annual",
    region=us_geom,
    scale=SCALE,
    maxPixels=MAX_PIXELS
)

annual_task.start()

# -----------------------------------------------
# Export summer NDVI
# -----------------------------------------------
summer_img = get_sentinel_ndvi(
    f"{YEAR}-06-01",
    f"{YEAR}-08-31"
)

summer_task = ee.batch.Export.image.toDrive(
    image=summer_img,
    description=f"Sentinel_NDVI_Summer_{YEAR}",
    folder=DRIVE_FOLDER,
    fileNamePrefix=f"{YEAR}_summer",
    region=us_geom,
    scale=SCALE,
    maxPixels=MAX_PIXELS
)

summer_task.start()

print("running")


