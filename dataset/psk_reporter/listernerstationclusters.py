import pandas as pd
import numpy as np
import geodatasets
import pickle
import matplotlib.pyplot as plt
import geopandas as gpd
from maidenhead_converter import maidenhead_to_gcs
from sklearn.cluster import KMeans
from shapely.geometry import Point, MultiPoint

class ListenerStationClusters:
    def __init__(self, df, k=11):
        # Saving the number of clusters
        self.k = k
        self.clusters_params = []

        # Remove invalid locators of the dataset
        df[['valid_coord', 'coord_y', 'coord_x']] = df['locator'].apply(lambda x: pd.Series(maidenhead_to_gcs(x)))
        # Delete a sample if it is not a valid_coord
        df.drop(df[df['valid_coord'] == -1].index, inplace=True)

        # Clustering
        self.kmeans = KMeans(n_clusters=k, max_iter=10000, tol=1e-4, random_state=0, algorithm='elkan')
        df['cluster'] = self.kmeans.fit_predict(df[['coord_x', 'coord_y']])
        self.centers = self.kmeans.cluster_centers_

        # Calculating the inertia, density and convex hull for each point
        for i in range(self.k):
            cluster = {}

            cluster_points = df[df['cluster'] == i][['coord_x', 'coord_y']].values
            cluster['id'] = i
            cluster['inertia'] = np.sum((cluster_points - self.centers[i]) ** 2)/(len(cluster_points))
            cluster['density'] = len(cluster_points)
            cluster['center'] = self.centers[i]

            cluster['convex_hull'] = MultiPoint(cluster_points).convex_hull
            self.clusters_params.append(cluster)

    @property
    def cluster_params(self):
        return self.clusters_params

    def save_to_pklgz(self, name=""):
        with gzip.open(name + '_clusters.pkl.gz', 'wb') as f:
            pickle.dump(self.clusters_params, f)

    def read_pklgz(self, name=""):
        with gzip.open(name + '_clusters.pkl.gz', 'rb') as f:
            return pickle.load(f)

    # Method to compare cluster integrity after serialization and compression
    def debug_compare_clusters(self, a, b):
        if len(a) != len(b):
            return False
        for d1, d2 in zip(a, b):
            if d1.keys() != d2.keys():
                return False
            for key in d1:
                v1, v2 = d1[key], d2[key]
                if isinstance(v1, np.ndarray) and isinstance(v2, np.ndarray):
                    if not np.array_equal(v1, v2):
                        return False
                else:
                    if v1 != v2:
                        return False
        return True

    def plot_clusters_points_and_convex_hull(self, df):
        # Convert to GeoDataFrame
        geometry = [Point(xy) for xy in zip(df['coord_x'], df['coord_y'])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

        # Load world map using geodatasets
        world = gpd.read_file(geodatasets.get_path('naturalearth.land'))

        # Plot
        fig, ax = plt.subplots(figsize=(15, 10))
        world.plot(ax=ax, color='lightgrey', edgecolor='white')

        # Plot points by cluster with color mapping
        gdf.plot(ax=ax, column='cluster', cmap='tab10', legend=True, markersize=10, alpha=0.7)

        # Plot convex hulls for each cluster
        for cluster_id in gdf['cluster'].unique():
            cluster_points = gdf[gdf['cluster'] == cluster_id]
            if len(cluster_points) >= 3:  # Convex hull requires at least 3 points
                hull = self.clusters_params[cluster_id]['convex_hull']
                gpd.GeoSeries([hull], crs="EPSG:4326").plot(ax=ax, facecolor='none', edgecolor='black', linewidth=1.5)

        # Plot cluster centers
        for i, center in enumerate(self.centers):
            ax.plot(center[0], center[1], 'kx', markersize=12, markeredgewidth=3)
            ax.text(center[0] + 2, center[1] + 4, f'{i}', fontsize=15, ha='right', color='black')

        plt.title('Clustered Coordinates with Convex Hulls on World Map')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

        # Display results
        for cluster in self.clusters_params:
            print(cluster)

