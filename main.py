from mpi4py import MPI
import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
import math

comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()

# Automatically creates the output folder which will store the papers in a PDF format
def create_output_folder(folder_name = "output"):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    return folder_name


# Sanitizes the title
def clean_filename(text):
    return re.sub(r'[\\/*?:"<>|]', "", text)


# Returns the URL with 2 added parameters ( query - the topic and page )
def get_search_url(query, page):
    return f"https://arxiv.org/search/?query={query}&searchtype=all&abstracts=show&order=-announced_date_first&size=50&start={page*50}"


# Scraping function ( using bp4 )
def scrape_arxiv(query, amount):
    articles = []
    page = 0

    while len(articles) < amount:
        url = get_search_url(query, page)
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")

        results = soup.find_all("li", attrs = {"class": "arxiv-result"})
        if not results:
            break

        for result in results:
            if len(articles) > amount:
                break
            title = result.find("p", attrs={"class": "title"}).text.strip()
            authors = [a.text.strip() for a in result.find("p", {"class": "authors"}).find_all("a")]
            abstract = result.find("span", attrs={"class": "abstract-full"}).text.strip().replace("\n", "")[
                       :-7].strip()
            pdfLink = result.find("p", class_="list-title").find("a", string="pdf")
            pdfUrl = f"{pdfLink['href']}" if pdfLink else None
            htmlUrl = result.find("p", class_="list-title").find("a", href=True)["href"]

            articles.append({
                "title": title,
                "authors": authors,
                "abstract": abstract,
                "pdfUrl": pdfUrl,
                "htmlUrl": f"https://arxiv.org{htmlUrl}"
            })

        page += 1
    return articles


def main():
    start_time = time.time()

    query = input("What subject sparks your interest?:\n")
    amount = int(input(f"How many papers matching \"{query}\" would you like?:\n"))
    articles = scrape_arxiv(query, amount)
    #save_and_download(articles)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total time: {total_time}")

if __name__ == "__main__":
    main()
