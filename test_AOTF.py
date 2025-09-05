import time
import numpy as np
from utils.laser_utils import init_AOTF, get_coord, change_power_function, move_and_click
from utils.socket_utils import send_cmd, receive_msg, create_server, accept_client


grid = init_AOTF()