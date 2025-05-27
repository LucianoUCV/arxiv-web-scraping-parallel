# arXiv Web Scraper ( Parallel )
This is a Python project that allows you to scrape research papers from arXiv.org. You can search for papers based on a query and retrieve their metadata (such as authors, abstract, and PDF links) as well as download the content itself in the desired format ( PDF / HTML ). It has a similar functionality to the Sequential one, but much faster ( especially for large amounts ).

## Features
* Search for research papers based on specific keywords on arXiv.

* Scrape metadata such as title, authors, abstract ( summary ), and PDF and HTML URL.

* Download the PDFs / HTMLs of the papers into an automatically created output folder.

* Save metadata in a JSON file for future reference.

## Project Requirements
* **Algorithm**: Web scraping in a parallel manner using BeautifulSoup to extract data from arXiv.org and mpi4py for parallelization

* **Programming Language**: Python 3.

* **External libraries**: `requests`, `bs4` (BeautifulSoup), `os`, `json`, `re`, `time`, `math`


## Project Structure
* `main.py`: Main Python script for scraping data.
* `requirements.txt`: List of the libraries needed to run the app
* `output`: Example folder of downloaded papers
* `README.MD`: Project info and user guide.


## How to use
1. Clone the repository to your local machine: <br>
```bash
git clone https://github.com/LucianoUCV/arxiv-web-scraping-parallel.git
```
2. Navigate to the project directory: <br>
```bash
cd arxiv-web-scraping-parallel
```

3. Run the following command ( with the desired amount of processes ):<br>
```bash
mpiexec -n *no_of_processes* python main.py
```
4. Enter a search query, the number of papers you want to scrape and the desired format.

## Expected Output
* An "output" folder containing the downloaded PDF/HTML files of the scraped papers.
* An "articles.json" file containing metadata about the papers ( title, authors, abstract, PDF and HTML URLs )

---

### [mpi4py Documentation](https://mpi4py.readthedocs.io/en/stable/)

