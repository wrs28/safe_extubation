import pandas as pd
import os
import math
import numpy as np
from directories import project_dir, processed_data_dir, mimic_dir
from definitions import tables


# number of rows in CHARTEVENTS to read in at a time (there are 330_712_483 lines in CHARTEVENTS)
CHUNK_SIZE = 10**6
NUM_CHUNKS = np.inf


# time window from end of intubation episode that chart data is extracted
WINDOW_1_SIZE = pd.Timedelta(hours=2)
WINDOW_2_SIZE = pd.Timedelta(hours=6)


# load in ventilation times
path = os.path.join(processed_data_dir, "vent_episodes.h5")
vent_episodes = pd.read_hdf(path, "vent_episodes")


# initialize chartevents dataframe
ce_columns = ["SUBJECT_ID", "ICUSTAY_ID", "ITEMID", "CHARTTIME", "VALUE", "VALUENUM", "VALUEUOM"]
dtypes = {
  "VALUE" : str,
  "VALUENUM" : float,
  "VALUEUOM" : str
}

print("Extracting relevent chart events")
path = os.path.join(mimic_dir, tables["chartevents"] + ".csv")
ce1_list = []
ce2_list = []
count = 0
for chunk in pd.read_csv(path, chunksize=CHUNK_SIZE, usecols=ce_columns, dtype=dtypes, parse_dates = ["CHARTTIME"]):
  count += 1
  if count <= NUM_CHUNKS:
    print("\tprocessing CHARTEVENTS chunk:",count, "of", math.ceil(330_712_483/CHUNK_SIZE))
    for (icustay, episode), group in vent_episodes.groupby(["ICUSTAY_ID", "EPISODE"]):
      # only extract chart data from before end of first intubation episode
      if episode==1:
        # one window period before end of episode
        interval1 = pd.Interval(group.ENDTIME.iloc[0] - WINDOW_1_SIZE, group.ENDTIME.iloc[0], closed="both")
        interval2 = pd.Interval(group.ENDTIME.iloc[0] - WINDOW_2_SIZE, group.ENDTIME.iloc[0], closed="both")
        # loop through all the times in a given ICUSTAY
        for time, time_group in chunk[chunk.ICUSTAY_ID == icustay].groupby("CHARTTIME"):
          # but only keep those in the window
          if time in interval1:
            ce1_list.append(time_group)
          if time in interval2:
            ce2_list.append(time_group)
  else:
    break


ce1 = pd.concat(ce1_list)
ce2 = pd.concat(ce2_list)

# save out result
ce1.ICUSTAY_ID = ce1.ICUSTAY_ID.astype(int)
ce1.SUBJECT_ID = ce1.SUBJECT_ID.astype(int)
ce1.ITEMID = ce1.ITEMID.astype(int)
ce2.ICUSTAY_ID = ce2.ICUSTAY_ID.astype(int)
ce2.SUBJECT_ID = ce2.SUBJECT_ID.astype(int)
ce2.ITEMID = ce2.ITEMID.astype(int)
print("Saving processed chart events")
path = os.path.join(processed_data_dir, "chart_data.h5")
ce1.to_hdf(path, "charts1", mode="w", format="Table")
ce2.to_hdf(path, "charts2", mode="a", format="Table")

print("Done processing chart events!")
