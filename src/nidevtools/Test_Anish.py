import common
import re

input_data = "site0\\a, site0\\b,  site1\\c  ,site2\\d,site3/e, pin5"
output_data = common.channel_list_to_pins(input_data)
print(input_data)
print(output_data)
pattern = r"/\\"
a = re.split(r'[/\\]', input_data)
# print(a)
