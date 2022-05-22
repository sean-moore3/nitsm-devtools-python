import re

import nidevtools.abstract_switch as ni_dt_abs
import nidevtools.common as ni_dt_common

# This file is used for testing some common functions

input_data = "site0\\a, site0\\b,  site1\\c  ,site2\\d,site3/e, pin5"
output_data = ni_dt_common.channel_list_to_pins(input_data)
print(input_data)
print(output_data)
pattern = r"/\\"
a = re.split(r"[/\\]", input_data)
print(a)

data = []
for pin_count in range(10):
    pin_str = [""]
    pins_array = pin_str * pin_count
    # cluster = {pins_array}
    data.append(pins_array)

print(data)

