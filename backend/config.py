from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
MODELS_DIR = ROOT_DIR / "models"
FRONTEND_DIR = ROOT_DIR / "frontend"

DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

WILAYAH_CACHE_FILE = DATA_DIR / "wilayah_cache.csv"
WILAYAH_SOURCE_URL = (
    "https://raw.githubusercontent.com/kodewilayah/permendagri-72-2019/main/dist/base.csv"
)

BMKG_FORECAST_URL = "https://api.bmkg.go.id/publik/prakiraan-cuaca"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "pressure_msl",
    "cloud_cover",
    "wind_speed_10m",
]

# Model / training hyperparameters
SEQ_LEN = 72          # hours of history fed into the LSTM
HORIZON = 24           # hours forecast ahead
TARGET_COLS = ["temperature_2m", "precipitation"]
HISTORY_YEARS = 1.5    # how much historical data to train on
HIDDEN_SIZE = 64
NUM_LAYERS = 2
DROPOUT = 0.2
BATCH_SIZE = 128
EPOCHS = 10
LEARNING_RATE = 2e-3
VAL_FRACTION = 0.1
TRAIN_STRIDE = 6  # subsample windows every N hours to keep training fast
