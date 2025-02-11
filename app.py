import streamlit as st
import folium
import requests
import json
from shapely.geometry import shape, Point
from streamlit_folium import st_folium

st.set_page_config(layout="wide")
st.title("Interactive US County Climate Data Map")
st.write("Click on any county on the map to display the county's name and sample climate data (retrieved via API).")

# 1. Load the county-level GeoJSON data from Plotly (valid JSON data source)
@st.cache_data
def load_counties_geojson():
    url = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    r = requests.get(url)
    r.raise_for_status()
    return r.json()

try:
    counties_geojson = load_counties_geojson()
    st.write("County GeoJSON data loaded successfully!")
except Exception as e:
    st.error(f"Failed to load county GeoJSON data: {e}")
    counties_geojson = None

# 2. Create a base map centered over the US
m = folium.Map(location=[37.8, -96], zoom_start=4, control_scale=True)

# 3. Add the county GeoJSON layer with a tooltip that shows the county name
if counties_geojson:
    folium.GeoJson(
        counties_geojson,
        name="US Counties",
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME"],  # Use the "NAME" field from the Plotly data
            aliases=["County:"]
        ),
        style_function=lambda feature: {
            "fillColor": "#blue",
            "color": "black",
            "weight": 0.5,
            "fillOpacity": 0.1
        }
    ).add_to(m)

# 4. Display the map in Streamlit and capture click events
map_data = st_folium(m, width=800, height=600, returned_objects=["last_clicked", "last_active_drawing"])

if map_data and map_data.get("last_clicked"):
    click_lat = map_data["last_clicked"]["lat"]
    click_lng = map_data["last_clicked"]["lng"]
    st.write(f"You clicked at: Longitude {click_lng:.4f}, Latitude {click_lat:.4f}")
    
    clicked_point = Point(click_lng, click_lat)
    selected_county = None
    
    # Iterate over the county features to determine if the clicked point is inside a county
    for feature in counties_geojson["features"]:
        geom = shape(feature["geometry"])
        if geom.contains(clicked_point):
            selected_county = feature["properties"].get("NAME", "Unknown County")
            break
    
    if selected_county:
        st.subheader(f"Selected County: {selected_county}")
        # Example: call the Open-Meteo API using the county's centroid as a representative point
        centroid = geom.centroid
        api_url = (
            f"https://archive-api.open-meteo.com/v1/archive?"
            f"latitude={centroid.y:.4f}&longitude={centroid.x:.4f}"
            f"&start_date=2000-01-01&end_date=2024-12-31"
            f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
        )
        st.write("Fetching climate data...")
        try:
            response = requests.get(api_url)
            response.raise_for_status()
            climate_data = response.json()
            st.json(climate_data)
        except Exception as ex:
            st.error(f"Failed to fetch climate data: {ex}")
    else:
        st.info("The clicked location is not within any county.")
