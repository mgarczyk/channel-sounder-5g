from RsInstrument import *
from time import sleep
import json

try:
    with open ("config.json") as config_f:
        config = json.load(config_f)
        IP_ADDRESS_ANALYZER = config["IP_ADDRESS_ANALYZER"]
        PORT = config["PORT"]
        CONNECTION_TYPE = config["CONNECTION_TYPE"]
        TRACE_FILE = config["TRACE_FILE"] 
        MEASURE_TIME = config["MEASURE_TIME"]
        resource = f'TCPIP::{IP_ADDRESS_ANALYZER}::{PORT}::{CONNECTION_TYPE}'  # Resource string for the device
        instrument = RsInstrument(resource, True, True, "SelectVisa='socket'")   
        config_f.close()
except FileNotFoundError:
    print("Brak pliku konfiguracyjnego.")
    exit()

'''
- option SelectVisa:
    - 'SelectVisa = 'socket' - uses no VISA implementation for socket connections 
                             - you do not need any VISA-C installation
    - 'SelectVisa = 'rs' - forces usage of Rohde&Schwarz Visa
    - 'SelectVisa = 'ni' - forces usage of National Instruments Visa     
'''

#
# Define subroutines
#


def com_prep():
    """Preparation of the communication (termination, timeout, etc...)"""
    
    print(f'VISA Manufacturer: {instrument.visa_manufacturer}')  # Confirm VISA package to be chosen
    instrument.visa_timeout = 5000  # Timeout in ms for VISA Read Operations
    instrument.opc_timeout = 3000  # Timeout in ms for opc-synchronised operations
    instrument.instrument_status_checking = True  # Error check after each command
    instrument.clear_status()  # Clear status register
  
    
def close():
    """Close the VISA session"""
    instrument.close()


def com_check():
    """Check communication with the device by requesting it's ID"""
    idn_response = instrument.query_str('*IDN?')
    print('Hello, I am ' + idn_response)
    
   
def meas_prep(freq : str, span : str, mode : str):
    instrument.write_str_with_opc(f'FREQuency:CENTer {freq}')  
    instrument.write_str_with_opc(f'FREQuency:SPAN {span}')  
    instrument.write_str_with_opc(f'DISPlay:TRACe1:MODE {mode}')  # Trace to Max Hold


def trace_get():
    """Initialize continuous measurement, stop it after the desired time, query trace data"""
    instrument.write_str_with_opc('INITiate:CONTinuous ON')  # Continuous measurement on trace 1 ON
    print('Please wait for maxima to be found...')
    sleep(int(MEASURE_TIME))  # Wait for preset record time
    instrument.write('DISPlay:TRACe1:MODE VIEW')  # Set trace to view mode / stop collecting data
    instrument.query_opc()
    sleep(0.5)

    # Get y data (amplitude for each point)
    trace_data = instrument.query('Trace:DATA? TRACe1')  # Read y data of trace 1
    csv_trace_data = trace_data.split(",")  # Slice the amplitude list
    trace_len = len(csv_trace_data)  # Get number of elements of this list

    # Reconstruct x data (frequency for each point) as it can not be directly read from the instrument
    start_freq = instrument.query_float('FREQuency:STARt?')
    span = instrument.query_float('FREQuency:SPAN?')
    step_size = span / (trace_len-1)

    # Now write values into file
    file = open(TRACE_FILE, 'a+')  # Open file for writing
    max_amp = -150
    x = 0  # Set counter to 0 as list starts with 0
    while x < int(trace_len):  # Perform loop until all sweep points are covered
        amp = float(csv_trace_data[x])
        if amp > max_amp:
            max_amp = amp
            max_x = x
        x = x+1
    file.write(f'{(start_freq + max_x * step_size):.1f}')  # Write adequate frequency information
    file.write(";")
    file.write(f'{max_amp:.2f}')  # Write adequate amplitude information
    file.write("\n")
    file.close()  # CLose the file
    
if __name__ == "__main__":
    com_prep()
    com_check()
    meas_prep("20e9", "1e6", "MAXHold ")
    trace_get()
    close()
    print('Program successfully ended.')
    print('Wrote trace data into', TRACE_FILE)
    exit()