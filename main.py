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
def scrape_page(query, page):
    url = get_search_url(query, page)
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    results = soup.find_all("li", attrs = {"class": "arxiv-result"})
    for result in results:
        title = result.find("p", attrs={"class": "title"}).text.strip()
        authors = [a.text.strip() for a in result.find("p", {"class": "authors"}).find_all("a")]
        abstract = result.find("span", attrs={"class": "abstract-full"}).text.strip().replace("\n", "")[
                    :-7].strip()
        pdfLink = result.find("p", class_="list-title").find("a", string="pdf")
        pdfUrl = f"{pdfLink['href']}" if pdfLink else None

        abs_link = result.find("p", class_="list-title").find("a", href=True)["href"]
        arxiv_id = abs_link.split("/abs/")[1]

        html_url = f"https://arxiv.org/html/{arxiv_id}"

        articles.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "pdfUrl": pdfUrl,
            "htmlUrl": html_url
            })

    return articles


def download_article(article, format, folder="output"):
    safe_title = clean_filename(article["title"])[:100]
    filename = os.path.join(folder, f"{safe_title}.{format}")

    try:
        if format == "pdf" and article["pdfUrl"]:
            content = requests.get(article["pdfUrl"]).content
        elif format == "html" and article["htmlUrl"]:
            content = requests.get(article["htmlUrl"]).content
        else:
            return False
        with open(filename, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[Rank {rank}] Error downloading {format.upper()}: {e}")
        return False


def parallel_scrape(query, amount):
    total_pages = math.ceil(amount / 50)
    pages_per_process = list(range(total_pages))[rank::size]
    collected = []

    for page in pages_per_process:
        articles = scrape_page(query, page)
        collected.extend(articles)
        if len(collected) >= amount:
            collected = collected[:amount]
            break

    return collected


def save_metadata(articles, filename="articles.json"):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=4)


def main():
    if rank == 0:
        query = input("What subject sparks your interest?:\n")
        amount = int(input(f"How many papers matching \"{query}\" would you like?:\n"))
        format_choice = input("Choose format (pdf/html):\n").strip().lower()
    else:
        query = amount = format_choice = None

    query = comm.bcast(query, root=0)
    amount = comm.bcast(amount, root=0)
    format_choice = comm.bcast(format_choice, root=0)

    create_output_folder("output")

    local_articles = parallel_scrape(query, amount)

    gathered = comm.gather(local_articles, root=0)

    if rank == 0:
        all_articles = [article for sublist in gathered for article in sublist][:amount]

        for article in all_articles:
            download_article(article, format=format_choice, folder="output")

        save_metadata(all_articles)
        print(f"\033[35mMetadata saved and files downloaded in \"output\" folder\033[0m")


if __name__ == "__main__":
    start = time.time()
    main()
    end = time.time()

    if rank == 0:
        print(f"Total time: {end - start:.2f} seconds")
