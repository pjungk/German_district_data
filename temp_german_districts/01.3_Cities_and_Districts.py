#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Oct  3 17:29:01 2024

@author: pjungk
"""

import geopandas as gpd
import matplotlib.pyplot as plt
import os
import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib.parse

abs_path = os.getcwd()

# Define the replacements for URL encoding
replacements = {
    '%C3%A4': 'ä',
    '%C3%B6': 'ö',
    '%C3%BC': 'ü',
    '%C3%9F': 'ß',
    '%28': '(',   # (
    '%29': ')',   # )
    '%20': ' '    # Space
}

state_map = {
    "NW": "Nordrhein-Westfalen",
    "RP": "Rheinland-Pfalz",
    "BY": "Bayern",
    "BW": "Baden-Württemberg",
    "TH": "Thüringen",
    "ST": "Sachsen-Anhalt",
    "NI": "Niedersachsen",
    "BB": "Brandenburg",
    "SN": "Sachsen",
    "HE": "Hessen",
    "SH": "Schleswig-Holstein",
    "MV": "Mecklenburg-Vorpommern",
    "SL": "Saarland",
    "BE": "Berlin",
    "HB": "Bremen",
    "HH": "Hamburg"
}

shp_district_name_maps = {
    "Neustadt a.d.Aisch-Bad Windsheim": "Neustadt an der Aisch-Bad Windsheim",
    "Saarbrücken, Regionalverband": "Regionalverband Saarbrücken",
    "Wunsiedel i.Fichtelgebirge": "Wunsiedel im Fichtelgebirge",
    "Nienburg (Weser)": "Nienburg-Weser",
    "Aachen, Städteregion": "Städteregion Aachen",
    "Mühldorf a.Inn": "Mühldorf am Inn",
    "Neumarkt i.d.OPf.": "Neumarkt in der Oberpfalz",
    "Hannover, Region": "Region Hannover",
    "Pfaffenhofen a.d.Ilm": "Pfaffenhofen an der Ilm",
    "Dillingen a.d.Donau": "Dillingen an der Donau",
    "Neustadt a.d.Waldnaab": "Neustadt an der Waldnaab",
    "Oldenburg (Oldb)": "Oldenburg",
    "Weiden i.d.OPf.": "Weiden in der Oberpfalz",
    }

wiki_district_name_maps = {
    "Mülheim": "Mülheim an der Ruhr",
    "Offenbach": "Offenbach am Main",
    "Frankenthal": "Frankenthal (Pfalz)",
    "Landau": "Landau in der Pfalz",
    "Ludwigshafen": "Ludwigshafen am Rhein",
    "Neustadt": "Neustadt an der Weinstraße",
    "Freiburg": "Freiburg im Breisgau",
    "Kempten": "Kempten (Allgäu)",
    "Brandenburg": "Brandenburg an der Havel",
    "Halle": "Halle (Saale)",
    "Weiden": "Weiden in der Oberpfalz"
    }




# Helper function to convert thumbnail to full image URL
def get_full_image_url(thumb_url):
    if "/thumb/" in thumb_url:
        parts = thumb_url.split("/thumb/")
        full_url = "https:" + parts[0] + "/" + parts[1].split('.svg/')[0] + ".svg"
        if ".png" in full_url:
            full_url = full_url.split('.png/')[0] + ".png"
    else:
        full_url = "https:" + thumb_url
    return full_url

# Function to clean up the image name
def clean_image_name(img_name):
    decoded_name = urllib.parse.unquote(img_name)
    for encoded, replacement in replacements.items():
        decoded_name = decoded_name.replace(encoded, replacement)
    return decoded_name




district_url = "https://de.wikipedia.org/wiki/Liste_der_Landkreise_in_Deutschland"

### Download and format DISTRICT data from Wikipedia
response = requests.get(district_url)
soup = BeautifulSoup(response.text, 'html.parser')

tables = pd.read_html(response.text)
df_districts = tables[0]

image_tags = soup.select('table img')
x = len(image_tags)
downloaded_images = 0

image_url_wappen = []
image_url_flag = []

# Download and clean image paths
for img in image_tags:
    if downloaded_images >= x:
        break

    if downloaded_images % 3 == 2:
        downloaded_images += 1
        continue

    img_url = get_full_image_url(img['src'])

    if downloaded_images % 3 == 0:
        image_url_wappen.append(img_url)
    elif downloaded_images % 3 == 1:
        image_url_flag.append(img_url)

    downloaded_images += 1




df_districts = df_districts.set_axis(['District_ID', 'District', 'COA', 'License_Plate_ID', 'State', 'District_Seat', 'Population',
                                                  'Area_in_km²', 'Population_density_in_1/km²', 'Map'], axis=1)

df_districts["District"] = df_districts["District"].str.replace("[FN 1]", "")
df_districts["District"] = df_districts["District"].apply(lambda x: f"{x.split(', ')[1]} {x.split(', ')[0]}" if ', ' in x else x)
df_districts.replace('Nienburg/Weser', 'Nienburg-Weser', inplace=True)

df_districts["State"] = df_districts['State'].map(state_map)

df_districts["Map"] = df_districts["District"].apply(lambda x: f'<img src=DistrictMap_{x.replace(" ", "_")}.png>')

df_districts['Area_in_km²'] = df_districts['Area_in_km²'].astype(str).str.replace(r"(\d{4,})$", lambda x: x.group(1)[:-2] + ',' + x.group(1)[-2:], regex=True)
df_districts['Area_in_km²'] = df_districts['Area_in_km²'].str.replace('.', ' ').apply(lambda x: x.split(',', 1)[0])
df_districts['Population'] = df_districts['Population'].str.replace('.', ' ')



df_districts["url_COA"] = image_url_wappen
df_districts["Save_paths_COA"] = df_districts["District"].apply(lambda x: f'images/COA_{x.replace(" ", "_")}.svg')
df_districts["COA"] = df_districts["District"].apply(lambda x: f'<img src=COA_{x.replace(" ", "_")}.svg>')

df_districts["url_StateFlag"] = image_url_flag
df_districts["Save_paths_StateFlag"] = df_districts["State"].apply(lambda x: f'images/StateFlag_{x.replace(" ", "_")}.svg')
df_districts.insert(5, 'State_Flag', df_districts["State"].apply(lambda x: f'<img src=StateFlag_{x.replace(" ", "_")}.svg>'))

# Download and clean image paths
for i in range(df_districts.shape[0]):
    
    img_path = df_districts.loc[i, "Save_paths_COA"]
    if not os.path.exists(img_path):
        img_url = df_districts.loc[i, "url_COA"]
        
        img_data = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data.raise_for_status()
        
        with open(img_path, 'wb') as handler:
            handler.write(img_data.content)
        print(f"Downloaded: {img_path}")
    else:
        print(f"File already exists: {img_path}")
            
        
    img_path = df_districts.loc[i, "Save_paths_StateFlag"]
    if not os.path.exists(img_path):
        img_url = df_districts.loc[i, "url_StateFlag"]
        img_data = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data.raise_for_status()
        
        with open(img_path, 'wb') as handler:
            handler.write(img_data.content)
        print(f"Downloaded: {img_path}")
    else:
        print(f"File already exists: {img_path}")






city_url = "https://de.wikipedia.org/wiki/Liste_der_kreisfreien_St%C3%A4dte_in_Deutschland"

### Download and format CITY data from Wikipedia
response = requests.get(city_url)
soup = BeautifulSoup(response.text, 'html.parser')

tables = pd.read_html(response.text)
df_cities = tables[1]

image_tags = soup.select('table img')
x = len(image_tags)
downloaded_images = 0

image_url_wappen = []
image_url_flag = []

# Download and clean image paths
for img in image_tags:
    if downloaded_images >= x:
        break

    if downloaded_images % 3 == 2:
        downloaded_images += 1
        continue

    img_url = get_full_image_url(img['src'])

    if downloaded_images % 3 == 0:
        image_url_wappen.append(img_url)
    elif downloaded_images % 3 == 1:
        image_url_flag.append(img_url)

    downloaded_images += 1


# Format dataframe
df_cities = df_cities.iloc[:, [0,1,2,3,4,5,6,12,13]]
df_cities = df_cities.set_axis(['COA', 'District', 'District_ID', 'State', 'Admin_district', 'License_Plate_ID', 'Area_in_km²', 'Population',
                        'Population_density_in_1/km²'], axis=1)

df_cities["State"] = df_cities['State'].map(state_map)
df_cities["State"][8] = "Berlin"

df_cities["District"] = [substr.split("[")[0] for substr in df_cities["District"]]
df_cities["District"] = [substr.split(" ")[0] for substr in df_cities["District"]]
df_cities["District"] = df_cities["District"].apply(lambda x: f"{x.split(', ')[1]} {x.split(', ')[0]}" if ', ' in x else x)
df_cities.replace('Nienburg/Weser', 'Nienburg-Weser', inplace=True)

df_cities["Map"] = df_cities["District"].apply(lambda x: f'<img src=DistrictMap_{x.replace(" ", "_")}.png>')

df_cities['Population'] = df_cities['Population'].astype(str).apply(lambda x: x.split(' ', 1)[0].replace('.', ' '))
df_cities['Area_in_km²'] = df_cities['Area_in_km²'].astype(str).apply(lambda x: x[:-2])




df_cities["url_COA"] = image_url_wappen
df_cities["Save_paths_COA"] = df_cities["District"].apply(lambda x: f'images/COA_{x.replace(" ", "_")}.svg')
df_cities["COA"] = df_cities["District"].apply(lambda x: f'<img src=COA_{x.replace(" ", "_")}.svg>')

df_cities["url_StateCOA"] = image_url_flag
df_cities["Save_paths_StateCOA"] = df_cities["State"].apply(lambda x: f'images/StateCOA_{x}.svg')
df_cities.insert(4, 'State_COA', df_cities["State"].apply(lambda x: f'<img src=StateCOA_{x}.svg>'))


# Download images
for i in range(df_cities.shape[0]):
    
    img_path = df_cities.loc[i, "Save_paths_COA"]
    if not os.path.exists(img_path):
        img_url = df_cities.loc[i, "url_COA"]
        
        img_data = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data.raise_for_status()
        
        with open(img_path, 'wb') as handler:
            handler.write(img_data.content)
        print(f"Downloaded: {img_path}")
    else:
        print(f"File already exists: {img_path}")
            
        
    img_path = df_cities.loc[i, "Save_paths_StateCOA"]
    if not os.path.exists(img_path):
        img_url = df_cities.loc[i, "url_StateCOA"]
        img_data = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'})
        img_data.raise_for_status()
        
        with open(img_path, 'wb') as handler:
            handler.write(img_data.content)
        print(f"Downloaded: {img_path}")
    else:
        print(f"File already exists: {img_path}")











# =============================================================================
# https://gdz.bkg.bund.de/index.php/default/digitale-geodaten/verwaltungsgebiete/verwaltungsgebiete-1-250-000-stand-01-01-vg250-01-01.html
# (Stand: 01.01., Georeferenzierung: UTM32s, Format: shape Inhalt: Ebenen (ZIP, 67 MB))
# =============================================================================

raw_district_shp = gpd.read_file("data/VG250_KRS.SHP")
raw_district_shp = raw_district_shp[raw_district_shp["GF"] == 4]

fig, ax = plt.subplots(figsize=(10, 10))
raw_district_shp.plot(ax=ax, color='lightblue', edgecolor='black')
ax.set_axis_off()
plt.savefig("images/blank_districts_map.png", format="png", dpi=150, bbox_inches='tight', pad_inches=0)
plt.show()
plt.close(fig)



df_shapes = raw_district_shp.iloc[:, [8,9,25]]
df_shapes["GEN"] = df_shapes["GEN"].replace(shp_district_name_maps)
df_shapes["Type"] = df_shapes["BEZ"].apply(lambda x: "Stadt" if (x == "Kreisfreie Stadt" or x == "Stadtkreis") else "Kreis")
df_shapes["District"] = df_shapes["GEN"].where(~df_shapes["GEN"].isin(df_shapes["GEN"][df_shapes["GEN"].duplicated(keep=False)]),
                                               df_shapes["GEN"] + df_shapes["Type"].map({"Kreis": " (Kreis)", "Stadt": " (Stadt)"}))



df_districts["State_COA"] = df_districts["State"].apply(lambda x: f'<img src=StateCOA_{x}.svg>')
df_districts_ordered = df_districts.iloc[:, [0,1,2,3,4,5,15,7,8,9,10]]

df_cities = df_cities[~df_cities["District_ID"].isin(set(df_districts["District_ID"]).intersection(set(df_cities["District_ID"])))]
df_cities.loc[(df_cities["District"] == "Frankfurt") & (df_cities["State"] == "Hessen"), "District"] = "Frankfurt am Main"
df_cities.loc[(df_cities["District"] == "Frankfurt") & (df_cities["State"] == "Brandenburg"), "District"] = "Frankfurt (Oder)"
df_cities["District"] = df_cities["District"].replace(wiki_district_name_maps)
df_cities["State_Flag"] = df_cities["State"].apply(lambda x: f'<img src=StateFlag_{x.replace(" ", "_")}.svg>')
df_cities_ordered = df_cities[df_districts_ordered.columns]


duplicated_districts_combined = df_districts_ordered["District"][df_districts_ordered["District"].isin(df_cities_ordered["District"])]
df_districts_ordered.loc[df_districts_ordered["District"].isin(duplicated_districts_combined), "District"] += " (Kreis)"
df_cities_ordered.loc[df_cities_ordered["District"].isin(duplicated_districts_combined), "District"] += " (Stadt)"

df_combined = pd.concat([df_districts_ordered, df_cities_ordered], ignore_index=True)


# df_combined["District_and_type"][~df_combined["District_and_type"].isin(df_shapes["District_and_type"])]
# df_shapes["District_and_type"][~df_shapes["District_and_type"].isin(df_combined["District_and_type"])]


merged = pd.merge(df_combined, df_shapes, on="District", how="left")
merged["Save_paths_Map"] = merged["District"].apply(lambda x: f'images/DistrictMap_{x.replace(" ", "_")}.png')
merged = gpd.GeoDataFrame(merged)

# merged.isnull().values.any()

merged["Map"] = merged["District"].apply(lambda x: f'<img src=DistrictMap_{x.replace(" ", "_")}.png>')


for i in range(merged.shape[0]):

    if os.path.isfile(merged.loc[i, "Save_paths_Map"]):
        print(f"File already exists: {merged.loc[i, 'Save_paths_Map']}")
        continue
    else:
        print(f"Generating: {merged.loc[i, 'Save_paths_Map']}")
    
    fig, ax = plt.subplots(figsize=(10, 10))
    raw_district_shp.plot(ax=ax, color='lightblue', edgecolor='black')
    merged.iloc[[i]].plot(ax=ax, color='blue', edgecolor='red')
    
    ax.set_axis_off()
    plt.savefig(merged.loc[i, "Save_paths_Map"], format="png", dpi=150, bbox_inches='tight', pad_inches=0)
    
    plt.show()
    plt.close(fig)


merged["Blank_districts"] = "<img src=blank_districts_map.png>"



merged = merged.iloc[:, [0,1,2,3,4,5,6,7,8,9,10,16]]
merged.to_csv('11.3_Cities_and_Districts.csv', index=False)










