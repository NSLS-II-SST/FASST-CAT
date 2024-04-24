  
#!/usr/bin/env python
#
#   Copyright 2012 Jonas Berg
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

"""
.. moduleauthor:: Jonas Berg <pyhys@users.sourceforge.net>
Driver for the Eurotherm3500 process controller, for communication via the Modbus RTU protocol.
This Python file was changed (committed) at 
$Date: 2012-08-26 16:14:30 +0200 (Sun, 26 Aug 2012) $, 
which was $Revision: 155 $.
"""

import minimalmodbus
from time import sleep, strftime, time
from datetime import datetime
#import matplotlib.pyplot as plt

__author__  = "Jonas Berg"
__email__   = "pyhys@users.sourceforge.net"
__license__ = "Apache License, Version 2.0"

__revision__  = "$Rev: 155 $"
__date__      = "$Date: 2012-08-26 16:14:30 +0200 (Sun, 26 Aug 2012) $"

class Eurotherm3500( minimalmodbus.Instrument ):
  """Instrument class for Eurotherm 3500 process controller. 
  
  Communicates via Modbus RTU protocol (via RS232 or RS485), using the *MinimalModbus* Python module.    
  Args:
      * portname (str): port name
      * subordinateaddress (int): subordinate address in the range 1 to 247
  Implemented with these function codes (in decimal):
      
  ==================  ====================
  Description         Modbus function code
  ==================  ====================
  Read registers      3
  Write registers     16
  ==================  ====================
  """
  
  def __init__(self, portname, subordinateaddress):
    minimalmodbus.Instrument.__init__(self, portname, subordinateaddress)
  
  ## Process value
  
  def get_pv_loop1(self):
    """Return the process value (PV) for loop1."""
    return self.read_register(289, 1)
  
  # def get_pv_loop2(self):
      # """Return the process value (PV) for loop2."""
      # return self.read_register(1313, 1)
  
  # def get_pv_module3(self):
      # """Return the process value (PV) for extension module 3 (A)."""
      # return self.read_register(370, 1)

  # def get_pv_module4(self):
      # """Return the process value (PV) for extension module 4 (A)."""
      # return self.read_register(373, 1)

  # def get_pv_module6(self):
      # """Return the process value (PV) for extension module 6 (A)."""
      # return self.read_register(379, 1)

  def create_pv_log(self):
                
    plt.ion()
    x = []
    y = []

    def write_temp(temp):
      with open('euro_temp.csv', 'a') as log:
        log.write('{0},{1}\n'.format(strftime('%Y-%m-%d %H:%M:%S'),str(temp)))

    def graph(temp):
      y.append(temp)
      x.append(time())
      plt.clf()
      plt.scatter(x,y)
      plt.plot(x,y)
      plt.draw()
      plt.xlabel('Time (s)')
      plt.ylabel('Temperature (C)')
      
    while True:        
      temp = self.read_register(289, 1)
      write_temp(temp)
      graph(temp)
      plt.pause(1)
      
  ## Programmed heating, cooling, and dwell
  
  def heating_event(self, rate_sp = None, sp = None):
    """Loops over actual temperature in an heating event until setpoint is reached"""
    print('Starting heating event:')
    try:
      print('Heating rate: {} C/min'.format(rate_sp))
      rate_sp = float(rate_sp)
      self.write_register(35, rate_sp, 1)
    except:
      rate_sp = None
      
    try:
      print('Setpoint: {} C'.format(sp))
      sp = float(sp)
      self.write_register(24, sp, 1)
    except:
      sp = None
      
    while True:
      try:
        temp_pv = self.read_register(1, 1) 
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      try:
        temp_wsp = self.read_register(1, 1)
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      try:
        result = float(temp_pv) < float(sp)
        if result == True:
          temp_pv = float(temp_pv)
          temp_wsp = float(temp_wsp)
          print('WSP Temperature: {} C'.format(temp_wsp),
                   ' / PV Temperature: {} C'.format(temp_pv), end = "\r")          
          sleep(1)
        else:
          print('{} C setpoint reached!'.format(sp))
          break
      except TypeError:
        continue
      
        
  def cooling_event(self, rate_sp = None, sp = None):
    """Loops over actual temperature in an cooling event until setpoint is reached"""
    
    print('Starting cooling event:')
    try:
      print('Heating rate: {} C/min'.format(rate_sp))
      rate_sp = float(rate_sp)
      self.write_register(35, rate_sp, 1)
    except:
      rate_sp = None
      
    try:
      print('Setpoint: {} C'.format(sp))
      sp = float(sp)
      self.write_register(24, sp, 1)
    except:
      sp = None
      
    while True:
      try:
        temp_pv = self.read_register(289, 1) 
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      try:
        temp_wsp = self.read_register(1, 1)
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      try:
        result = float(temp_pv) > float(sp)
        if result == True:
          temp_pv = float(temp_pv)
          sp = float(sp)
          print('Setpoint Temperature: {} C'.format(sp),
                  ' / Process Temperature: {} C'.format(temp_pv), end = "\r")
          sleep(1)
        else:
          print('{} C setpoint reached!'.format(sp))
          break
      except TypeError:
        continue
        
  def temperature_ramping_event(self,rate_sp = None, sp = None ):
    while True:
      try:
        temp_pv = self.read_register(289, 1) 
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      try:
        result = float(temp_pv) > float(sp)
        if result == True:
          self.cooling_event(rate_sp, sp)
          print('start cooling event')
          break
        else:
          self.heating_event(rate_sp, sp)
          print('start heating event')
          break
      except TypeError:
        continue

  def setpoint_finish_experiment(self):
    """Loops over actual temperature in an cooling event until setpoint is reached"""
    rate_sp=10
    sp=18
    
    print('adjust temperature set point to 18C:')
    try:
      print('cooling rate: {} C/min'.format(rate_sp))
      rate_sp = float(rate_sp)
      self.write_register(35, rate_sp, 1)
    except:
      rate_sp = None
      
    try:
      print('Setpoint: {} C'.format(sp))
      sp = float(sp)
      self.write_register(24, sp, 1)
    except:
      sp = None
      


  def time_event(self, time_at_sp, argument):
    """Loops over actual temperature at setpoint temperature dunring a specific time"""
    print('{} time: {} seconds'.format(argument, time_at_sp))
    print('============================================================')
    time_counter = 0
    time_at_sp = int(time_at_sp)
    for value in range(0, time_at_sp):   
      time_counter = time_counter + 1
      sleep(1)
      print('Time elapsed: {} s'.format(time_counter), end = "\r")    
    print('End of {} seconds waiting time'.format(time_at_sp))
    
  ## Remote Triggering
  def DRIFTS_PID(self):
    
    self.write_register(6, 86.92)
    self.write_register(8, 95.52)
    self.write_register(9, 15.92)
    p=self.read_register(6, 2)
    i=self.read_register(8, 2)
    d=self.read_register(9, 2)
    
    print("PID for DRIFTS cell is imported" + " ,proportional band={}".format(p) + " , integral time={}".format(i) + ", derivative time={}".format(d) + ", please switch output to LOCAL")
   
  def Clausen_Cell_PID(self):
    
    self.write_register(6, 600)
    self.write_register(8, 20)
    self.write_register(9, 4)
    p=self.read_register(6)
    i=self.read_register(8)
    d=self.read_register(9)
    
    print("PID for Clausen cell is imported" + " ,proportional band={}".format(p) + ", integral time={}".format(i) + ", derivative time={}".format(d) + ", please switch output to AUX")
  
  def MS_ON(self):
    """Sends a logic value (0 or 1) to perform remote digital triggering to RlyAA"""
    self.write_register(363, 0)
    sleep(10)
    print('MS sequence started')
    
  def MS_OFF(self):
    """Sends a logic value (0 or 1) to perform remote digital triggering to RlyAA"""
    self.write_register(363, 1)
    sleep(10)
    print('MS sequence stopped')
    
  def IR_ON(self):
    """Sends 5V to perform remote triggering to logic A"""    
    self.write_register(376, 5)
    sleep(1)
    self.write_register(376, 0)
    print('IR data acquisition started')
    now = datetime.now()
    dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
    print('\ndate and time =', dt_start)
    
  def pulse_ON(self):
    """Sends 5V to perform remote triggering to logic A"""    
    self.write_register(376, 3)
    #sleep(1)
    #self.write_register(376, 0)
    print('Pulse ON')
    now = datetime.now()
    dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
    print('\ndate and time =', dt_start)
    
  def pulse_OFF(self):
    """Sends 5V to perform remote triggering to logic A"""    
    self.write_register(376, 0)
    #sleep(1)
    #self.write_register(376, 0)
    print('Pulse OFF')
    now = datetime.now()
    dt_start = now.strftime("%m/%d/%Y %H:%M:%S")
    print('\ndate and time =', dt_start)
    
  def IR_STATUS(self):
    """Sends 5V to perform remote triggering to logic A"""    
    while True:
      try:
        result = self.read_register(361)
      except IOError:
        continue
        # print("Failed to read from instrument")
      except ValueError:
        continue
        # print("Instrument response is invalid")
      if result == 1:
        break
      elif result == 0:
        sleep(0.1)
      continue

  ## Auto/manual mode
  
  def is_manual_loop1(self):
    """Return True if loop1 is in manual mode."""
    return self.read_register(273, 1) > 0
  
  ## Setpoint
  
  def get_sptarget_loop1(self):
    """Return the setpoint (SP) target for loop1."""
    return self.read_register(2, 1)
  
  def get_sp_loop1(self):
    """Return the (working) setpoint (SP) for loop1."""
    return self.read_register(5, 1)
  
  def set_sp_loop1(self, value):
    """Set the SP1 for loop1.
      
    Note that this is not necessarily the working setpoint.
    Args:
        value (float): Setpoint (most often in degrees)
    """
    self.write_register(24, value, 1)
  
  # def get_sp_loop2(self):
      # """Return the (working) setpoint (SP) for loop2."""
      # return self.read_register(1029, 1)
  
  ## Setpoint rate
  
  def get_sprate_loop1(self):
    """Return the setpoint (SP) change rate for loop1."""
    return self.read_register(35, 1)   
  
  def set_sprate_loop1(self, value):
    """Set the setpoint (SP) change rate for loop1.
      
    Args:
        value (float): Setpoint change rate (most often in degrees/minute)
    """
    self.write_register(35, value, 1)  
  
  def is_sprate_disabled_loop1(self):
    """Return True if Loop1 setpoint (SP) rate is disabled."""
    return self.read_register(78, 1) > 0

  def disable_sprate_loop1(self):
    """Disable the setpoint (SP) change rate for loop1. """
    VALUE = 1
    self.write_register(78, VALUE, 0) 
      
  def enable_sprate_loop1(self):
    """Set disable=false for the setpoint (SP) change rate for loop1.
    
    Note that also the SP rate value must be properly set for the SP rate to work.
    """
    VALUE = 0
    self.write_register(78, VALUE, 0) 
  
  ## Output signal
  
  def get_op_loop1(self):
    """Return the output value (OP) for loop1 (in %)."""
    return self.read_register(85, 1)
 
  def is_inhibited_loop1(self):
    """Return True if Loop1 is inhibited."""
    return self.read_register(268, 1) > 0

  # def get_op_loop2(self):
      # """Return the output value (OP) for loop2 (in %)."""
      # return self.read_register(1109, 1)
  
  ## Alarms

  def get_threshold_alarm1(self):
    """Return the threshold value for Alarm1."""
    return self.read_register(10241, 1)
  
  def is_set_alarmsummary(self):
    """Return True if some alarm is triggered."""
    return self.read_register(10213, 1) > 0
    
########################
## Testing the module ##
########################

if __name__ == '__main__':

  minimalmodbus._print_out( 'TESTING EUROTHERM 3500 MODBUS MODULE')

  a = Eurotherm3500('COM9', 1)
  a.debug = False
  
  minimalmodbus._print_out( 'SP1:                    {0}'.format(  a.get_sp_loop1()             ))
  minimalmodbus._print_out( 'SP1 target:             {0}'.format(  a.get_sptarget_loop1()       ))
  minimalmodbus._print_out( 'SP2:                    {0}'.format(  a.get_sp_loop2()             ))
  minimalmodbus._print_out( 'SP-rate Loop1 disabled: {0}'.format(  a.is_sprate_disabled_loop1() ))
  minimalmodbus._print_out( 'SP1 rate:               {0}'.format(  a.get_sprate_loop1()         ))
  minimalmodbus._print_out( 'OP1:                    {0}%'.format( a.get_op_loop1()             ))
  minimalmodbus._print_out( 'OP2:                    {0}%'.format( a.get_op_loop2()             ))
  minimalmodbus._print_out( 'Alarm1 threshold:       {0}'.format(  a.get_threshold_alarm1()     ))
  minimalmodbus._print_out( 'Alarm summary:          {0}'.format(  a.is_set_alarmsummary()      ))
  minimalmodbus._print_out( 'Manual mode Loop1:      {0}'.format(  a.is_manual_loop1()          ))
  minimalmodbus._print_out( 'Inhibit Loop1:          {0}'.format(  a.is_inhibited_loop1()       ))
  minimalmodbus._print_out( 'PV1:                    {0}'.format(  a.get_pv_loop1()             ))
  minimalmodbus._print_out( 'PV2:                    {0}'.format(  a.get_pv_loop2()             ))
  minimalmodbus._print_out( 'PV module 3:            {0}'.format(  a.get_pv_module3()           ))
  minimalmodbus._print_out( 'PV module 4:            {0}'.format(  a.get_pv_module4()           ))
  minimalmodbus._print_out( 'PV module 6:            {0}'.format(  a.get_pv_module6()           ))

  #a.set_sprate_loop1(30)
  #a.enable_sprate_loop1() 

  minimalmodbus._print_out( 'DONE!' )

pass  