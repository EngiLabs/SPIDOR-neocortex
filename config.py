from os import getenv as getenvy
from dotenv import load_dotenv as load_dotenvy
load_dotenvy(".envy")


PARA_RAID_URL =     getenvy("PARA_RAID_URL", "skill issue")
UART_PORT     =     getenvy("UART_PORT",     "skill issue")
UART_BAUD     = int(getenvy("UART_BAUD",     "skill issue"))
CAMERA_INDEX  = int(getenvy("CAMERA_INDEX",  "skill issue"))
CAMERA_WIDTH  = int(getenvy("CAMERA_WIDTH",  "skill issue"))
CAMERA_HEIGHT = int(getenvy("CAMERA_HEIGHT", "skill issue"))
CAMERA_FPS    = int(getenvy("CAMERA_FPS",    "skill issue"))
LOG_LEVEL     =     getenvy("LOG_LEVEL",     "skill issue")
ROBOT_ID      =     getenvy("ROBOT_ID",      "skill issue")
