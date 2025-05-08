import time
import random
import os

class SimulatedVisaCon:
    def __init__(self, addr="GPIB0::17::INSTR", timeout=10000):
        self.addr = addr
        self.timeout = timeout
        self.connected = False  # Simulated connection state
        self.inst = self  # Simulated `inst` attribute
        self.query_delay = 0.1  # Simulated query delay

    # Simulates connecting to the instrument
    def connect(self):
        print(f"Simulating connection to {self.addr}...")
        self.connected = True  # Simulate successful connection
        print(f"Simulated connection successful to {self.addr}")

    # Simulates disconnecting from the instrument
    def disconnect(self):
        if self.connected:
            print(f"Simulating disconnection from {self.addr}...")
            self.connected = False
            print(f"Simulated disconnection successful from {self.addr}")
        else:
            print("Simulated device is already disconnected.")

    # Simulates checking the connection
    def check_connection(self, force_check=False):
        if force_check:
            print("Simulating forced connection check...")
        return self.connected  # Return the simulated connection state

    # Simulates writing a command to the instrument
    def write(self, command):
        print(f"Simulated write: {command}")

    # Simulates querying the instrument
    def query(self, command):
        print(f"Simulated query: {command}")
        # Return simulated responses for specific queries
        simulated_responses = {
            "ID?": "Simulated HP4280A Device",
            "*IDN?": "Simulated HP4280A,12345,1.0",
            "PV?": "5.0",
            "PS?": "0.0",
            "PP?": "5.0",
            "PE?": "0.1",
            "PL?": "0.01",
            "PD?": "0.03",
        }
        return simulated_responses.get(command, "Simulated Response")

    # Simulates reading data from the instrument
    def read(self):
        print("Simulated read: Returning default data.")
        return "Simulated,Data,1.0,2.0,3.0"

    # Simulates reading raw data from the instrument
    def read_raw(self):
        print("Simulated read_raw: Returning dummy binary data.")
        return b"Simulated,Data,1.0,2.0,3.0"

    # Simulates clearing the instrument's state
    def clear(self):
        if self.connected:
            print("Simulated: Instrument cleared successfully.")
        else:
            print("Simulated: No instrument connected to clear.")

    # Simulates getting the MAC address
    def get_MAC(self):
        return self.addr

    # Simulates setting the MAC address
    def set_MAC(self, addr):
        self.addr = addr

    # Simulates getting the timeout value
    def get_timeout(self):
        return self.timeout

    # Simulates setting the timeout value
    def set_timeout(self, timeout):
        self.timeout = timeout

    # Simulates querying the device ID
    def get_device_id(self):
        if self.connected:
            return "Simulated HP4280A Device"
        else:
            return "No device connected"

    # Simulates querying measurement
    def query_measurement(self, value):
        c = random.uniform(1.0, 10.0)  # Simulated capacitance
        g = random.uniform(0.1, 1.0)   # Simulated conductivity
        return c, g

    # Simulates a default sweep using a CSV file
    def simulate_default_sweep(self):
        csv_path = os.path.join(os.path.dirname(__file__), "uploads", "datasweep0313.csv")
        try:
            with open(csv_path, "r") as file:
                data = file.read()
            print("Simulated sweep data loaded successfully.")
            return data
        except FileNotFoundError:
            print("Simulated sweep data file not found.")
            return "Error: Simulated data file not found."