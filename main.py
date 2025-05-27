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
def scrape_page(session, query, page):
    url = get_search_url(query, page)
    response = session.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    articles = []

    results = soup.find_all("li", attrs = {"class": "arxiv-result"})
    for result in results:
        title = result.find("p", attrs={"class": "title"}).text.strip()
        authors = [a.text.strip() for a in result.find("p", {"class": "authors"}).find_all("a")]
        abstract = result.find("span", attrs={"class": "abstract-full"}).text.strip().replace("\n", "")[
                    :-7].strip()
        pdf_link = result.find("p", class_="list-title").find("a", string="pdf")
        pdf_url = f"{pdf_link['href']}" if pdf_link else None

        abs_link = result.find("p", class_="list-title").find("a", href=True)["href"]
        arxiv_id = abs_link.split("/abs/")[1]

        html_url = f"https://arxiv.org/html/{arxiv_id}"

        articles.append({
            "title": title,
            "authors": authors,
            "abstract": abstract,
            "pdf_url": pdf_url,
            "html_url": html_url
            })

    return articles


# Download articles in desired format ( either pdf or html )
def download_article(session, article, format, folder="output"):
    safe_title = clean_filename(article["title"])[:100]
    filename = os.path.join(folder, f"{safe_title}.{format}")

    try:
        if format == "pdf" and article["pdf_url"]:
            url = article["pdf_url"]
        elif format == "html" and article["html_url"]:
            url = article["html_url"]
        else:
            return False
        content = session.get(url).content
        with open(filename, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[Rank {rank}] Error downloading {format.upper()}: {e}")
        return False


# Parallel scraping method
def parallel_scrape(session, query, amount):
    total_pages = math.ceil(amount / 50)
    pages_per_process = list(range(total_pages))[rank::size]
    collected = []

    for page in pages_per_process:
        articles = scrape_page(session, query, page)
        collected.extend(articles)
        if len(collected) >= amount:
            collected = collected[:amount]
            break

    return collected


# Save JSON metadata
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

    session = requests.Session()

    local_articles = parallel_scrape(session, query, amount)

    failed_articles = []

    for article in local_articles:
        success = download_article(session, article, format=format_choice, folder="output")
        if not success:
            failed_articles.append(article)

    if format_choice == "html" and failed_articles:
        print(
            f"\033[31m{len(failed_articles)} research papers couldn't be downloaded due to missing HTML URL.\033[0m")
        answer = input("Do you want to download them as PDF instead? (y/n): ").lower()
        if answer == "y":
            for article in failed_articles:
                success = download_article(article, format="pdf", folder="output")
                if not success:
                    print(f"Also failed to download PDF for: {article['title']}")
        else:
            print("Skipping papers without HTML version.")

    gathered_metadata = comm.gather(local_articles, root=0)

    if rank == 0:
        all_articles = [item for sublist in gathered_metadata for item in sublist][:amount]
        if len(all_articles) == 0:
            print(
                f"\033[31mNo result for: \"{query}\". Check grammar or use a more general term.\033[0m")
            return
        save_metadata(all_articles)
        print(f"\033[35mMetadata saved and files downloaded in \"output\" folder\033[0m")


if __name__ == "__main__":
    start = time.time()
    main()
    end = time.time()

    # Print time ( for analysis )
    if rank == 0:
        print(f"Total time: {end - start:.2f} seconds")
