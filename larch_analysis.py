import numpy as np
import matplotlib.pyplot as plt
import os
import larch
from larch import Group
from larch.xafs import pre_edge
import larch.io

data_dir = r'C:\Users\jmoncadav\OneDrive - Brookhaven National Laboratory\Documents\EXAFS ANALYSIS\PNNL_PySpecNotebooks_Share\Data\Fe_Data'
file_name = '\FeS2_rt_01.xdi'


# Import a given file and create a Larch group
dat = larch.io.read_xdi(data_dir+file_name)

# Plot XAFS data
plt.figure(figsize=(8, 6))

x = dat.energy
y = dat.mutrans
plt.plot(x, y, label='FeS2')

plt.legend(loc='upper right', ncol=1, prop={'size': 24})
plt.xlabel('Energy (eV)', size=20)
plt.ylabel('x\u03BC', size=20)
plt.tick_params(direction='in', top='True', right ='True', length=6)
plt.show()

# Normalize spectrum and save relevant info to the data's group
pre_edge(dat.energy, dat.mutrans, group=dat, pre1=-150, pre2=-30, norm1=150, norm2=750, nnorm=2)

# Plot raw data with pre- and post-edge lines
plt.figure(figsize=(8, 6))
plt.plot(dat.energy, dat.mutrans)
plt.plot(dat.energy, dat.pre_edge)
plt.plot(dat.energy, dat.post_edge)

plt.xlabel('Energy (eV)', size=20)
plt.ylabel('x\u03BC', size=20)
plt.tick_params(direction='in', top='True', right ='True', length=6)
plt.show()