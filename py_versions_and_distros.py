import requests
import os
import csv
from datetime import datetime
from bs4 import BeautifulSoup


CSV_FIELDNAMES = ['distribution', 'dist_version', 'python_version', 'resource']
PY_3_6_VERSIONS = ["3.6.2",
                   "3.6.1",
                   "3.6.0"]


def fetch_webpage(source_url, destination_filename):
    """
    Download <source_url> and save it as <destination_filename>
    """
    r = requests.get(source_url)
    with open(destination_filename, 'w+') as file:
        file.write(r.text)


def scrape_webpage(source_url, destination_filename):
    """
    Check if we have downloaded <source_url> today.
    If not yet, then download it
    """
    if not os.path.exists(destination_filename):
        fetch_webpage(source_url, destination_filename)

    mod_date = datetime.fromtimestamp(
        os.path.getmtime(destination_filename))
    if mod_date.date() < datetime.today().date():
        fetch_webpage(source_url, destination_filename)

def get_distros():
    """
    Parse distrowatch.html, find the select element with name 'distribution'
    and return all the options.
    """
    with open("downloaded_data/distrowatch.html") as fp:
        soup = BeautifulSoup(fp, "html.parser")
        one = soup.select_one("select[name=distribution]")
        for item in filter(lambda x: x['value'], one.find_all("option")):
            yield item['value']


def process_distro(distribution):
    """
    Parse <distribution>.html, look for "Full Package List" table.
    The package release version is listed in that table.
    :param distribution:
    :return:
    """
    with open(f"downloaded_data/{distribution}.html") as file:
        soup = BeautifulSoup(file, "html.parser")
        th = soup.find_all("th", text="Full Package List")
        if th:
            for sib in th[0].next_siblings:
                a_elem = sib.find("a")
                if a_elem and a_elem != -1:
                    process_resource(distribution, a_elem.text)


def process_resource(distribution, dist_version):
    """
    Download the resources at
    https://distrowatch.com/resource/{distribution}/{distribution}-{dist_version}.txt
    It lists all the packaged shipped for the specified distribution and release.

    Python 3.6 is possibly identified using one of the following patterns:
    These are only my own guess and assumption.

        python3 3.6*    e.g. antergos 17.6: python 3.6.1-1
        python3^3.6*    e.g. kaos 2017.07: python3^3.6.1-1
        python3-3.6*    e.g. fedora 26: python3-3.6.1-8.fc26.x86_64
        python 3.6*     e.g. gentoo unstable: python 3.6.1
        python-3.6*     e.g arch current: python-3.6.2-1-i686.pkg.tar.xz
        python3.6*      e.g parrotsecurity 3.7: python3.6^3.6.2~rc1-1
    """
    resource_url = f"https://distrowatch.com/resource/{distribution}/{distribution}-{dist_version}.txt"
    resource_file_path = f"downloaded_resources_data/{distribution}-{dist_version}.txt"

    scrape_webpage(resource_url, resource_file_path)

    with open(resource_file_path) as file:
        for line in file.readlines():
            if line.startswith("python3 3.6") or line.startswith("python3^3.6") \
                    or line.startswith("python3-3.6") or line.startswith("python3.6") \
                    or line.startswith("python 3.6") or line.startswith("python-3.6"):
                version = None
                for v in PY_3_6_VERSIONS:
                    if v in line:
                        version = v

                if version:
                    write_output({"distribution": distribution,
                                   "dist_version": dist_version,
                                   "python_version": version,
                                   "resource": line.strip()})
                    return


def init_csv():
    """
    Clean up the output csv (python_distros.csv)
    Create the output csv file, along with the headers
    """
    if os.path.exists("python_distros.csv"):
        os.remove("python_distros.csv")

    with open("python_distros.csv", 'a') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES)
        writer.writeheader()


def write_output(dist_json):
    """
    Write a line to python_distros.csv
    """
    with open("python_distros.csv", 'a') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=CSV_FIELDNAMES)
        writer.writerow(dist_json)


def print_report():
    """
    Print to terminal the distributions that have python 3.6
    """
    with open("python_distros.csv") as file:
        csvreader = csv.DictReader(file, fieldnames=CSV_FIELDNAMES)
        count = 0
        for row in csvreader:
            if count > 0:
                print(f"{row['distribution']} {row['dist_version']}: Python {row['python_version']}")
            count += 1
        print("="*36)
        print(f"{count-1} distros with Python 3.6")

def main():
    init_csv()
    scrape_webpage('https://distrowatch.com/', "downloaded_data/distrowatch.html")
    for distro in get_distros():
        distro_url = f"https://distrowatch.com/table-mobile.php?distribution={distro}"
        dest_filename = f"downloaded_data/{distro}.html"
        scrape_webpage(distro_url, dest_filename)
        process_distro(distro)

    print_report()

if __name__ == "__main__":
    main()
