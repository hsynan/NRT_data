# -*- coding: utf-8 -*-
"""
Created on Fri Sep 19 13:00:10 2025

@author: haley.synan
"""

import pandas as pd
import os
import numpy as np
import geopandas as gpd
from NESCAPES_func_model import * 


data = pd.read_csv(os.path.join(r'W:\nadata\PROJECTS\NESCAPES\PROCESSED_DATA','final','formatted_equigrid_all_finer.csv'))
#data = data[data.latitude<44.85]
shp = gpd.read_file(r'C:\Users\haley.synan\Documents\DATA\SHAPEFILES\Estuary_CyAN_4_8_2019\Atlantic_estuary_shore_dist.shp').to_crs("EPSG:4326") #load coastlines shapefile
data = buffer_clip(data,shp,0.2) #create 0.2 buffer from coastlines and clip data
data = log_chla(data) #log10 chlorophyll
monthly = True
formatted = get_vars(data,monthly=monthly) #format data (into monthly as rows, if necessary)
data = formatted[0] #format data (monthly or not)
if monthly == False:
    clustering_vars = ['CT','SA','rho']
else:
    clustering_vars = formatted[1] # get variables to train on (monthly or not)
dataa = normalize(data, clustering_vars,monthly=monthly)[0] #normalize data 
scaler = normalize(data, clustering_vars,monthly=monthly)[1] #output scaler to save later

sm = train_som(dataa, clustering_vars,msz=[50,50],rough_len=1000, fine_len =300) #train model
print ("Topographic error = %s; Quantization error = %s" % (sm.calculate_topographic_error(), sm.calculate_quantization_error())) #get errors from model

nodes = sm.codebook.matrix #get node centers
bmu = sm._bmu #get bmus
clustering = linkage(nodes, method="ward", metric="euclidean") #HAC clustering
#plots to help decide optimal num clusters 
plt_wss(clustering) #within cluster sum of squares
plt_dendro(clustering) #dendrogram

#CHOOSE NUMBER OF CUSTERS
#data = data.reset_index()
import cartopy
n_clusters = 12
cm = plt.get_cmap('jet', n_clusters) #choose colorbar
cluster_labels = cut_tree(clustering, n_clusters=n_clusters).reshape(-1, ) #cut dendrogram at desired cluster num

res = get_clus_labels(data, clustering_vars, bmu, cluster_labels) #apply HAC clusters to original data
if monthly==False:
    res['month'] = data.month.reset_index().month #add month to result dataframe
else:
    pass
plot_map(res, n_clusters, monthly=monthly) #plot maps

#run validity tests
print('The silhouette score is ' + str(validity_tests(nodes, cluster_labels)[0]))
print('The Calinski Harabasz Index is ' + str(validity_tests(nodes, cluster_labels)[1]))
print('The Davies Bouldin score is ' + str(validity_tests(nodes, cluster_labels)[2]))

#summary_stats(res) #get summary statistics 

save_model(nodes,res,clustering_vars,sm,data, scaler) #pickle dump to save model 