import pickle
import gzip
import os
import pandas as pd
import numpy as np
import geodatasets
import pickle
import shutil
import sys
import matplotlib.pyplot as plt
import geopandas as gpd
from sklearn.cluster import KMeans
from shapely.geometry import Point, MultiPoint

def plot_clusters_and_save(clusters, filepath):
    # Load world map
    world = gpd.read_file(geodatasets.get_path('naturalearth.land'))

    # Plot
    fig, ax = plt.subplots(figsize=(15, 10))
    world.plot(ax=ax, color='lightgrey', edgecolor='white')

    # Plot convex hulls and centers
    for cluster in clusters:
        gpd.GeoSeries([cluster['convex_hull']], crs="EPSG:4326").plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1.5)
        center = cluster['center']
        ax.plot(center[0], center[1], 'kx', markersize=12, markeredgewidth=3)
        ax.text(center[0] + 2, center[1] + 4, f"{cluster['id']}", fontsize=15, ha='right', color='black')

    plt.title('Clustered Coordinates with Convex Hulls on World Map')
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filepath + "/cluster_convex_hulls.png", dpi=300)

def main():

    print("Hello World!")
    full_name = sys.argv[1]
    print(f"You passed: {full_name}")
    dir_name = full_name[:-7]

    with gzip.open(full_name, 'rb') as f:
        dataset_sample = pickle.load(f)

    if os.path.exists(dir_name): # Delete if the directory alread exists
        shutil.rmtree(dir_name)
    os.makedirs(dir_name, exist_ok=True) # Create a new directory (and any necessary parent directories)

    dataset_sample['receive_reports'].to_csv(dir_name + "/wsjtx_reports.csv", index=False)

    dataset_sample['transmission_reports']['reception_reports'].to_csv(dir_name + "/psk_reception_reports.csv", index=False)

    dataset_sample['transmission_reports']['active_cs'].to_csv(dir_name + "/psk_active_cs.csv", index=False)

    plot_clusters_and_save(dataset_sample['transmission_reports']['activer_receivers'], dir_name)

    with open(dir_name + '/last_report_time.txt', 'w') as output:
        output.write(str(dataset_sample['transmission_reports']['last_report_time']))

    return 0

if __name__ == '__main__':

    main()

