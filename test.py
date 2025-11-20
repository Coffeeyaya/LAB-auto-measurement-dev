params = {
        "material": "mw",
        "device_number": "1-1",
        "measurement_type": "time",
        "measurement_index": "0",
        "laser_function": "1_on_off",
        "rest_time": "2",
        "dark_time1": "2",
        "dark_time2": "2" 
    }

def change_params(params, key_values_pairs):
    params_copy = params.copy()
    for k, v in key_values_pairs.items():
        params_copy[k] = v
    return params_copy

work_flow = [{'measurement_index': '0',
              'laser_function': '1_on_off'
              },
              {'measurement_index': '1',
              'laser_function': 'multi_on_off'
              }
              ]

for job in work_flow:
    params_2 = change_params(params, job)
    print(params_2)