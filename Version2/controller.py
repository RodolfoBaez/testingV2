from visacon import VisaCon
import pyvisa
import csv
import time
import os
import datetime

class controller:
    DC_V = 0.0
    Start_V = 0.0
    Stop_V = 0.0
    Step_V = 0.0
    Hold_T = 0.0
    Step_T = 0.0

    def __init__(self, conn, DC_V, Start_V, Stop_V, Step_V, Hold_T, Step_T):
        self.DC_V = DC_V
        self.Start_V = Start_V
        self.Stop_V = Stop_V
        self.Step_V = Step_V
        self.Hold_T = Hold_T
        self.Step_T = Step_T
        
        self.conn = conn

    # Ensure the connection object has an 'inst' attribute
        if hasattr(self.conn, 'inst'):
            self.inst = self.conn.inst
        else:
            raise AttributeError("The connection object does not have an 'inst' attribute.")
        
    # initialize the instrument measurement

    def measure_start(self):
        cmd = "INIT"
        self.command(cmd)

    """
    Numerical Settings
    """
    # Functions to set the values of the instrument
    def set_DCV(self, DC_V):
        if self.conn.inst is not None:
            self.DC_V = DC_V
            command = "PV " + str(self.DC_V)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_StartV(self, Start_V):
        if self.conn.inst is not None:
            self.Start_V = Start_V
            command = "PS " + str(self.Start_V)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_StopV(self, Stop_V):
        if self.conn.inst is not None:
            self.Stop_V = Stop_V
            command = "PP " + str(self.Stop_V)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_StepV(self, Step_V):
        if self.conn.inst is not None:
            self.Step_V = Step_V
            command = "PE " + str(self.Step_V)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_Hold_Time(self, Hold_T):
        if self.conn.inst is not None:
            self.Hold_T = Hold_T
            command = "PL " + str(self.Hold_T)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_StepT(self, Step_T):
        if self.conn.inst is not None:
            self.Step_T = Step_T
            command = "PD " + str(self.Step_T)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    #number of step readings
    def set_NOFREAD(self, v):
        if self.conn.inst is not None:
            command = "PN " + str(v)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    """
    Setup CT Function
    Functions to set the values of the clock from start time to end time:

    PU is the Pulse voltage

    PH (th) is the hold time (default 10ms)

    PT is the measurement interval
    """
    def set_Measure_pulse(self, m_v):
        if self.conn.inst is not None:
            command = "PM " + str(m_v)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_Pulse(self, pulse_v):
        if self.conn.inst is not None:
            command = "PU " + str(pulse_v)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_th(self, bp_v):
        if self.conn.inst is not None:
            command = "PH " + str(bp_v)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    def set_td(self, mi_v):
        if self.conn.inst is not None:
            command = "PT " + str(mi_v)
            self.conn.inst.write_delay = 0.5
            self.command(command)
        else:
            print("No connection to instrument.")

    """
    Measurement functionality settings
    These functions determine the functionality of the instrument
    FN1: C-G function measures capacitance and conductance 
    FN2: C-V function measures capacitance and voltage 
    FN5: C-t measures capacitance and time 
    """
    def set_double(self):
        if self.conn.inst is not None:
            self.command("IB3") #sets biasing to double sweep
    
    def default_single(self):
        if self.conn.inst is not None:
            self.command("IB2") #set biasing
            self.command("MS2") #measurement speed set to medium
            self.command("FL")  #float mode
            self.command("FN1") #C-G function
            self.command("CEI") #enable correction
            self.command("TR1") #changes to hold/manual sweep
            self.command("LE1") #set cable length
            self.command("SL2") #signal level to sl2
            self.command("RA1") #C-G range to auto
            #default settings for CV
            self.set_DCV(5.0) 
            self.set_StartV(0.0)
            self.set_StopV(5.0)
            self.set_Hold_Time(0.01)
            self.set_StepV(0.01)
            self.set_StepT(0.03)
        else:
            print("No connection to instrument.")

    def default_CT(self):
        if self.conn.inst is not None:
            self.command("FN5") #C-t function
            self.command("IB5") #set biasing
            self.command("FL") #float mode
            self.command("LE1") #set cable length
            self.command("MS1") #measurement speed set to medium
            self.command("RA1") #C-G range to auto
            self.command("TR1") #changes to hold/manual sweep
            
            #default settings for CT
            self.set_Pulse(0.0)
            self.set_Measure_pulse(0.0)
            self.set_NOFREAD(10)
            self.set_th(1.0)
            self.set_td(0.01)
            self.command("SL2") #signal level to 30
        else:
            print("No connection to instrument.")

    def single_config(self):
        self.set_DCV(self.DC_V)
        self.set_StartV(self.Start_V)    
        self.set_StopV(self.Stop_V)
        self.set_StepV(self.Step_V)
        self.set_Hold_Time(self.Hold_T)
        self.set_StepT(self.Step_T)
        self.command("IB2") #set biasing to Single Sweep

    """def set_cvfunc(self):
        if self.conn.inst is not None:
            self.command("FN2")
        else:
            print("No connection to instrument.")"""

    def set_ctfunc(self):
        if self.conn.inst is not None:
            self.command("FN5")
    
    def set_cgtfunc(self):
        if self.conn.inst is not None:
            self.command("FN4")

    """
    None Numerical Settings
    Mode configurations:
    Floating mode: FL
    Ground mode: GN

    Measurement speed:
    Slow: MS3
    Medium: MS2
    Fast: MS1

    Signal level:
    SL1: 10
    SL2: 30

    Cable length:
    LE1: 1m
    LE2: 2m
    LE3: 3m

    Trigger/Sweep:
    TR1: repeat
    TR2: EXT
    TR3: Hold/manual sweep (Single)
    """

    def set_float(self):
        if self.conn.inst is not None:
            self.command("FL")
        else:
            print("No connection to instrument.")
    
    def set_ground(self):
        if self.conn.inst is not None:
            self.command("GN")
        else:
            print("No connection to instrument.")

    def set_slow(self):
        if self.conn.inst is not None:
            self.command("MS3")
        else:
            print("No connection to instrument.")
    
    def set_medium(self):
        if self.conn.inst is not None:
            self.command("MS2")
        else:
            print("No connection to instrument.")

    def set_fast(self):
        if self.conn.inst is not None:
            self.command("MS1")
        else:
            print("No connection to instrument.")

    def set_signal_10(self):
        if self.conn.inst is not None:
            self.command("SL1")
        else:
            print("No connection to instrument.")

    def set_signal_30(self):
        if self.conn.inst is not None:
            self.command("SL2")
        else:
            print("No connection to instrument.")

    def set_cable_1(self):
        if self.conn.inst is not None:
            self.command("LE1")
        else:
            print("No connection to instrument.")

    def set_cable_2(self):
        if self.conn.inst is not None:
            self.command("LE2")
        else:
            print("No connection to instrument.")

    def set_cable_3(self):
        if self.conn.inst is not None:
            self.command("LE3")
        else:
            print("No connection to instrument.")

    def set_repeat(self):
        if self.conn.inst is not None:
            self.command("TR1")

    def set_ext(self):
        if self.conn.inst is not None:
            self.command("TR2")

    def set_hold(self):
        if self.conn.inst is not None:
            self.command("TR3")

## Individual Functions ###########################################################################################

    #Functions to set the function of the instrument
    def set_cg(self):
        if self.conn.inst is not None:
            self.command("FN1")
        else:
            print("No connection to instrument.")
    
    def set_c(self):
        if self.conn.inst is not None:
            self.command("FN2")
        else:
            print("No connection to instrument.")

    def set_g(self):
        if self.conn.inst is not None:
            self.command("FN3")
        else:
            print("No connection to instrument.")

    def set_gtfunc(self):
        if self.conn.inst is not None:
            self.command("FN6")

    #Functions to set MEAS Range
    def set_auto(self):
        if self.conn.inst is not None:
            self.command("RA1")
        else:
            print("No connection to instrument.")

    def set_manual(self):
        if self.conn.inst is not None:
            self.command("RA0")
        else:
            print("No connection to instrument.")

    def set_10pf(self):
        if self.conn.inst is not None:
            self.command("RM1")
        else:
            print("No connection to instrument.")

    def set_100pf(self):
        if self.conn.inst is not None:
            self.command("RM2")
        else:
            print("No connection to instrument.")
    
    def set_10nf(self):
        if self.conn.inst is not None:
            self.command("RM3")
        else:
            print("No connection to instrument.")

    # Functions to set the trigger/sweep mode of the instrument

    def set_int(self):
        if self.conn.inst is not None:
            self.command("TR1")
        else:
            print("No connection to instrument.")

    def set_ext(self):
        if self.conn.inst is not None:
            self.command("TR2")
        else:
            print("No connection to instrument.")

    def set_hold(self):
        if self.conn.inst is not None:
            self.command("TR3")
        else:
            print("No connection to instrument.")

###################################################################################################################

    #Functions to begin data collection
    ###Commands sent to the HP4280A to start and stop sweeps
    def init_sweep(self):
        if self.conn.inst is not None:
            self.command("TR3")
            self.command("SW1")
            print("Sweep Initialized")
        else:
            print("No connection to instrument.")

    def stop_sweep(self):
        if self.conn.inst is not None:
            self.command("IB2")
            self.command("SW0")
            print("Sweep Stopped")
        else:
            print("No connection to instrument.")

    def sweep_measure(self):
        if self.conn.inst is not None:
            self.conn.inst.timeout = 1000000
            self.command("V01")
            self.command("SW1")
            self.command("BL1")
            self.command("BD")
            self.command("READ?")
            response = self.ReadBlockResponseAscii()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            uploads_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
            os.makedirs(uploads_folder, exist_ok=True)  # Ensure the uploads folder exists
            filename = f"data_{timestamp}.csv"
            file_path = os.path.join(uploads_folder, filename)
            if response is not None:
                print("Data Received: ", response)
                self.mkcsv(response, filename, uploads_folder)
                self.command("SW0")
                self.conn.inst.timeout = 10000
                print("Sweep Stopped")
                return file_path  # Return the file path
            else:
                print("No data received")
                return None
        else:
            print("No connection to instrument.")
            return None
    
    """
    def pulse_sweep(self, num, stopv):
        if self.conn.inst is not None:
            try:
                temp1 = self.Stop_V
                temp2 = self.Step_V
                temp3 = self.Start_V
                for i in range(num):  
                    temp = self.Start_V
                    self.set_StopV(stopv)
                    self.set_StepV(temp)
                    self.command("SW1")
                    time.sleep(self.sweep_time_calc())
                    self.command("SW0")
                    self.command("BL1")
                    self.command("BD")
                    self.command("READ?")
                    response = self.ReadBlockResponseAscii()
                    if response is not None:
                        print("Data Received: ", response)
                        self.mkcsv(response)
                    else:
                        print("No data received")
                    self.set_StartV(temp+temp2)
                    if temp == temp1:
                        self.command("SW0")   
                        break
                self.set_StopV(temp1)
                self.set_Step(temp2)
                self.set_StartV(temp3)                 
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")"
        """
    
    def pulse_sweep(self):
        if self.conn.inst is not None:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"data_{timestamp}.csv"
            try:
                self.set_double()
                current_end = self.Step_V
                actual_end = self.Stop_V
                while current_end < actual_end+self.Step_V:
                    self.set_StopV(current_end)
                    self.set_StartV(current_end)
                    self.command("SW1")
                    self.conn.inst.timeout = 6000000
                    self.command("BL1")
                    self.command("BD")
                    self.command("READ?")                        
                    response = self.ReadBlockResponseAscii()
                    if response is not None:
                        print("Pulse Complete")
                        print("Data Received: ", response)
                        self.mkcsv(response, filename)
                    else:
                        print("No data received")
                    self.command("SW0")
                    self.conn.inst.timeout = 10000
                    print("Pulse complete\n")
                    current_end += self.Step_V

            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")


    #Function to calculate the number of steps taken in the sweep
    def step_calc(self):
        num_Steps = 0.0
        if self.Step_V == 0:
            num_Steps = ((self.Stop_V - self.Start_V) / 1)
            return num_Steps
        else:
            num_Steps = (((self.Stop_V - self.Start_V) / self.Step_V) + 1)
            return num_Steps

    #Function to calculate the sweep time    
    def sweep_time_calc(self):
        num_Steps = self.step_calc()
        calc = ((num_Steps * (self.Step_T + self.Hold_T) * 1000) + 1000)
        print(calc/1000)
        return (calc/1000)

    #Function to send and recieve data from the instrument
    def command(self, cmd):
        if self.conn.inst is not None:
            try:
                #self.conn.inst.write_raw(cmd + "\n")
                self.conn.inst.write(cmd)
                #time.sleep(0.0)
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        print("Command:", cmd)
    
    def read(self):
        if self.conn.inst is not None:
            try:
                return self.conn.inst.read()
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")
    
    def rq(self, cmd):
        if self.conn.inst is not None:
            try:
                return self.conn.inst.query(cmd + "\n")
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")
    
    #clears values of the instrument
    def clear(self):
        if self.conn.inst is not None:
            self.conn.inst.clear()
            print("Clearing the instrument")
        else:
            print("No connection to instrument.")
    
    #data processing functions
    def ReadBlockResponseAscii(self):
        if self.conn.inst is not None:
            try:
                response_string = self.conn.inst.read()#self.conn.inst.read()
                return response_string
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")

    #reads binary response
    def ReadBlockResponse(self):
        if self.conn.inst is not None:
            try:
                response = self.conn.inst.read_raw()
                return response
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")

    def ProcessAscii(self, response_string):
        if response_string is not None:
            print("Data Received: ", response_string)
            self.mkcsv(response_string)
        else:
            print("No data received")

    def ProcessBinary(self, response):
        if response is not None & len(response) > 0:
            bin_response = self.conn.inst.read_raw()
            print("Data Received: ", bin_response)
            self.csv(bin_response)
        else:
            print("No data received")

    def data_standard_transfer_mode(self):
        if self.conn.inst is not None:
            try:
                self.command("BLO")
                self.command("READ?")
                response = self.read()
                if response is not None:
                    print("Data Received: ", response)
                    self.mkcsv(response)
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
        else:
            print("No connection to instrument.")
    
    def read_data(self):
        if self.conn.inst is not None:
            try:
                self.command("AS")
                self.command("MEASURE")
                response = self.read()
                return response
            except pyvisa.errors.VisaIOError as e:
                error_code = e.error_code
                print(f"GPIB Communication Error [{error_code}]: {e.description}")
            return None
        else:
            print("No connection to instrument.")

    def mkcsv(self, data, filename='data.csv', file_path=None):
        """
        Writes the measurement data to a CSV file in the correct format, with date and time added to the filename.
        """
        if file_path is None:
            uploads_folder = os.path.join(os.path.dirname(__file__), "uploads")
            os.makedirs(uploads_folder, exist_ok=True)  # Ensure the uploads folder exists
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"{os.path.splitext(filename)[0]}_{timestamp}.csv"
            file_path = os.path.join(uploads_folder, filename)

        try:
            with open(file_path, "w", newline="") as file:
                file.write(data)
            print(f"Data saved to {file_path}")
            return file_path  # Return the full path of the saved file
        except Exception as e:
            print(f"Error saving data to CSV: {e}")
            return None