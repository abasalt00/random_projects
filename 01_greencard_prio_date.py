import streamlit as st
import requests
import pdfplumber
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Function to scrape visa bulletin data from the PDF


@st.cache_data
def scrape_visa_bulletin_pdf(month):
    try:
        # Dynamically construct the PDF URL based on the selected month
        base_url = "https://travel.state.gov/content/dam/visas/Bulletins/visabulletin_"
        pdf_url = f"{base_url}{month}2024.pdf"

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
        # Assuming table starts with "1st"
        table_start = text.find("1st", section_start)
        if table_start == -1:
            return None

        # Extract the relevant portion of the text
        # Extract a chunk for the table
        table_text = text[table_start:table_start + 1000]

        # Parse the table manually
        lines = table_text.split("\n")
        data = []
        for line in lines:
            columns = line.split()
            if len(columns) > 1:
                data.append(columns)

        # Convert the parsed data into a pandas DataFrame
        df = pd.DataFrame(data)

        # Select only the desired columns (0 and 1) and rename them
        df = df.iloc[:, [0, 1]]  # Select column 0 and 1
        df.columns = ["Employment-based", "Priority Date"]  # Rename columns

        # Replace "1st", "2nd", "3rd", "4th", "5th" with "EB-1", "EB-2", "EB-3", "EB-4", "EB-5"
        df["Employment-based"] = df["Employment-based"].replace(
            {"1st": "EB-1", "2nd": "EB-2", "3rd": "EB-3",
                "4th": "EB-4", "5th": "EB-5"}
        )

        return df
    except Exception as e:
        return None

# Cache the plot data to avoid re-computation


@st.cache_resource
# Cache the plot data to avoid re-computation
# Cache the plot data to avoid re-computation
def get_plot_data():
    if "plot_data" not in st.session_state:
        plot_data = []
        for i, month in enumerate(months):
            data = scrape_visa_bulletin_pdf(month)
            if data is not None and i + 1 < current_month:  # Passed month
                plot_data.append((month, data))
        st.session_state["plot_data"] = plot_data
    return st.session_state["plot_data"]

# Function to generate the plot


def generate_plot(plot_data):
    months_plot_eb2 = []
    dates_plot_eb2 = []
    months_plot_eb3 = []
    dates_plot_eb3 = []

    for month, df in plot_data:
        # Filter data for EB-2
        df_eb2 = df[df["Employment-based"] == "EB-2"]
        if not df_eb2.empty:
            months_plot_eb2.append(month)
            dates_plot_eb2.append(df_eb2["Priority Date"].iloc[0])

        # Filter data for EB-3
        df_eb3 = df[df["Employment-based"] == "EB-3"]
        if not df_eb3.empty:
            months_plot_eb3.append(month)
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
    plt.title("Priority Dates for EB-2 and EB-3 in 2024 (Passed Months)")
    plt.xticks(rotation=45)
    plt.legend()
    return plt


# Streamlit app
st.title("Visa Bulletin Priority Dates for 2024")

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
    # st.subheader("Priority Dates for EB-2 and EB-3 in Passed Months")
    plot = generate_plot(plot_data)
    st.pyplot(plot)

# Sidebar for upcoming months
# Sidebar for upcoming months
st.sidebar.subheader("Upcoming Months")
for i, month in enumerate(months):
    if i + 1 >= current_month:
        if st.sidebar.button(f"{month}"):
            data = scrape_visa_bulletin_pdf(month)
            if data is not None:
                st.sidebar.success(f"{month} 2024")
                st.sidebar.table(data)
            else:
                st.sidebar.error(f"No data available for {month}")
