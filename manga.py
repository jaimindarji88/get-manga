#!/usr/bin/python3.6

from lxml import html
import requests
import shutil
import os
from tqdm import tqdm
from multiprocessing import Pool, cpu_count
import argparse

import zipfile

HEADERS = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'accept-language': 'en-US,en;q=0.9,fr;q=0.8',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36'
}


def get_url(search, debug=False):
    p_search = search.replace(' ', '_')

    r = requests.get(
        f'https://manganelo.com/search/{p_search}', headers=HEADERS
    )
    body = html.fromstring(r.text)
    results = body.xpath('//div[@class="story_item"]')

    if r.status_code != 200:
        raise Exception("Unable to get the server")

    for res in results:
        name = res.xpath('.//h3//text()')
        url = res.xpath('.//a/@href')[0]

        name = next(filter(lambda x: x.strip(), name))
        if not name:
            raise Exception('Couldnt find the manga' + search)
        while True:
            print('Is this the name of the manga? [y,n]')
            inp = input(name+'\n')
            if inp == 'y':
                return name, url
            elif inp == 'n':
                break

    if debug:
        with open('a.html', 'w') as f:
            f.write(r.text)
    raise Exception('couldnt find any results')


def get_chapter(m_c):
    manga, chapter_url = m_c

    chapter = chapter_url.split('/')[-1]

    req = requests.get(chapter_url, headers=HEADERS)
    body = html.fromstring(req.text)
    images = body.xpath('//div[@class="vung-doc"]//img//@src')

    if not os.path.isdir(manga):
        os.mkdir(manga)

    chapter_path = os.path.join(manga, chapter)
    if not os.path.isdir(chapter_path):
        os.mkdir(chapter_path)

    for image in images:
        page = image.split(os.path.sep)[-1].split('.')[0]

        r = requests.get(image, stream=True, headers=HEADERS)

        page_path = os.path.join(
            os.getcwd(),
            chapter_path,
            f'{page}.jpg'
        )

        with open(page_path, 'wb') as f:
            r.raw.decode_content = True
            shutil.copyfileobj(r.raw, f)

    print('done', chapter)


def get_manga(manga_name='manga', u='', processes=4):
    if u:
        url = u
    else:
        manga_name, url = get_url(manga_name)

    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    r = requests.get(url)

    body = html.fromstring(r.text)

    chapters = body.xpath('//div[contains(@class, "chapter-list")]//@href')
    chapters = list(map(lambda x: (manga_name, x), chapters))

    with Pool(processes) as p:
        p.map(get_chapter, chapters)

    print('done getting all chapters')
    return manga_name


def zip_folder(folder: str):
    chapter = folder.split(os.path.sep)[-1].replace('.', '-')

    with zipfile.ZipFile(f'{chapter}.cbz', 'w', zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for f in files:
                z.write(
                    os.path.relpath(os.path.join(root, f)),
                    arcname=f
                )


def zip_manga(manga_name, base_dir=os.getcwd(), delete=True, processes=4):
    directory = os.path.join(base_dir, manga_name)
    os.chdir(directory)

    _, chapters, _ = next(os.walk(directory))

    c_count = cpu_count()
    if processes >= c_count:
        processes = c_count - 2

    with Pool(processes) as p:
        p.map(zip_folder, chapters)

    print('done zipping files')
    if delete:
        for chapter in tqdm(chapters):
            shutil.rmtree(chapter)
        print('deleted the files')


def main():
    parser = argparse.ArgumentParser(description='Gets manga')

    parser.add_argument('Name', metavar='N', type=str,
                        help='Name of the manga')
    parser.add_argument(
        '-d', type=bool, help='Delete the image folders [default = True]', default=True
    )
    parser.add_argument(
        '-u', type=str, help='url youd like to download from', default=''
    )
    parser.add_argument(
        '-p', type=int, help='number of processors to use', default=4
    )
    parser.add_argument(
        '-z', type=bool, default=False, help='Zip the chapters in cbz format for manga name'
    )
    args = parser.parse_args()

    if args.z:
        return zip_manga(args.Name)

    manga_name = get_manga(manga_name=args.Name, processes=args.p)
    zip_manga(manga_name, processes=args.p)


if __name__ == '__main__':
    main()
