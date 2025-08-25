# -*- coding: utf-8 -*-
"""
Created on Wed Aug 20 10:08:35 2025

@author: haley.synan
"""

import os
import warnings
#from urllib.error import HTTPError
#import urllib
import ctd
#import numpy as np
import pandas as pd
#import matplotlib.pyplot as plt
from seabird.cnv import fCNV
import urllib.request
#import cartopy

import hvplot.xarray  # needed for features
import hvplot
import geoviews as gv
from geoviews import feature as gf
import panel as pn 
from datetime import datetime
warnings.filterwarnings('ignore', category=SyntaxWarning)
warnings.filterwarnings('ignore', category=UserWarning)

data_dir = r'C:\Users\haley.synan\Documents\DATA\NRT_DATA'


cruise_name = 'PC2503'
a = os.popen('gsutil ls -l gs://nmfs_odp_nefsc/NEFSC_CTD_Program_near_real_time_data/'+cruise_name+'/*.cnv').read().split('\n')
aa = [s[12:].split('  ')[0].split('T')[0] for s in a]
aa= aa[:-2] #remove last 2 strings in list (they are metadata, not valid dates)
d8 = [datetime.strptime(date, "%Y-%m-%d").date() for date in aa]

idx= [i for i, element in enumerate(d8)] #get indices for dates to plot
t = [s[12:].split('  ') for s in a] #split date/paths into nested list of strings
paths = [sublist[1:] for sublist in t] #get file paths only (remove dates)
fnames=[]
for x in range(len(idx)):
    fnames.append(paths[idx[x]]) #get new files to plot using indices of new dates
    
#fnames = !gsutil ls gs://nmfs_odp_nefsc/NEFSC_CTD_Program_near_real_time_data/PC2503/*.cnv 
#list all files
#fnames=fnames.list #turn into list
#folds=!gsutil ls gs://nmfs_odp_nefsc/NEFSC_CTD_Program_near_real_time_data
#folds = folds[2:-1]
#cruise_name = folds[-2].split('/')[4] #get most recent cruise name
#files = [s for s in fnames if cruise_name in s] #sort by cruise name


#DATA DOWNLOAD AND PREPROCESS
casts=[]
counter=1
lats=[]
lons=[]
count=[]
d8 = []
for x in range(len(fnames)):
    data_dir_fold = data_dir+'\\'+cruise_name
    if fnames[x][0].split('/')[5] == 'ctd999.cnv':
        pass
    else: 
        file = data_dir_fold+'\\'+fnames[x][0].split('/')[5]
        urllib.request.urlretrieve('https://storage.googleapis.com/'+fnames[x][0].split('//')[1],file)
        down, up = ctd.from_cnv(file).split()
        cast = up.reset_index().rename(columns={"Pressure [dbar]": "pres"})
        cast= cast[cast.pres>0.5] #remove negative pressures
        file = fCNV(file)
        lat = file.attributes['LATITUDE']
        lats.append(lat)
        lon = file.attributes['LONGITUDE']
        lons.append(lon)
        date = file.attributes['gps_datetime']
        d8.append(date)
        try: #check if sbe or ctd profile 
            cast.t090C
            cast = cast.rename(columns={"t090C": "temp"})
            supname = 'CTD Cast '+fnames[x][0].split('d')[3].split('.')[0]+'\n'+file.attributes['gps_datetime']
        except AttributeError:
            cast.tv290C
            cast = cast.rename(columns={"tv290C": "temp"})
            supname = 'SBE Cast '+fnames[x][0].split('e')[5].split('.')[0]+'\n'+file.attributes['gps_datetime']
        cast = cast.rename(columns={"sal00": "sal"})
        count.append(counter)
        cast['lat'] = [lat]*len(cast)
        cast['lon'] = [lon]*len(cast)
        cast['profnum'] = [counter]*len(cast)
        cast['date'] = [date]*len(cast)
        casts.append(cast)
    counter=counter+1
df = pd.concat(casts)
stations_df = pd.DataFrame({'lat':lats,'lon':lons,'profnum':count,'date':d8})
#cruiseid = fnames[0].split('/')[4]

df['temp'] = pd.to_numeric(df['temp'])
df['sal'] = pd.to_numeric(df['sal'])

stations_df['date'] = [datetime.strptime(d, '%b %d %Y %H:%M:%S').strftime("%m-%d") for d in stations_df.date]

import hvplot.pandas
import holoviews as hv
from holoviews.streams import Selection1D

hv.extension('bokeh')

station_plot = stations_df.hvplot.points(
    'lon', 'lat',
    geo=True,
    color='date',
    cmap='Category10',
    projection='EPSG:4326',
    hover_cols=['profnum'],
    size=60,
    tools=['tap'],
    title=cruise_name+ ' stations'
)

gv.extension('bokeh')


coastline = gf.coastline(scale='10m').opts(line_color='black')
land = gf.land(scale='10m').opts(fill_color='lightgray')
map_with_features = land * coastline * station_plot
station_plot = map_with_features.opts(
    xlim=(-77, -63), ylim=(35, 46)  # adjust to your region
)

import cmocean as cm
selection = Selection1D(source=station_plot)
#selected_station=[]
#profile_data = []
def sal_plot(index):
    if not index or index[0] >= len(stations_df):
        return hv.Scatter([]).opts(title="Select a station", height=300,ylim=(0,100),xlim= (25,37), invert_yaxis=True)
    selected_station = stations_df.iloc[index[0]]['profnum']
    profile_data = df[df['profnum'] == selected_station]
    return hv.Scatter(profile_data, kdims='sal', vdims='pres').opts(invert_yaxis=True, cmap=cm.cm.haline,color='sal',
                                                                    title = 'Salinity profile', size=3, marker='circle',
                                                                    xlim=(profile_data.sal.min()-0.5, profile_data.sal.max()+0.5),
                                                                    ylim= (profile_data.pres.min()-5, profile_data.pres.max()+5),
                                                                    colorbar=True,
                                                                    tools=['hover'])
sal_dmap = hv.DynamicMap(sal_plot,streams=[selection])

def temp_plot(index):
    if not index or index[0] >= len(stations_df):
        return hv.Scatter([]).opts(title="Select a station", height=300, ylim=(0,100),xlim= (0,25), invert_yaxis=True)
    selected_station = stations_df.iloc[index[0]]['profnum']
    profile_data = df[df['profnum'] == selected_station]
    return hv.Scatter(profile_data, kdims=['temp'], vdims=['pres']).opts(invert_yaxis=True, cmap=cm.cm.thermal,color='temp',
                                                                          ylim= (0,200),
                                                                          title = 'Station '+ str(profile_data.profnum.iloc[0]).split('.')[0]+': Temperature profile', size=3,  marker='circle',
                                                                          xlim=(profile_data.temp.min()-2, profile_data.temp.max()+2),
                                                                          colorbar=True,tools=['hover']
                                                                          )
                                                                    
temp_dmap = hv.DynamicMap(temp_plot,streams=[selection])


def stats(index):
    if not index or index[0] >= len(stations_df):
        return hv.Text(0.45, 0.7, "Tap a profile")
    selected_station = stations_df.iloc[index[0]]['profnum']
    profile_data = df[df['profnum'] == selected_station]
    return hv.Text(0.45,0.7, f'STATION {str(profile_data.profnum.iloc[0]).split('.')[0]} \n max depth: {str(profile_data.pres.max())} \n min temp: {str(profile_data.temp.min())} \n max temp: {str(profile_data.temp.max())}\n min sal: {str(profile_data.sal.min())} \n max sal: {str(profile_data.sal.max())}').opts(height=300,width = 100,)

dmap = hv.DynamicMap(stats, streams=[selection]).opts(show_frame=False,
    xaxis=None,
    yaxis=None,)


layout = station_plot +temp_dmap+sal_dmap+dmap
layout.opts(shared_axes=False)

title = pn.pane.Markdown("# Near Real Time CTD dashboard \n Data is collected by the NOAA Fisheries Oceanography Branch \n Disclaimer: Data is preliminary and has not been processed yet. You can find processed data on ERDDAP.", )


pn.extension()
# Combine title and layout
app = pn.Column(title, layout)
app.servable()
