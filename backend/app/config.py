from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    PROJECT_NAME: str = "InfinityCore Quantum Traffic Optimizer"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"
    DEBUG: bool = True
    
    # City configuration
    DEFAULT_CITY: str = "New Delhi (Connaught Place & Central Hub)"
    DEFAULT_LAT: float = 28.6315
    DEFAULT_LON: float = 77.2167
    GRAPH_RADIUS_METERS: int = 4000
    
    # QPSO Hyperparameters
    QPSO_DEFAULT_PARTICLES: int = 35
    QPSO_DEFAULT_MAX_ITER: int = 50
    QPSO_BETA_INITIAL: float = 1.0
    QPSO_BETA_FINAL: float = 0.4
    
    # Objective weights defaults
    DEFAULT_W_TIME: float = 0.40
    DEFAULT_W_DISTANCE: float = 0.20
    DEFAULT_W_CONGESTION: float = 0.25
    DEFAULT_W_ROAD_CONDITION: float = 0.15
    
    # Simulator parameters
    SIMULATOR_UPDATE_INTERVAL_SEC: float = 3.0

settings = Settings()
