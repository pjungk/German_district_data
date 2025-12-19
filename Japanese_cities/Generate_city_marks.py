import re
import geopandas as gpd
import matplotlib.pyplot as plt
from geopy.geocoders import Nominatim
from shapely.geometry import Point
import time
import pandas as pd
import json
import os
from typing import Optional

### Startup actions. Create folders, load shapefiles, define prefecture variables and mapping
output_folder = 'img'
os.makedirs(output_folder, exist_ok=True)

japan = gpd.read_file('data/ne_10m_admin_0_countries_jpn/ne_10m_admin_0_countries_jpn.shp')
prefectures = gpd.read_file('data/ne_10m_admin_1_states_provinces/ne_10m_admin_1_states_provinces.shp')

japan_prefectures = prefectures[prefectures['admin'] == 'Japan']

region_colors = {
    'Tohoku': '#fffb92',
    'Hokkaido': '#ff8585',
    'Kanto':  '#79ff76',
    'Chubu': '#8bffe8',
    'Kansai': '#7171fe',
    'Chugoku': '#ff923f',
    'Shikoku': '#d16dfe',
    'Kyushu': '#c5c5c5',
    'Okinawa':  '#f0f0f0'
}

region_to_prefectures = {
    'Hokkaido': ['Hokkaidō', 'Hokkaido'],
    'Tohoku': ['Aomori', 'Iwate', 'Miyagi', 'Akita', 'Yamagata', 'Fukushima'],
    'Kanto': ['Ibaraki', 'Tochigi', 'Gunma', 'Saitama', 'Chiba', 'Tōkyō', 'Tokyo', 'Kanagawa'],
    'Chubu':  ['Niigata', 'Toyama', 'Ishikawa', 'Fukui', 'Yamanashi', 'Nagano', 'Gifu', 'Shizuoka', 'Aichi'],
    'Kansai': ['Mie', 'Shiga', 'Kyōto', 'Kyoto', 'Ōsaka', 'Osaka', 'Hyōgo', 'Hyogo', 'Nara', 'Wakayama'],
    'Chugoku': ['Tottori', 'Shimane', 'Okayama', 'Hiroshima', 'Yamaguchi'],
    'Shikoku':  ['Tokushima', 'Kagawa', 'Ehime', 'Kōchi', 'Kochi'],
    'Kyushu': ['Fukuoka', 'Saga', 'Nagasaki', 'Kumamoto', 'Ōita', 'Oita', 'Miyazaki', 'Kagoshima'],
    'Okinawa':  ['Okinawa'],
}

prefecture_to_region = {}
for region, prefs in region_to_prefectures.items():
    for pref in prefs:
        prefecture_to_region[pref] = region
japan_prefectures['region'] = japan_prefectures['name'].map(prefecture_to_region)

### Read and clean city data from Anki export
anki_file = 'Japanese cities.txt'

cities_df = pd.read_csv(
    anki_file,
    sep='\t',
    comment='#',
    header=None,
    names=['kanji_raw', 'reading', 'audio_field_raw', 'rank', 'population', 'map_html', 'map_empty_html'],
    dtype=str,
    keep_default_na=False
)

print(f"Found {len(cities_df)} cities in Anki file")

# Helper regex and functions for cleaning fields and initialize new columns
tag_re = re.compile(r'<[^>]+>')
img_src_re = re.compile(r'src\s*=\s*["\']([^\'"]+)["\']', flags=re.IGNORECASE)
sound_re = re.compile(r'\[?sound:([^\]\s]+)\]?')

def strip_html_tags(s: str) -> str:
    if not s:
        return s
    stripped = tag_re.sub('', s)
    return stripped.strip()

def extract_src(html):
    """Extract src attribute from HTML img tag"""
    if not html:
        return None
    s = html.strip().strip('"').strip("'")
    s = s.replace('""', '"')
    m = img_src_re.search(s)
    return m.group(1) if m else None

def extract_reading_from_kanji(kanji_raw):
    """Extract kana reading from brackets in kanji field, e.g., '福山[ふくやま]'"""
    m = re.match(r'^(?P<kanji>.*?)\[(?P<hira>[^\]]+)\]\s*$', kanji_raw)
    if m:
        return m.group('kanji').strip(), m.group('hira').strip()
    fallback = re.search(r'\[([^\]]+)\]', kanji_raw)
    if fallback:
        return kanji_raw.replace(fallback.group(0), '').strip(), fallback.group(1).strip()
    return kanji_raw, None

# Actual cleaning of read fields
cities_df['kanji'] = cities_df['kanji_raw'].apply(lambda x: strip_html_tags(extract_reading_from_kanji(x)[0]))
cities_df['reading'] = cities_df.apply(lambda row: extract_reading_from_kanji(row['kanji_raw'])[1] or row['reading'], axis=1)

cities_df['audio_filename'] = cities_df['audio_field_raw'].apply(
    lambda x: sound_re.search(x).group(1) if sound_re.search(x) else (x.strip() or None)
)

cities_df['map_filename'] = cities_df['map_html'].apply(extract_src)
cities_df['map_empty_filename'] = cities_df['map_empty_html'].apply(extract_src)

cities_df['lat'] = None
cities_df['lon'] = None
cities_df['geocode_query'] = None
cities_df['prefecture'] = None

print("First few cities (cleaned):", cities_df['kanji'].head(8).tolist())

# Define geocoding functions
def geocode_with_fallbacks(key_name:  str, reading: str, geolocator: Nominatim, cache: dict, sleep=True) -> dict:
    """
    Try several geocoding queries to find a city: 
      1) exact kanji (key_name)
      2) reading (hiragana/kana) if provided
      3) kanji + '市'
      4) kanji + '区' (useful for Tokyo wards)
    Cache by key_name so we don't repeat work.
    Returns dict with 'found', 'lat', 'lon', 'query', and 'prefecture'
    """
    if key_name in cache:
        return cache[key_name]

    queries = []
    if key_name and not key_name.endswith('市'):
        queries.append(f"{key_name}市, Japan")
    if key_name: 
        queries.append(f"{key_name}, Japan")
    if reading:
        queries.append(f"{reading}, Japan")
    # common fallbacks
    # Tokyo wards often need '区'
    if key_name and not key_name.endswith('区'):
        queries.append(f"{key_name}区, Tokyo, Japan")

    for q in queries:
        if sleep:
            time.sleep(0.5)
        try: 
            loc = geolocator.geocode(q, addressdetails=True)
            if loc:
                address = loc.raw['address']
                prefecture = address.get('province')
                
                result = {
                    'found':  True, 
                    'lat': loc.latitude, 
                    'lon': loc.longitude, 
                    'query': q,
                    'prefecture': prefecture
                }
                cache[key_name] = result
                return result
        except Exception as e:
            print(f"Geocode error for query '{q}': {e}")

    # failed
    result = {'found': False, 'lat':  None, 'lon': None, 'query': None, 'prefecture': None}
    cache[key_name] = result
    return result

def get_prefecture_from_coordinates(lat:  float, lon: float, prefectures_gdf: gpd.GeoDataFrame) -> Optional[str]:
    """
    Determine which prefecture contains the given coordinates.
    """
    
    # Create a point from the coordinates
    point = Point(lon, lat)
    
    # Check which prefecture contains this point
    for idx, pref in prefectures_gdf.iterrows():
        if pref.geometry.contains(point):
            return pref['name_local']
    
    return None

### Geocode all cities with caching
print("\n=== Geocoding cities ===")
geolocator = Nominatim(user_agent="anki_japan_cities")
cache_file = 'geocode_cache.json'

if os.path.exists(cache_file):
    with open(cache_file, 'r', encoding='utf-8') as f:
        geocode_cache = json.load(f)
    print(f"Loaded {len(geocode_cache)} cached locations")
else:
    geocode_cache = {}

for idx, row in cities_df.iterrows():
    key_name = row['kanji']
    reading = row['reading']
    
    result = geocode_with_fallbacks(key_name, reading, geolocator, geocode_cache)
    
    # If prefecture is missing but we have coordinates, use shapefile to find it
    if result['found'] and not result['prefecture']: 
        prefecture = get_prefecture_from_coordinates(result['lat'], result['lon'], japan_prefectures)
        if prefecture and key_name in geocode_cache:
            geocode_cache[key_name]['prefecture'] = prefecture
    
    
    cities_df.at[idx, 'lat'] = result['lat'] if result['found'] else None
    cities_df.at[idx, 'lon'] = result['lon'] if result['found'] else None
    cities_df.at[idx, 'geocode_query'] = result['query'] if result['found'] else None
    cities_df.at[idx, 'prefecture'] = result['prefecture'] if result['found'] else None
    
    if result['found']:
        pref_info = f" [{result['prefecture']}]" if result['prefecture'] else ""
        print(f"Done {idx+1}/{len(cities_df)}: {key_name}{pref_info} -> {result['lat']:.4f}, {result['lon']:.4f}  (via: {result['query']})")
    else:
        print(f"✗ {idx+1}/{len(cities_df)}: {key_name} - Not found (will be included in TSV but no zoomed map)")


with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(geocode_cache, f, ensure_ascii=False, indent=2)

cities_df.to_csv('geocoded_cities.csv', index=False, encoding='utf-8')
print(f"\nSuccessfully processed and saved {len(cities_df)} cities")


# Convert shp data to projected CRS (meters) for buffering
japan_proj = japan.to_crs("EPSG:3857")
prefectures_proj = japan_prefectures.to_crs("EPSG:3857")

# Helper function to make safe filenames
illegal_re = re.compile(r'[\\/:*?"<>|]')

def make_safe_basename(name:  str) -> str:
    """Return a filesystem-safe basename (no suffix). Keeps Japanese characters."""
    if name is None:
        name = 'unknown'
    safe = illegal_re.sub('_', name)
    safe = safe.replace('\n', '').replace('\r', '').strip()
    safe = re.sub(r'_+', '_', safe)
    if not safe:
        safe = 'unknown'
    return safe

### Generate zoomed maps for each city
print("\n=== Generating individual city maps ===")
buffer_distance = 300 * 1000  # 300 km in meters
cities_df['map_zoomed'] = ''

for idx, row in cities_df.iterrows():
    city_name = row['kanji']
    
    safe_basename = make_safe_basename(city_name)
    safe_filename = f"{safe_basename}_zoomed.png"
    output_path = os.path.join(output_folder, safe_filename)

    if not (pd.notna(row['lat']) or pd.notna(row['lon'])):
        raise ValueError(f"City {city_name} is missing coordinates, cannot generate zoomed map")
    
    # Build single-row GeoDataFrame in projected CRS
    pt_gdf = gpd.GeoDataFrame([{'geometry': Point(row['lon'], row['lat'])}], crs="EPSG:4326")
    pt_proj = pt_gdf.to_crs("EPSG:3857")
    city_buffer = pt_proj.buffer(buffer_distance)
    minx, miny, maxx, maxy = city_buffer.total_bounds

    # If image doesn't exist, create it
    if not os.path.exists(output_path):
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_facecolor('#E8F4F8')

        # Plot each region with its color
        for region, color in region_colors.items():
            region_prefs = prefectures_proj[prefectures_proj['region'] == region]
            if len(region_prefs) > 0:
                region_prefs.plot(ax=ax, color=color, edgecolor='#333333', linewidth=1.2, alpha=0.9)

        # Plot country border
        japan_proj.plot(ax=ax, color='none', edgecolor='#000000', linewidth=2.5)

        # Plot this city point
        pt_proj.plot(ax=ax, color='#D32F2F', markersize=200, zorder=6, marker='X',
                        edgecolor='white', linewidth=1.85)

        # Set zoom to this city
        ax.set_xlim(minx, maxx)
        ax.set_ylim(miny, maxy)

        ax.set_axis_off()
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='none')
        plt.close(fig)
        print(f"✅ {idx+1}/{len(cities_df)}: {city_name} - Map saved to {output_path}")
    else:
        print(f"⏭️  {idx+1}/{len(cities_df)}: {city_name} - {safe_filename} exists, skipping")
    
    cities_df.at[idx, 'map_zoomed'] = safe_filename


### Prepare dataframe for Anki import, manually fix some problems and write TSV
anki_df = pd.DataFrame({
    'Kanji': cities_df['kanji'],
    'Reading': cities_df['reading'].fillna(''),
    'Audio': cities_df['audio_filename'].apply(lambda x: f'[sound:{x}]' if x else ''),
    'Rank according to residents': cities_df['rank'].fillna(''),
    'Population_(2020)': cities_df['population'].fillna(''),
    'Prefecture': cities_df['prefecture'].fillna(''),
    'Map': cities_df['map_filename'].apply(lambda x: f'<img src="{os.path.basename(x)}">' if x else ''),
    'Map_zoomed': cities_df['map_zoomed'].apply(lambda x: f'<img src="{x}">' if x else ''),
    'Map_empty': cities_df['map_empty_filename'].apply(lambda x: f'<img src="{os.path.basename(x)}">' if x else '')
})

anki_df['__rank_num'] = pd.to_numeric(anki_df['Rank according to residents'], errors='coerce').fillna(10**9).astype(int)
anki_df = anki_df.sort_values('__rank_num').drop(columns='__rank_num').reset_index(drop=True)
anki_df.loc[anki_df["Kanji"] == "八尾", "Audio"] = "howtopronounce_八尾.mp3"

anki_import_path = 'Japanese_cities_anki_import.tsv'
anki_df.to_csv(anki_import_path, sep='\t', index=False, encoding='utf-8', header=False)
print(f"\n✨ All done! Generated maps in '{output_folder}/' folder and Anki TSV '{anki_import_path}'")