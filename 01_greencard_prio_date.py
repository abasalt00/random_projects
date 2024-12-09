import streamlit as st
import requests
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Function to scrape visa bulletin data from the PDF


@st.cache_data
def scrape_visa_bulletin_pdf(month, year):
    try:
        # Dynamically construct the PDF URL based on the selected month and year
        base_url = "https://travel.state.gov/content/dam/visas/Bulletins/visabulletin_"
        pdf_url = f"{base_url}{month}{year}.pdf"

        # Download the PDF file
        response = requests.get(pdf_url)
        if response.status_code != 200:
            return None

        # Save the PDF locally
        pdf_path = "visa_bulletin.pdf"
        with open(pdf_path, "wb") as f:
            f.write(response.content)

        # Extract text from the PDF
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text()

        # Find the relevant section
        section_title = "B. DATES FOR FILING OF EMPLOYMENT-BASED VISA APPLICATIONS"
        if section_title not in text:
            return None

        # Extract the section and the table
        section_start = text.find(section_title)
        table_start = text.find("1st", section_start)
        if table_start == -1:
            return None

        # Extract the relevant portion of the text
        table_text = text[table_start:]

        # Parse the table manually
        lines = table_text.split("\n")
        data = []
        current_row = []

        for line in lines:
            # Check if the line starts with a valid employment-based category
            if line.split()[0] in ["1st", "2nd", "3rd", "4th", "5th", "Certain", "Other"]:
                if current_row:
                    data.append(current_row)
                current_row = [line]
            else:
                current_row.append(line)

        # Add the last row to the data
        if current_row:
            data.append(current_row)

        # Flatten rows and split columns based on spaces
        flattened_data = []
        for row in data:
            combined_row = " ".join(row)
            columns = combined_row.split()
            flattened_data.append(columns)

        # Convert the parsed data into a pandas DataFrame
        df = pd.DataFrame(flattened_data)
        df = df.iloc[:, :2]  # Select only the first two columns
        df.columns = ["Employment-based", "Priority Date"]

        # Replace "1st", "2nd", etc., with "EB-1", "EB-2", etc.
        df["Employment-based"] = df["Employment-based"].replace(
            {
                "1st": "EB-1", "2nd": "EB-2", "3rd": "EB-3",
                "4th": "EB-4", "5th": "EB-5", "Certain": "Certain Religious Workers",
                "Other": "Other Workers",
            }
        )

        # Filter for only EB-1, EB-2, EB-3, and EB-4
        df = df[df["Employment-based"].isin(["EB-1", "EB-2", "EB-3", "EB-4"])]

        # Filter out invalid priority dates
        df = df[~df["Priority Date"].isin(["Set", "Unreserved"])]
        return df

    except Exception as e:
        st.error(f"An error occurred: {e}")
        return None


# Cache the plot data to avoid re-computation
@st.cache_resource
def get_plot_data():
    plot_data = []
    for year in [2024, 2025]:  # Check both years
        for month in months:
            data = scrape_visa_bulletin_pdf(month, year)
            if data is not None:
                plot_data.append((f"{month} {year}", data))
    return plot_data


# Function to generate the plot
def generate_plot(plot_data):
    months_plot_eb2 = []
    dates_plot_eb2 = []
    months_plot_eb3 = []
    dates_plot_eb3 = []

    for month_year, df in plot_data:
        # Filter data for EB-2
        df_eb2 = df[df["Employment-based"] == "EB-2"]
        if not df_eb2.empty:
            months_plot_eb2.append(month_year)
            dates_plot_eb2.append(df_eb2["Priority Date"].iloc[0])

        # Filter data for EB-3
        df_eb3 = df[df["Employment-based"] == "EB-3"]
        if not df_eb3.empty:
            months_plot_eb3.append(month_year)
            dates_plot_eb3.append(df_eb3["Priority Date"].iloc[0])

    # Convert priority dates to datetime objects for plotting
    if months_plot_eb2 and dates_plot_eb2:
        dates_plot_eb2 = pd.to_datetime(
            dates_plot_eb2, errors="coerce", format="%d%b%y")
    if months_plot_eb3 and dates_plot_eb3:
        dates_plot_eb3 = pd.to_datetime(
            dates_plot_eb3, errors="coerce", format="%d%b%y")

    # Plot the data
    plt.figure(figsize=(10, 5))
    if months_plot_eb2 and dates_plot_eb2 is not None:
        plt.plot(months_plot_eb2, dates_plot_eb2,
                 marker="o", label="EB-2", color="blue")
    if months_plot_eb3 and dates_plot_eb3 is not None:
        plt.plot(months_plot_eb3, dates_plot_eb3,
                 marker="o", label="EB-3", color="green")

    plt.xlabel("Months")
    plt.ylabel("Priority Dates")
    plt.title("Priority date for filing 485 in EB-2 and EB-3 categories")
    plt.xticks(rotation=45)
    plt.legend()
    return plt


# Streamlit app
st.title("Visa Bulletin Priority Dates")

# List of all months
months = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

# Current month
current_month = datetime.now().month

# Generate plot data
plot_data = get_plot_data()

# Display plot for EB-2 and EB-3
if plot_data:
    plot = generate_plot(plot_data)
    st.pyplot(plot)

    # Add a disclaimer under the plot
    st.write(
        """
        **Note:** This app is not responsible for any likely mistakes which might happen,
        so please double-check the priority dates at:
        [Visa Bulletin](https://travel.state.gov/content/travel/en/legal/visa-law0/visa-bulletin/2025/visa-bulletin-for-december-2024.html) to make sure.
        """
    )

    # Add contact information
    st.write(
        "For any questions or feedback, contact me on Telegram: [@adi18bh](https://t.me/adi18bh)")


# Sidebar for current month's data
st.sidebar.subheader("Current Month Data")
current_month_name = months[current_month - 1]
current_year = datetime.now().year

current_data = scrape_visa_bulletin_pdf(current_month_name, current_year)
if current_data is not None:
    st.sidebar.success(f"{current_month_name} {current_year}")
    st.sidebar.table(current_data)
else:
    st.sidebar.error(
        f"No data available for {current_month_name} {current_year}")
