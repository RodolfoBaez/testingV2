from visacon import VisaCon
from controller import controller

###test calls
conn = VisaCon()
ctrl = controller(conn, 5.0, (0.0), 5.0, 0.50, 1.0, 1.0)
ctrl.clear()
#ctrl.single_config()
#ctrl.set_cgtfunc() ### Set the CGT function
#ctrl.set_ctfunc()
#ctrl.default_CT()
#ctrl.set_double()
#ctrl.sweep_measure()
#ctrl.pulse_sweep(5, 5.0)
#ctrl.pulse_sweep()

#ctrl.single_config()
"""
ctrl.default_CT()
ctrl.set_td(2) # Set the delay time to 2 seconds
ctrl.set_th(2) # Set the hold time to 2 seconds
ctrl.set_Measure_pulse(0.10) # Set the measure pulse to 0.10 seconds
ctrl.set_Pulse(3) # Set the number of pulses to 3
ctrl.set_NOFREAD(10) # Set the number of reads to 10
ctrl.sweep_measure()
"""
"""
def pulse_algorithm_test(v_start=0.0, v_step=0.5, v_end=5.0):
    current_end = v_step
    actual_end = v_end
    init_step = v_step
    pulse_step = v_step
    while current_end <= actual_end:
        print("self.set_end", current_end)
        print("self.set_step", pulse_step)
        v = v_start
        while v <= current_end:
            print(v)
            v += v_step
        print("Pulse complete\n")  # Marks the end of one pulse cycle
        current_end += init_step
        pulse_step = current_end
        print('current_end', current_end)
        print('actual_end', actual_end)

pulse_algorithm_test()

"""