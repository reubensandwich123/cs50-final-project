

# CS50 Final Project

This repository contains my CS50 final project, a web application built with Flask that processes and analyzes financial data extracted from PDF bank statements. It features data visualization, advanced data handling, and modern UI design techniques.

---

## Features & Technologies Used

* **PDF Data Extraction**

  * Use of `pdfplumber` to extract text from bank statement PDFs
  * Regular expressions (`re` module) to parse and extract relevant financial data

* **Data Processing & Analysis**

  * Construction of dataframes from lists of dictionaries for easy manipulation
  * Use of `datetime` library to convert date strings into `datetime` objects, enabling time series analysis with pandas
  * Storage and retrieval of dataframes in SQLite databases

* **Web Application**

  * Flask framework serving as the backend
  * User authentication and session management
  * File upload handling for bank statements

* **Data Visualization**

  * Matplotlib plots generated dynamically from dataframes
  * Conversion of plots to PNG images in-memory using `BytesIO` buffers for serving via Flask’s `send_file`
  * Customization of plot size (`figsize`), date formatting on x-axis (showing day only), and usage of colormaps for better aesthetics

* **Frontend & Styling**

  * Implementation of modern CSS design styles including **glassmorphism** and **neumorphism** for visually appealing user interfaces
  * Jinja2 templating with custom filters:

    * A monetary value formatter for currency display
    * Use of `safe` filter to render raw HTML safely
  * Conversion of pandas dataframes to HTML tables with `.to_html()` for displaying data on pages

---

## How to Use

1. **Upload Bank Statement PDF**
   Upload your bank statement PDF through the web interface. The system will extract and parse the transaction data.

2. **Analyze Transactions**
   View detailed analyses such as total withdrawals, deposits, and transaction counts.

3. **Visualize Data**
   Access various interactive plots and charts representing your financial data trends.

---

## Key Code Highlights

* Regex extraction pattern examples for capturing dates and monetary values from PDFs
* Dataframe manipulation using `to_frame()`, `reset_index()`, and filtering
* Flask routes for handling uploads, analysis, and plotting with image buffers
* SQL integration for persistent storage of user data and analyses
* Use of matplotlib colormaps for color-coded plots enhancing readability

---

