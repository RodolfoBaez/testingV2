import pyvisa
import sys

# VisaCon class to connect and disconnect from GPIB instruments
class VisaCon:
    def __init__(self, addr="GPIB1::17::INSTR", timeout=10000):
        self.addr = addr
        self.timeout = timeout
        self.inst = None
        self.connected = False  # NEW: Track connection status explicitly
        self.connect()

    # Connects to the instrument
    def connect(self):
        try:
            self.rm = pyvisa.ResourceManager()
            self.inst = self.rm.open_resource(self.addr)
            if self.inst is not None:
                self.inst.timeout = self.timeout
                self.inst.query_delay = 0.1
                idn = self.inst.query('ID?')
                print(f"Connected to {self.addr}")
                print(f"Instrument ID: {idn}")
                self.connected = True  # NEW: Mark as connected on success
        except pyvisa.errors.VisaIOError as e:
            error_code = e.error_code
            if error_code == pyvisa.constants.StatusCode.error_resource_not_found:
                print(f"Error: GPIB device not found at {self.addr}. Please check the connection and address.")
            else:
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
            self.inst = None
            self.connected = False  # NEW: Mark as not connected on error
        except Exception as e:
            print(f"Unexpected Error: {e}")
            self.inst = None
            self.connected = False  # NEW: Also mark not connected on unexpected error

    # Disconnects from the instrument
    def disconnect(self):
        try:
            if self.inst is not None:
                self.inst.close()
                print("Disconnected from", self.addr)
                self.connected = False  # NEW: Ensure connected status is updated
        except pyvisa.errors.VisaIOError as e:
            error_code = e.error_code
            print(f"GPIB Communication Error [{error_code}]: {e.description}")

    # Utility get/set methods
    def set_MAC(self, addr):
        self.addr = addr

    def get_MAC(self):
        return self.addr

    def set_timeout(self, timeout):
        self.timeout = timeout

    def get_timeout(self):
        return self.timeout

    def get_device_id(self):
        if self.inst is not None:
            return self.inst.query('ID?')
        return None

    def check_connection(self, force_check=False):
        if force_check:
            try:
                if self.inst is not None:  # NEW: Was 'self.resource', should be 'self.inst'
                    _ = self.inst.query("*IDN?")
                    self.connected = True  # NEW: Update status if query works
                    return True
                else:
                    self.connected = False
                    return False
            except Exception:
                self.connected = False  # NEW: Safely catch any issue and update status
                return False
        return self.connected  # NEW: This now safely returns the explicitly managed attribute
