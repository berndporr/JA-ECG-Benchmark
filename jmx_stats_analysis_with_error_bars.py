# -*- coding: utf-8 -*-
"""
This code is used to analyse csv files generated by 'jmx_detector_analysis.py'
and normalise (using a global mean value) and map coefficients which represent
detector performance for jitter(J), missed beats(M), and extra ddetections(X).
These are combined to give an overall'JMX Benchmark' rating for a detector
which is shown for Einthoven II and Chest strap leads. The individual values
for J, M, and X are also plotted individually for Einthoven II and Chest strap.
Error bars have been added to the overall JMX Benchmark plots.

"""

import pandas as pd
import numpy as np
import os.path as path
import matplotlib.pyplot as plt
from ecgdetectors import Detectors

all_recording_leads=["einthoven_ii", "chest_strap_V2_V1"] # can be expanded if required
all_categories=["jitter", "missed", "extra"] # 


def mapping_curve():
    # equate mean point to cube root of 0.5 so that if all three parameters are average, when multiplied together we get 50% as an overall result
    for_x_is_1 = 0.5 ** (1. / 3) # i.e cube root of 0.5
    # To use individual parameters for comparison, use parameter^3, again to make 0.5=mean
    
    x = np.array([0.0, 1.0, 6.0, 10.0]) # 'source' input points for piecewise mapping
    # x = np.array([0.0, 1.0, 8.0, 15.0]) # alternative mapping for more detail in lower values.
    y = np.array([1.0, for_x_is_1, 0.2, 0.0]) # 'destination' output points for piecewise mapping
    z = np.polyfit(x, y, 3) # z holds the polynomial coefficients of 3rd order curve fit
    return z

def return_globals():
    global_filename ="results/global_results.csv" # set path to 'global_results.csv'
    if path.exists(global_filename) == True: # Does Global values file exist?
        global_values=pd.read_csv(global_filename, dtype=float, index_col=0)
        Global_jitter_mad=pd.Series.tolist(global_values["Global_jitter_mad"])[0]
        Global_missed_mean=pd.Series.tolist(global_values["Global_missed_mean"])[0]
        Global_extra_mean=pd.Series.tolist(global_values["Global_extra_mean"])[0]
        
    else: # Use default values if no Global file exists
        print()
        print('Using default Global reference mean values')
        print()
        Global_jitter_mad = 2.991280672344543
        Global_missed_mean = 2.761072988147224
        Global_extra_mean = 4.480973175296319
    
    return Global_jitter_mad, Global_missed_mean, Global_extra_mean

def normalise_and_map(param, category):
    # Identifies param type, normalises using appropriate global value, and
    # maps to benchmark value using 'poly' 3rd order polynomial
    global_constants=return_globals()
    poly=mapping_curve()
    # Normalise by dividing by appropriate global reference constant
    if category=='jitter':
        param_norm = param/global_constants[0]
    elif category=='missed':
        param_norm = param/global_constants[1]
    elif category=='extra':
        param_norm = param/global_constants[2]
    if param_norm<=10.0: # Is normalised param less than 10x the global reference?
        x = param_norm    
        param_mapped=(poly[0]*x*x*x)+(poly[1]*x*x)+(poly[2]*x)+poly[3]
    else:
        param_mapped=0.0 # if the input parameter is greater than 10x the global
        # reference, a returned value of 0.0 will signify failure as a detector,
        # and when multiplied, the overall benchmark will also be 0
    
    return param_mapped

def find_err_plus_minus(array_in, category):
    array_in= [x for x in array_in if ~np.isnan(x)] # remove nan's
    array=np.asarray(array_in) # make sure that it is an array
    mean_array=np.mean(array) # mean value to be mapped and SE applied to (+-)
    
    std_err = (np.std(array, ddof=1)) / np.sqrt(np.size(array)) # for std error
    
    mapped_mean=normalise_and_map(mean_array, category) # normalise and map mean value of array
    mapped_mean_plus=normalise_and_map((mean_array-std_err), category) # note: lower value maps higher
    mapped_mean_minus=normalise_and_map((mean_array+std_err), category) # note: higher value maps lower
    
    diff_pos=100.0*(mapped_mean_plus-mapped_mean) # scale x 100 as per JMX benchmark
    diff_neg=100.0*(mapped_mean-mapped_mean_minus) # scale x 100 as per JMX benchmark
    
    return diff_neg, diff_pos
        
def overall_benchmark(record_lead, detector, bench_stats):
    # 'bench_stats' is dictionary
    part_name='_accum_'+record_lead+'_'+detector
    bm=100.0 # set initial value of benchmark - multiply by all three individual values
    for key_name in bench_stats.keys():
        if part_name in key_name:
            #print[column]
            bm=bm*bench_stats.get(key_name)
        
    return bm

def category_benchmarks(record_lead, bench_stats):
    # Allow for both leads?
    jitter_list=[]
    missed_list=[]
    extra_list=[]
    for category in all_categories:
        for detector in all_detectors:
            for key_name in bench_stats.keys():
                if record_lead in key_name:
                    if category in key_name:
                        if detector in key_name:
                            exec(category+'_list.append(100.0*((bench_stats.get(key_name))**3))')
                       
    return jitter_list, missed_list, extra_list
            
def autolabel(rects): # https://matplotlib.org/3.1.1/gallery/lines_bars_and_markers/barchart.html
    """Attach a text label above each bar in *rects*, displaying its height."""
    for rect in rects:
        height = rect.get_height()
        height=int(height)
        ax.annotate('{}'.format(height),
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')

    
    
#%%
# All detectors and recording leads used for analysis should be used for benchmarking

data_filename ="results/data_det_lead.csv"  
stats_filename ="results/det_lead_stats.csv"


bench_data=pd.read_csv(data_filename, dtype=float, index_col=0)
bench_stats=pd.read_csv(stats_filename, dtype=float, index_col=0)

mapped_params={} # dictionary for parameters once they have been mapped
whiskers_dict={}

err_jitter_einth = []
err_missed_einth = []
err_extra_einth = []
err_jitter_chest = []
err_missed_chest = []
err_extra_chest = []


for record_lead in all_recording_leads: # loop for all chosen leads
    BM_array = [] # Create empty list for that record lead's benchmarks

    detectors = Detectors(250)
    for d in detectors.detector_list:

        detector = detector[1].__name__

        for category in all_categories:
            if category == 'jitter':
                name_end='_mad'
            else:
                name_end='_mean'
            # Now generate all benchmarking values for all parameters
            name=category+'_accum_'+record_lead+'_'+detector+name_end
            name_data=category+'_accum_'+record_lead+'_'+detector # for error bars
            name_val=pd.Series.tolist(bench_stats[name])[0]
            name_val_array=pd.Series.tolist(bench_data[name_data])
            
            mapped_params[name]=normalise_and_map(name_val, category) # for main plot
            
            # For error bars on bar charts
            err_stat=find_err_plus_minus(name_val_array, category) # err_stat is a tuple
            
            whiskers_dict[name_data]=err_stat # unused at present but may be used for saving
            if category =='jitter' and record_lead=='einthoven_ii':
                err_jitter_einth.append(err_stat)
            elif category =='missed'and record_lead=='einthoven_ii':
                err_missed_einth.append(err_stat)
            elif category =='extra'and record_lead=='einthoven_ii':
                err_extra_einth.append(err_stat)
            elif category =='jitter' and record_lead=='chest_strap_V2_V1':
                err_jitter_chest.append(err_stat)
            elif category =='missed'and record_lead=='chest_strap_V2_V1':
                err_missed_chest.append(err_stat)
            elif category =='extra'and record_lead=='chest_strap_V2_V1':
                err_extra_chest.append(err_stat)
    
        detector_overall_BM=overall_benchmark(record_lead, detector, mapped_params)
        BM_array.append(detector_overall_BM)
          
    if record_lead=='einthoven_ii':
        BM_data_einthoven_ii=BM_array
    elif record_lead=='chest_strap_V2_V1':
        BM_data_chest_strap_V2_V1=BM_array
        

BM_einth_jitter, BM_einth_missed, BM_einth_extra = category_benchmarks('einthoven_ii', mapped_params)
BM_chest_jitter, BM_chest_missed, BM_chest_extra = category_benchmarks('chest_strap_V2_V1', mapped_params)      
    
# Now have named variables and values as saved

#%% SET OVERALL PARAMETERS FOR PLOTS:

plt.rcParams['figure.figsize'] = [19.2, 10.8]
plt.rcParams['figure.dpi'] = 100 # Make = 100 for 1920 x 1080 HD video size
plt.rcParams['ytick.labelsize']=15


plt.ion() # enables interactive mode (keep plots visible until closed)

#%% PLOT OF OVERALL BENCHMARKS FOR EINTH AND CHEST

# Add errors (as in multiplication) and transpose array 
err_BM_einth=np.transpose(np.asarray(err_jitter_einth)+np.asarray(err_missed_einth)+np.asarray(err_extra_einth))
err_BM_chest=np.transpose(np.asarray(err_jitter_chest)+np.asarray(err_missed_chest)+np.asarray(err_extra_chest))


fig, ax = plt.subplots()
det_posh_names = ['Elgendi et al', 'Kalidas and Tamil', 'Engzee Mod', 'Christov', 'Hamilton', 'Pan and Tompkins', 'Matched Filter']
# use 'all_detectors'

x_pos = np.arange(len(all_detectors))
y_pos_maj=np.linspace(0,100,11)
y_pos_min=np.linspace(0,100,21)
width = 0.4 # set width of bars
ax.set_yticks(y_pos_maj)
ax.set_yticks(y_pos_min, minor=True)
ax.grid(which="major", axis='y', alpha=0.6, zorder=0)
ax.grid(which="minor", axis='y', alpha=0.2, zorder=0)
#ax.yaxis.grid(which='both', zorder=0) # Plot grid behind bars for clarity
rects1 = ax.bar(x_pos, BM_data_einthoven_ii, width, color='plum', yerr=err_BM_einth, alpha=1.0, zorder=3, capsize=10)
rects2 = ax.bar(x_pos+width, BM_data_chest_strap_V2_V1, width, color='mediumseagreen', yerr=err_BM_chest, alpha=1.0, zorder=3, capsize=10)
ax.set_ylim([0,110.0])
y_label='JMX Benchmark Score'
ax.set_ylabel(y_label, fontsize=18)
ax.set_xlabel('Detector Algorithm', fontsize=18)
ax.set_xticks(x_pos + width / 2)
ax.set_xticklabels(det_posh_names, fontsize=15)
legend1='Einthoven II leads'
legend2='Chest strap leads'
ax.legend((rects1[0], rects2[0]), (legend1, legend2), loc='upper right', fontsize=15)
ax.set_title('Overall JMX Benchmark Score for Einthoven II and Chest Strap Leads', fontsize=20)

plt.tight_layout()

#Add values to the top of bars
# autolabel(rects1)
# autolabel(rects2)

#%% PLOTS OF ALL 3 FACTORS - EINTHOVEN

fig, ax = plt.subplots()

x_pos = np.arange(len(all_detectors))
y_pos_maj=np.linspace(0,100,11)
y_pos_min=np.linspace(0,100,21)

width = 0.25 # set width of bars
ax.set_yticks(y_pos_maj)
ax.set_yticks(y_pos_min, minor=True)
ax.grid(which="major", axis='y', alpha=0.6, zorder=0)
ax.grid(which="minor", axis='y', alpha=0.2, zorder=0)
# rects1 = ax.bar(x_pos-width, BM_einth_jitter, width, yerr=np.transpose(err_jitter_einth), alpha=1.0, zorder=3, capsize=10)
# rects2 = ax.bar(x_pos, BM_einth_missed, width, yerr=np.transpose(err_missed_einth), alpha=1.0, zorder=3, capsize=10)
# rects3 = ax.bar(x_pos+width, BM_einth_extra, width, yerr=np.transpose(err_extra_einth), alpha=1.0, zorder=3, capsize=10)
rects1 = ax.bar(x_pos-width, BM_einth_jitter, width, color='lightslategrey', yerr=np.transpose(err_jitter_einth), alpha=1.0, zorder=3, capsize=10)
rects2 = ax.bar(x_pos, BM_einth_missed, width, color='lightsalmon', yerr=np.transpose(err_missed_einth), alpha=1.0, zorder=3, capsize=10)
rects3 = ax.bar(x_pos+width, BM_einth_extra, width, color='mediumaquamarine',yerr=np.transpose(err_extra_einth), alpha=1.0, zorder=3, capsize=10)

ax.set_ylim([0,115.0])
y_label='JMX Benchmark Score'
ax.set_ylabel(y_label, fontsize=18)
ax.set_xlabel('Detector Algorithm', fontsize=18)
ax.set_xticks(x_pos)
ax.set_xticklabels(det_posh_names, fontsize=15)
legend1='MAD of temporal jitter'
legend2='Missed heartbeats'
legend3='Extra detections'
ax.legend((rects1[0], rects2[0], rects3[0]), (legend1, legend2, legend3), loc='upper right', fontsize=15)
ax.set_title('Breakdown of JMX Benchmark Score for Einthoven II Leads', fontsize=20)
 
plt.tight_layout()

#Add values to the top of bars
# autolabel(rects1)
# autolabel(rects2) 
# autolabel(rects3)  

            
#%% PLOTS OF ALL 3 FACTORS - CHEST

fig, ax = plt.subplots()

x_pos = np.arange(len(all_detectors))
y_pos_maj=np.linspace(0,100,11)
y_pos_min=np.linspace(0,100,21)

width = 0.25 # set width of bars
ax.set_yticks(y_pos_maj)
ax.set_yticks(y_pos_min, minor=True)
ax.grid(which="major", axis='y', alpha=0.6, zorder=0)
ax.grid(which="minor", axis='y', alpha=0.2, zorder=0)
rects1 = ax.bar(x_pos-width, BM_chest_jitter, width, color='lightslategrey', yerr=np.transpose(err_jitter_chest), alpha=1.0, zorder=3, capsize=10)
rects2 = ax.bar(x_pos, BM_chest_missed, width, color='lightsalmon', yerr=np.transpose(err_missed_chest), alpha=1.0, zorder=3, capsize=10)
rects3 = ax.bar(x_pos+width, BM_chest_extra, width, color='mediumaquamarine', yerr=np.transpose(err_extra_chest), alpha=1.0, zorder=3, capsize=10)

ax.set_ylim([0,115.0])
y_label='JMX Benchmark Score'
ax.set_ylabel(y_label, fontsize=18)
ax.set_xlabel('Detector Algorithm', fontsize=18)
ax.set_xticks(x_pos)
ax.set_xticklabels(det_posh_names, fontsize=15)
legend1='MAD of temporal jitter'
legend2='Missed heartbeats'
legend3='Extra detections'
ax.legend((rects1[0], rects2[0], rects3[0]), (legend1, legend2, legend3), loc='upper right', fontsize=15)
ax.set_title('Breakdown of JMX Benchmark Score for Chest Strap Leads', fontsize=20)

plt.tight_layout()

# Add values to the top of bars
# autolabel(rects1)
# autolabel(rects2) 
# autolabel(rects3)        

plt.ioff()
plt.show()
            
       
