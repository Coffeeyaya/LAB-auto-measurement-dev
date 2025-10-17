import os
import pandas as pd
from pathlib import Path

def find_header_row(file_path):
    """
    find the location of actual data in file
    """
    header_row = 0
    with open(file_path, "r") as f:
        for j, line in enumerate(f):
            if line.strip().startswith('\"Index\"'):
                header_row = j
                break
    if header_row == 0:
        print('can not find header row')
    return header_row

column_names_dict = {
    'idvg': ['gate Voltage (V)', 'drain Current (A)'],
    'idvd': ['drain Voltage (V)', 'drain Current (A)'],
    'time': ['drain Time (s)', 'drain Current (A)']
}

def process(source_folder, target_folder):
    csv_files = [f for f in os.listdir(source_folder) if f.endswith('.csv')]

    for i in range(len(csv_files)):
        file = csv_files[i]
        measurement_type = file.split('_')[1]
        file_path = os.path.join(source_folder, file)

        df = pd.read_csv(file_path, skiprows=find_header_row(file_path), index_col=0)

        # df.dropna(how='all', inplace=True)
        # df.reset_index(drop=True, inplace=True)

        selected_columns = df[column_names_dict[measurement_type]]

        new_file = f'{os.path.splitext(os.path.basename(file_path))[0]}.csv'
        new_file_path = os.path.join(target_folder, new_file)
        selected_columns.to_csv(new_file_path, index=False) # index = False

# recursively process all csv files in folder
raw_data_folder = Path('/Users/tsaiyunchen/Desktop/lab/master/measurement_dev/receive_data')
# date = Path('20250925')
# device = Path('data_mw_6-3')
data_folder = Path('data')
process_root_folder = Path('./process')

# measurement_folder = raw_data_folder / date / device
measurement_folder = raw_data_folder / data_folder
# process_folder = process_root_folder / date / device
process_folder = process_root_folder / data_folder

os.makedirs(process_folder, exist_ok=True)

process(measurement_folder, process_folder)

