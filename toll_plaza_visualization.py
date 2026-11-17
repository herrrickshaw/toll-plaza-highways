#!/usr/bin/env python3
"""
Toll Plaza Traffic & Collection Visualization System
- Extracts toll plaza data from PDFs
- Geocodes locations
- Creates interactive maps with heat maps for monthly collections
- Visualizes traffic movement across major toll booths
"""

import pandas as pd
import numpy as np
import pdfplumber
import json
from pathlib import Path
from datetime import datetime, timedelta
import re

class TollPlazaVisualization:
    def __init__(self):
        self.plazas_df = None
        self.payment_data = None
        self.geocoded_plazas = None

    def extract_toll_plazas_from_pdf(self, pdf_paths):
        """Extract toll plaza data from multiple PDFs"""
        all_records = []

        for pdf_path in pdf_paths:
            print(f"Processing {Path(pdf_path).name}...")
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    if tables:
                        for table in tables:
                            headers = table[0]
                            for row in table[1:]:
                                if row and any(row):
                                    all_records.append(row)

        # Convert to DataFrame and clean
        self.plazas_df = pd.DataFrame(all_records)
        self._clean_plaza_data()
        return self.plazas_df

    def _clean_plaza_data(self):
        """Clean and structure the extracted toll plaza data"""
        # Remove completely empty rows and columns
        self.plazas_df = self.plazas_df.dropna(how='all')
        self.plazas_df = self.plazas_df.dropna(axis=1, how='all')

        indian_states = [
            'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
            'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
            'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya',
            'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim',
            'Tamil Nadu', 'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand',
            'West Bengal', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Puducherry', 'Chandigarh'
        ]
        state_lc = {s.lower(): s for s in indian_states}
        nh_re = re.compile(r'\bNH[-\s]?\d+', re.IGNORECASE)

        def is_plaza_text(v):
            return 'toll' in v.lower() or 'plaza' in v.lower()

        structured_data = []
        for idx, row in self.plazas_df.iterrows():
            row_dict = {}
            row_list = [str(x).strip() for x in row if pd.notna(x) and str(x).strip()]

            # State: a cell that IS a state name wins; otherwise a non-plaza cell containing one.
            exact = [state_lc[v.lower()] for v in row_list if v.lower() in state_lc]
            if exact:
                row_dict['state'] = exact[0]
            else:
                for v in row_list:
                    if not is_plaza_text(v) and any(st in v for st in indian_states):
                        row_dict['state'] = v
                        break

            highways = [v for v in row_list if nh_re.search(v) and not is_plaza_text(v)]
            if highways:
                row_dict['highway'] = highways[0]

            # Plaza name: a cell mentioning toll/plaza, else the first descriptive cell
            # (not a serial number, the state or the highway).
            plaza_candidates = [v for v in row_list if is_plaza_text(v)]
            if not plaza_candidates:
                plaza_candidates = [v for v in row_list
                                    if not re.fullmatch(r'[\d.\s]+', v)
                                    and v != row_dict.get('state') and v != row_dict.get('highway')]
            row_dict['plaza_name'] = plaza_candidates[0] if plaza_candidates else f"Unknown_Plaza_{idx}"

            row_dict['raw_data'] = ' | '.join(row_list)
            structured_data.append(row_dict)

        self.plazas_df = pd.DataFrame(structured_data).reindex(
            columns=['plaza_name', 'state', 'highway', 'raw_data'])

        # Remove duplicates based on plaza name
        self.plazas_df = self.plazas_df.drop_duplicates(subset=['plaza_name'], keep='first')

        print(f"✓ Extracted {len(self.plazas_df)} unique toll plazas")
        print(f"✓ States covered: {self.plazas_df['state'].nunique()}")

        return self.plazas_df

    def geocode_plazas(self):
        """
        Geocode toll plaza locations using geopy.
        Note: This requires actual location names and may need manual review.
        """
        try:
            from geopy.geocoders import Nominatim
            geocoder = Nominatim(user_agent="toll_plaza_mapper")
        except ImportError:
            print("Installing geopy for geocoding...")
            import subprocess
            subprocess.run(['pip', 'install', 'geopy', '-q'])
            from geopy.geocoders import Nominatim
            geocoder = Nominatim(user_agent="toll_plaza_mapper")

        print("Geocoding toll plazas (this may take a few minutes)...")

        lats = []
        lons = []

        for idx, row in self.plazas_df.iterrows():
            if idx % 50 == 0:
                print(f"  Progress: {idx}/{len(self.plazas_df)}")

            try:
                plaza_name = row['plaza_name']
                state = row.get('state', '')
                search_query = f"{plaza_name}, {state}, India"

                location = geocoder.geocode(search_query, timeout=10)

                if location:
                    lats.append(location.latitude)
                    lons.append(location.longitude)
                else:
                    lats.append(None)
                    lons.append(None)
            except:
                lats.append(None)
                lons.append(None)

        self.plazas_df['latitude'] = lats
        self.plazas_df['longitude'] = lons

        # Count successful geocoding
        success = self.plazas_df[['latitude', 'longitude']].notna().all(axis=1).sum()
        print(f"✓ Successfully geocoded {success}/{len(self.plazas_df)} plazas")

        return self.plazas_df

    def create_base_map(self, output_html='toll_plazas_map.html'):
        """Create interactive base map with all toll plazas"""
        if self.plazas_df is None or 'latitude' not in self.plazas_df.columns:
            print("Error: Plazas must be extracted and geocoded first")
            return None

        try:
            import folium
            from folium.plugins import HeatMap, MarkerCluster
        except ImportError:
            print("Installing folium...")
            import subprocess
            subprocess.run(['pip', 'install', 'folium', '-q'])
            import folium
            from folium.plugins import HeatMap, MarkerCluster

        # Calculate center of India
        valid_plazas = self.plazas_df.dropna(subset=['latitude', 'longitude'])
        if len(valid_plazas) > 0:
            center_lat = valid_plazas['latitude'].mean()
            center_lon = valid_plazas['longitude'].mean()
        else:
            # Default to center of India
            center_lat, center_lon = 23.6345, 85.2988

        # Create base map
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=5,
            tiles='OpenStreetMap'
        )

        # Add marker cluster
        marker_cluster = MarkerCluster().add_to(m)

        # Add toll plaza markers
        for idx, row in valid_plazas.iterrows():
            folium.Marker(
                location=[row['latitude'], row['longitude']],
                popup=f"""
                <b>{row['plaza_name']}</b><br>
                State: {row.get('state', 'Unknown')}<br>
                Highway: {row.get('highway', 'Unknown')}
                """,
                tooltip=row['plaza_name'],
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(marker_cluster)

        m.save(output_html)
        print(f"✓ Base map created: {output_html}")
        return m

    def create_heat_map(self, payment_data=None, output_html='toll_plazas_heatmap.html'):
        """
        Create heat map visualization of toll collections.

        Args:
            payment_data: DataFrame with columns [plaza_name, date, amount, latitude, longitude]
                         If None, generates sample data for demonstration
        """
        try:
            import folium
            from folium.plugins import HeatMap
        except ImportError:
            print("Installing folium...")
            import subprocess
            subprocess.run(['pip', 'install', 'folium', '-q'])
            import folium
            from folium.plugins import HeatMap

        if payment_data is None:
            # Generate sample payment data for demonstration
            print("Generating sample payment data for visualization...")
            valid_plazas = self.plazas_df.dropna(subset=['latitude', 'longitude']).copy()

            if len(valid_plazas) == 0:
                print("Error: No geocoded plazas available")
                return None

            # Create sample data for 12 months
            payment_records = []
            base_date = datetime(2024, 1, 1)

            for month in range(12):
                current_date = base_date + timedelta(days=30*month)
                for idx, row in valid_plazas.iterrows():
                    # Generate realistic collection amounts (₹ lakhs)
                    base_amount = np.random.uniform(50, 500)  # Base amount varies by plaza
                    monthly_amount = base_amount * np.random.uniform(0.8, 1.2)  # Monthly variation

                    payment_records.append({
                        'plaza_name': row['plaza_name'],
                        'state': row.get('state', 'Unknown'),
                        'date': current_date,
                        'month': current_date.strftime('%Y-%m'),
                        'amount': monthly_amount,
                        'latitude': row['latitude'],
                        'longitude': row['longitude']
                    })

            payment_data = pd.DataFrame(payment_records)
            self.payment_data = payment_data

        # Create heat map by month
        months = sorted(payment_data['month'].unique())

        print(f"Creating monthly heat maps for {len(months)} months...")

        # Create map with all months combined (showing intensity)
        center_lat = payment_data['latitude'].mean()
        center_lon = payment_data['longitude'].mean()

        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=5,
            tiles='CartoDB positron'
        )

        # Prepare heat map data - normalize by collection amount
        max_amount = payment_data['amount'].max()
        heat_data = []

        for idx, row in payment_data.iterrows():
            # Intensity represents collection amount (normalized 0-1)
            intensity = row['amount'] / max_amount
            heat_data.append([row['latitude'], row['longitude'], intensity])

        HeatMap(heat_data, radius=25, blur=15, max_zoom=1).add_to(m)

        m.save(output_html)
        print(f"✓ Heat map created: {output_html}")

        # Also create monthly breakdowns
        for month in months:
            month_data = payment_data[payment_data['month'] == month]

            m_monthly = folium.Map(
                location=[center_lat, center_lon],
                zoom_start=5,
                tiles='CartoDB positron',
                name=f'Collections - {month}'
            )

            month_heat_data = []
            for idx, row in month_data.iterrows():
                intensity = row['amount'] / max_amount
                month_heat_data.append([row['latitude'], row['longitude'], intensity])

            if month_heat_data:
                HeatMap(month_heat_data, radius=25, blur=15).add_to(m_monthly)

            m_monthly.save(f'toll_heatmap_{month}.html')

        print(f"✓ Monthly heat maps created (total: {len(months)} files)")
        return m, payment_data

    def generate_report(self):
        """Generate a summary report of toll plaza data"""
        if self.plazas_df is None:
            return None

        report = {
            'total_plazas': len(self.plazas_df),
            'states_covered': self.plazas_df['state'].nunique(),
            'states': self.plazas_df['state'].value_counts().to_dict(),
            'highways': self.plazas_df.get('highway', pd.Series()).value_counts().head(10).to_dict(),
            'geocoded_plazas': self.plazas_df[['latitude', 'longitude']].notna().all(axis=1).sum() if 'latitude' in self.plazas_df.columns else 0
        }

        print("\n" + "="*60)
        print("TOLL PLAZA SUMMARY REPORT")
        print("="*60)
        print(f"Total Plazas Extracted: {report['total_plazas']}")
        print(f"States Covered: {report['states_covered']}")
        print(f"Plazas with Coordinates: {report['geocoded_plazas']}")
        print("\nTop States by Plaza Count:")
        for state, count in sorted(report['states'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {state}: {count}")
        print("="*60 + "\n")

        return report


def main():
    """Main execution"""
    pdf_paths = [
        '/Users/umashankar/Downloads/NH-Fee-Plazas-1.pdf',
        '/Users/umashankar/Downloads/NH-Toll-Plaza-.pdf',
        '/Users/umashankar/Downloads/NHAI-toll-list.pdf'
    ]

    viz = TollPlazaVisualization()

    # Step 1: Extract toll plaza data
    print("Step 1: Extracting toll plaza data from PDFs...")
    plazas = viz.extract_toll_plazas_from_pdf(pdf_paths)

    # Step 2: Save cleaned data
    plazas.to_csv('/Users/umashankar/Downloads/toll_plazas_cleaned.csv', index=False)
    print("✓ Cleaned data saved to: toll_plazas_cleaned.csv")

    # Step 3: Geocode plazas (optional - slower)
    print("\nStep 2: Geocoding toll plaza locations...")
    print("(Skipping live geocoding - using sample coordinates instead)")

    # Add sample coordinates for testing
    state_coords = {
        'Gujarat': (22.3, 72.6),
        'Maharashtra': (19.76, 75.71),
        'Rajasthan': (27.0, 74.2),
        'Haryana': (29.0, 77.0),
        'Tamil Nadu': (11.1, 79.8),
        'Karnataka': (15.3, 75.9),
        'Andhra Pradesh': (15.9, 78.5),
        'Telangana': (17.4, 78.5),
        'Punjab': (31.5, 74.8),
        'Uttar Pradesh': (26.8, 80.6),
        'Delhi': (28.6, 77.2),
        'Himachal Pradesh': (32.2, 77.2),
        'Madhya Pradesh': (22.9, 78.6),
        'West Bengal': (24.2, 88.4),
    }

    lats = []
    lons = []
    for idx, row in viz.plazas_df.iterrows():
        state = row.get('state', 'Unknown')
        if state in state_coords:
            lat, lon = state_coords[state]
            # Add some randomness
            lat += np.random.uniform(-0.5, 0.5)
            lon += np.random.uniform(-0.5, 0.5)
            lats.append(lat)
            lons.append(lon)
        else:
            lats.append(None)
            lons.append(None)

    viz.plazas_df['latitude'] = lats
    viz.plazas_df['longitude'] = lons
    print(f"✓ Added sample coordinates for {len([l for l in lats if l is not None])}/{len(lats)} plazas")

    # Step 4: Create visualizations
    print("\nStep 3: Creating interactive maps...")

    # Base map
    viz.create_base_map('/Users/umashankar/Downloads/toll_plazas_map.html')

    # Heat map with sample data
    viz.create_heat_map(output_html='/Users/umashankar/Downloads/toll_collections_heatmap.html')

    # Step 5: Generate report
    print("\nStep 4: Generating summary report...")
    report = viz.generate_report()

    print("\n✅ Visualization complete!")
    print("\nGenerated files:")
    print("  📍 toll_plazas_map.html - Interactive map of all toll plazas")
    print("  🔥 toll_collections_heatmap.html - Heat map of collections")
    print("  📊 toll_plazas_cleaned.csv - Cleaned plaza data")
    print("\nTo view the maps, open the HTML files in your browser.")
    print("\nNote: For real data integration, provide a CSV with columns:")
    print("      [plaza_name, date, amount, latitude, longitude]")


if __name__ == '__main__':
    main()
