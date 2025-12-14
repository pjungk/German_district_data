import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import os
from urllib.request import urlretrieve

headers = {
    "User-Agent": (
        "NobelDataCollector/1.0 (https://example.com/contact) "
        "Python-Requests"
    )
}

pages = {
    "Physics": "https://en.wikipedia.org/wiki/List_of_Nobel_laureates_in_Physics",
    "Chemistry": "https://en.wikipedia.org/wiki/List_of_Nobel_laureates_in_Chemistry",
    "Economics": "https://en.wikipedia.org/wiki/List_of_Nobel_Memorial_Prize_laureates_in_Economic_Sciences",
    "Physiology_or_Medicine": "https://en.wikipedia.org/wiki/List_of_Nobel_laureates_in_Physiology_or_Medicine"
}


laur_wo_img = {
    "Kenneth G. Wilson": "https://upload.wikimedia.org/wikipedia/en/d/d1/Kenneth_G._Wilson.jpg",
    'Ernst Ruska': "https://upload.wikimedia.org/wikipedia/en/9/90/Ernst_Ruska.jpg",
    'Hans Georg Dehmelt': "https://upload.wikimedia.org/wikipedia/commons/a/aa/Hans_Dehmelt.jpg",
    'Wolfgang Paul': "https://upload.wikimedia.org/wikipedia/en/c/c0/Wolfgang_Paul.jpg",
    'Stanford Moore': "https://upload.wikimedia.org/wikipedia/en/7/7f/Stanford_Moore.jpg",
    'William H. Stein': "https://upload.wikimedia.org/wikipedia/en/d/dd/William_Howard_Stein.jpg",
    'Ernst Otto Fischer': "https://www.nobelprize.org/images/fischer-13243-content-portrait-mobile-tiny.jpg",
    'Georg Wittig': "https://upload.wikimedia.org/wikipedia/en/e/ea/Georg_Wittig.jpg",
    'Donald J. Cram': "https://www.nobelprize.org/images/cram-13387-content-portrait-mobile-tiny.jpg",
    'Charles J. Pedersen': "https://upload.wikimedia.org/wikipedia/en/b/bd/Charles_J._Pedersen.jpg",
    'William S. Knowles': "https://upload.wikimedia.org/wikipedia/en/6/6b/William_Standish_Knowles.jpg",
    'Richard Robson': "https://cdn.britannica.com/67/278067-050-C9CA38A8/richard-robson-professor-university-of-melbourne-2025-nobel-prize-chemistry-metal-organic-frameworks.jpg",
    'George Stigler': "https://upload.wikimedia.org/wikipedia/en/c/c7/George_Stigler.jpg",
    'Richard Stone': "https://upload.wikimedia.org/wikipedia/en/7/71/Richard_Stone.jpg",
    'Harry Markowitz': "https://www.nobelprize.org/images/markowitz-13420-content-portrait-mobile-tiny.jpg",
    'Merton Miller': "https://upload.wikimedia.org/wikipedia/en/7/7c/Merton_Miller.jpg",
    'John Harsanyi': "https://upload.wikimedia.org/wikipedia/en/6/6b/John_Harsanyi.jpg",
    'William Vickrey': "https://upload.wikimedia.org/wikipedia/en/2/2d/William_Vickrey.gif",
    'Robert B. Wilson': "https://www.nobelprize.org/images/wilson-robert%20b111769-portrait-medium.jpg",
    'Peter Howitt': "https://cdn.britannica.com/67/278267-050-F03DDEE7/Peter-Howitt-Awarded-Sveriges-Riksbank-Prize-In-Economic-Sciences-In-Memory-Of-Alfred-Nobel-2025.jpg",
    'John Franklin Enders': "https://upload.wikimedia.org/wikipedia/en/8/83/John_Franklin_Enders_nobel.jpg",
    'George D. Snell': "https://www.nobelprize.org/images/snell-13328-content-portrait-mobile-tiny.jpg",
    'Joseph E. Murray': "https://upload.wikimedia.org/wikipedia/en/3/3a/Joseph_Murray_Nobel_Portrait.jpg",
    'Edwin G. Krebs': "https://upload.wikimedia.org/wikipedia/en/9/9e/Edwin_G._Krebs.jpg",
    'Leland H. Hartwell': "https://www.nobelprize.org/images/hartwell-13731-content-portrait-mobile-tiny.jpg",
    'H. Robert Horvitz': "https://www.nobelprize.org/images/horvitz-13885-content-portrait-mobile-tiny.jpg",
    'Mary E. Brunkow': "https://cdn.britannica.com/62/278062-050-35F9BDAA/Dr-Mary-Brunkow-2025-Nobel-Prize-winner.jpg",
    'Fred Ramsdell': "https://cdn.britannica.com/23/278023-050-FFCF289F/2025-Nobel-Prize-winner-Fred-Ramsdell.jpg"
    }



def clean_column(col):
    col = re.sub(r"\[.*?\]", "", col)
    col = re.sub(r"\(.*?\)", "", col)
    return col.strip()


def extract_birth_death(text):
    if pd.isna(text):
        return text, None, None

    name = re.sub(r"\s*\(.*?\)", "", text).strip()
    
    m = re.search(r"\(([^)]+)\)", text)
    birth, death = None, None

    if m:
        years = m.group(1)

        # Format: 1926–1996 (deceased)
        m_range = re.match(r"(\d{4})\s*[–-]\s*(\d{4})", years)
        if m_range:
            birth = int(m_range.group(1))
            death = int(m_range.group(2))
        else:
            # Format: b. 1932 (still alive)
            m_birth = re.search(r"b\.\s*(\d{4})", years)
            if m_birth:
                birth = int(m_birth.group(1))
                death = None

    return name, birth, death


def get_local_filename_from_url(url):
    """Return the local filename (basename + extension) from URL."""
    if url is None:
        return None
    return os.path.basename(url.split("/")[-1])


def get_extension(url):
    """Return file extension (.jpg, .png). Default to .jpg."""
    if url is None:
        return "jpg"
    match = re.search(r"\.(jpg|jpeg|png|webp|gif)", url, re.IGNORECASE)
    return match.group(1) if match else "jpg"


all_dfs = []

for prize_type, url in pages.items():
    print(f"Downloading {prize_type}…")

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html = response.text
    soup = BeautifulSoup(html, "html.parser")

    df = pd.read_html(html)[0]
    df.columns = [clean_column(c) for c in df.columns]
    df["Prize_Type"] = prize_type

    # Normalize column names across pages
    if "Country" in df.columns:
        df.rename(columns={"Country": "Nationality"}, inplace=True)
    if "Laureate (birth/death)" in df.columns:
        df.rename(columns={"Laureate (birth/death)": "Laureate"}, inplace=True)

    # Remove reference columns
    df = df.loc[:, ~df.columns.str.contains("Ref", case=False)]

    # Extract Laureate portrait + nationality flag URLs
    table = soup.find("table", class_="wikitable")
    portrait_urls = []
    flag_urls = []

    for row in table.find_all("tr")[1:]:
        cells = row.find_all(["td", "th"])

        # Portrait image (col 2)
        if len(cells) > 1 and (cells[1].find("img") or cells[0].find("img")):
            img_tag = cells[0].find("img") or cells[1].find("img")
            src = img_tag["src"]
            if src.startswith("//"):
                src = "https:" + src
            portrait_urls.append(src)
        else:
            portrait_urls.append(None)

        # Nationality flag(s) - get ALL flag images from nationality cell
        flag_imgs = []

        # Check cells 2, 3, and last two cells for flags
        for idx in [2, 3, -1, -2]:
            if abs(idx) < len(cells):
                cell = cells[idx]
                
                # Find all images inside flagicon spans
                for span in cell.find_all("span", class_="flagicon"):
                    for img in span.find_all("img"):
                        src = img.get("src", "")
                        if src.startswith("//"):
                            src = "https:" + src
                        if src not in flag_imgs:
                            flag_imgs.append(src)

        flag_urls.append(";".join(flag_imgs) if flag_imgs else flag_urls[-1] if flag_urls else None)

    df["Portrait_URL"] = portrait_urls
    df["Flag_URL"] = flag_urls

    # Extract clean name + birth/death years
    names, births, deaths = [], [], []
    for val in df["Laureate"]:
        n, b, d = extract_birth_death(val)
        names.append(n)
        births.append(b)
        deaths.append(d)

    df["Laureate"] = names
    df["Birth_Year"] = pd.array(births, dtype="Int64")  # Use nullable Int64
    df["Death_Year"] = pd.array(deaths, dtype="Int64")  # Use nullable Int64

    # Add local paths for images
    laureate_local_paths = []
    flag_local_paths = []

    for name, birth, portrait, flag in zip(df["Laureate"], df["Birth_Year"],
                                           df["Portrait_URL"], df["Flag_URL"]):

        # ---- Laureate image ----
        ext = get_extension(portrait)
        safe_name = re.sub(r"[^A-Za-z0-9_]+", "_", name)
        if pd.isna(birth):
            birth = "unknown"
        laureate_local_paths.append(
            f"/imgs/Laureates/{safe_name}_{birth}.{ext}"
        )

        # ---- Nationality flag(s) ----
        if flag:
            # Handle multiple flags separated by semicolon
            flag_files = []
            for flag_url in flag.split(";"):
                filename = get_local_filename_from_url(flag_url.strip())
                if filename:
                    flag_files.append(f"/imgs/Flags/{filename}")
            flag_local_paths.append(";".join(flag_files) if flag_files else None)
        else:
            flag_local_paths.append(None)

    df["Laureate_img"] = laureate_local_paths
    df["Nationality_img"] = flag_local_paths

    all_dfs.append(df)


# ---- COMBINE & KEEP ONLY REQUIRED COLUMNS ----
df_all = pd.concat(all_dfs, ignore_index=True)

df_all = df_all[["Prize_Type", "Year", "Laureate", "Laureate_img", "Nationality", "Nationality_img", "Rationale",
                 "Birth_Year", "Death_Year", "Portrait_URL", "Flag_URL"
                 ]]

df_all = df_all.replace(r'\[\d+\]', '', regex=True)
df_all["Rationale"] = df_all["Rationale"].str.replace("'|\"", "", regex=True)
df_all["Nationality"] = df_all["Nationality"].str.replace("  ", ";", regex=False)
df_all.loc[df_all["Laureate"].isin(laur_wo_img.keys()), "Portrait_URL"] = df_all.loc[df_all["Laureate"].isin(laur_wo_img.keys()), "Laureate"].map(laur_wo_img)
# Handle years where prize was not awarded
not_awarded_mask = df_all["Laureate"].str.contains("Not awarded", case=False, na=False)
df_all.loc[not_awarded_mask, "Laureate"] = "Not awarded"
df_all.loc[not_awarded_mask, "Laureate_img"] = "/imgs/Not_awarded_placeholder.png"
df_all.loc[not_awarded_mask, 
           ["Nationality", "Rationale", "Birth_Year", "Death_Year", "Portrait_URL"] + [col for col in df_all.columns if "Nationality_img" in col or "Flag_URL" in col]] = None


print(df_all[(df_all["Portrait_URL"].str.contains("No_image|BLANK_ICON", na=True) | df_all["Portrait_URL"].isna()) &
             ~df_all["Laureate"].str.contains("Not awarded", na=True)]["Laureate"].tolist())

# Create directories
os.makedirs("imgs/Laureates", exist_ok=True)
os.makedirs("imgs/Flags", exist_ok=True)



def download_image(url, local_path):
    if url and local_path and not os.path.exists(local_path. lstrip("/")):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            with open(local_path. lstrip("/"), 'wb') as f:
                f.write(response.content)
            print(f"✓ {local_path}")
        except Exception as e:
            print(f"✗ {local_path}: {e}")


# Download portraits
portraits = df_all[["Portrait_URL", "Laureate_img"]].dropna()
for url, local_path in zip(portraits["Portrait_URL"], portraits["Laureate_img"]):
    download_image(url, local_path)

# Split semicolon-separated columns into multiple columns
def split_column(df, col_name, new_col_prefix):
    # Split by semicolon and expand into separate columns
    split_data = df[col_name].str.split(';', expand=True)
    
    # Rename columns
    for i in range(split_data.shape[1]):
        df[f"{new_col_prefix}_{i+1}"] = split_data[i]. str.strip()
    
    # Drop original column
    df.drop(col_name, axis=1, inplace=True)
    
    return split_data. shape[1]  # Return number of new columns created

# Split the three columns
max_nat = split_column(df_all, 'Nationality', 'Nationality')
max_img = split_column(df_all, 'Nationality_img', 'Nationality_img')
max_url = split_column(df_all, 'Flag_URL', 'Flag_URL')

print(f"Created {max_nat} Nationality columns, {max_img} Nationality_img columns, {max_url} Flag_URL columns")

# Download flags
flag_downloads = set()
for col in [c for c in df_all.columns if 'Flag_URL_' in c]:
    img_col = col.replace('Flag_URL_', 'Nationality_img_')
    for url, path in zip(df_all[col]. dropna(), df_all[img_col]. dropna()):
        flag_downloads.add((url, path))

for url, local_path in flag_downloads:
    download_image(url, local_path)

# Clean Rationale column including ” and “
df_all["Rationale"] = df_all["Rationale"].str.replace('"', '', regex=True).str.replace("'", "", regex=True).str.replace("“", "", regex=True).str.replace("”", "", regex=True)

anki_df = df_all[["Prize_Type", "Year", "Laureate", "Laureate_img", "Rationale", "Birth_Year", "Death_Year"] + [c for c in df_all. columns if 'Nationality' in c]]
for col in anki_df.columns:
    if 'img' in col:
        anki_df[col] = anki_df[col].apply(lambda x: f'<img src="{os.path.basename(x)}">' if pd.notna(x) else '')
anki_df.to_csv("nobel_laureates_anki.csv", index=False, header=False)

print("Saved results!")
