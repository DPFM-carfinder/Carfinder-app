import re
from concurrent.futures import ThreadPoolExecutor, as_completed

import cloudscraper
import requests
from bs4 import BeautifulSoup


import json
import os
import logging
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

with open("data.json", encoding="utf-8") as f:
    D = json.load(f)


@app.route("/")
def home():
    return send_file("index.html")


@app.route("/api/data")
def api_data():
    return jsonify(D)

TURBO_MAKES = D["turbo_makes"]
TURBO_MAKE_MODELS = D["turbo_make_models"]
TURBO_COLORS = D["turbo_colors"]

AZE_CITIES = D["cities"]

AB_MAKES = D["ab_makes"]
AB_MAKE_MODELS = D["ab_make_models"]
AB_CITIES = D["ab_cities"]
AB_COLORS = D["ab_colors"]

TURBO_TO_BAKU_CITY = D["turbo_to_baku_city"]

scraper = cloudscraper.create_scraper()


def build_turbo_url(
    make="",
    model="",
    price_from="",
    price_to="",
    color="",
    city="",
    page=1,
    **kw,
):
    make_num = TURBO_MAKES.get(make, "")
    model_num = TURBO_MAKE_MODELS.get(make, {}).get(model, "") if model else ""

    parts = ["https://turbo.az/autos?q%5Bsort%5D="]

    if make_num:
        parts.append(f"q%5Bmake%5D%5B%5D={make_num}")

    if model_num:
        parts.append(f"q%5Bmodel%5D%5B%5D={model_num}")

    if city:
        parts.append(f"q%5Bregion%5D%5B%5D={city}")

    if price_from:
        parts.append(f"q%5Bprice_from%5D={price_from}")

    if price_to:
        parts.append(f"q%5Bprice_to%5D={price_to}")

    parts.extend([
        "q%5Bused%5D=",
        "q%5Bcurrency%5D=azn",
        "q%5Bloan%5D=0",
        "q%5Bbarter%5D=0",
        "q%5Bcategory%5D%5B%5D=",
        "q%5Byear_from%5D=",
        "q%5Byear_to%5D=",
    ])

    color_id = TURBO_COLORS.get(color, "")

    if color_id:
        parts.append(f"q%5Bcolor%5D%5B%5D={color_id}")

    parts.extend([
        "q%5Bgear%5D%5B%5D=",
        "q%5Btransmission%5D%5B%5D=",
        "q%5Bengine_volume_from%5D=",
        "q%5Bengine_volume_to%5D=",
        "q%5Bpower_from%5D=",
        "q%5Bpower_to%5D=",
        "q%5Bmileage_from%5D=",
        "q%5Bmileage_to%5D=",
        "q%5Bonly_shops%5D=",
        "q%5Bprior_owners_count%5D%5B%5D=",
        "q%5Bseats_count%5D%5B%5D=",
        "q%5Bmarket%5D%5B%5D=",
        "q%5Bcrashed%5D=1",
        "q%5Bpainted%5D=1",
        "q%5Bfor_spare_parts%5D=0",
        "q%5Bavailability_status%5D=",
    ])

    if int(page) > 1:
        parts.append(f"page={page}")

    return "&".join(parts)


def build_baku_url(
    make="",
    model="",
    price_from="",
    price_to="",
    color="",
    city="",
    page=1,
    **kw,
):
    make_num = AB_MAKES.get(make, "")
    model_num = AB_MAKE_MODELS.get(make, {}).get(model, "") if model else ""
    color_id = AB_COLORS.get(color, "")

    parts = [
        "https://www.avtobaku.com/buy-cars?utf8=%E2%9C%93",
        "listing%5Border_by%5D=",
        "listing%5Bsold%5D=0",
    ]

    if make_num:
        parts.append(f"listing%5Bbrand_id%5D={make_num}")

    parts.append(f"listing%5Bmodel_id%5D={model_num or '%20'}")

    parts.extend([
        f"listing%5Bminprice%5D={price_from or 167}",
        f"listing%5Bmaxprice%5D={price_to or 503709}",
        "listing%5Bminyear%5D=1950",
        "listing%5Bmaxyear%5D=2026",
    ])

    parts.append("listing%5Bcity_id%5D%5B%5D=")

    if city:
        parts.append(f"listing%5Bcity_id%5D%5B%5D={city}")

    parts.extend([
        "listing%5Bcar_type%5D=",
        "listing%5Bcar_type%5D=car",
        "listing%5Bbody_id%5D=%20",
        "listing%5Bgear_type%5D=",
        "listing%5Bgear_type%5D=",
        "listing%5Bfuel_id%5D=",
        "listing%5Bminmileage%5D=",
        "listing%5Bmaxmileage%5D=",
    ])

    parts.append("listing%5Bcolor%5D%5B%5D=")

    if color_id:
        parts.append(f"listing%5Bcolor%5D%5B%5D={color_id}")

    if int(page) > 1:
        parts.append(f"page={page}")

    return "&".join(parts)


def build_baku_url_universal(
    make="",
    model="",
    price_from="",
    price_to="",
    color="",
    city_name="",
    page=1,
    **kw,
):
    baku_city_name = TURBO_TO_BAKU_CITY.get(city_name, "")
    baku_city_id = AB_CITIES.get(baku_city_name, "")

    return build_baku_url(
        make=make,
        model=model,
        price_from=price_from,
        price_to=price_to,
        color=color,
        city=baku_city_id,
        page=page,
    )


def matches_search(title, make="", model=""):
    title = (title or "").lower().strip()

    if make:
        make = make.lower().strip()
        if make not in title:
            return False

    if model:
        model = model.lower().strip()

        if model:
            model_words = model.split()

            if not all(word in title for word in model_words):
                return False

    return True


def get_total_pages(soup):
    for pag in soup.find_all(
        ["div", "ul", "nav"],
        class_=re.compile(r"paginat", re.I),
    ):
        nums = [
            int(a.get_text(strip=True))
            for a in pag.find_all("a", href=True)
            if a.get_text(strip=True).isdigit()
        ]

        if nums:
            return max(nums)

    return 1


def scrape_turbo(url, make="", model=""):
    try:
        resp = scraper.get(url, timeout=(5, 15))
    except Exception as e:
        raise RuntimeError(f"Turbo.az request failed: {e}")

    if resp.status_code != 200:
        raise RuntimeError(f"Turbo.az HTTP {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")

    listing_re = re.compile(r"^/autos/\d+(-[^/]*)?$")
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].rstrip("/")

        if not listing_re.match(href):
            continue

        full_url = "https://turbo.az" + href

        if full_url in seen:
            continue

        seen.add(full_url)

        title = ""
        parent = a

        for _ in range(4):
            parent = getattr(parent, "parent", None)

            if not parent:
                break

            for cls in (
                "products-i__name",
                "product-name",
                "products-i__title",
                "name",
            ):
                node = parent.find(class_=cls)

                if node:
                    title = node.get_text(" ", strip=True)[:80]
                    break

            if title:
                break

        if not title:
            parts = href.split("/")[-1].split("-")
            title = (
                " ".join(parts[1:]).title()
                if len(parts) > 1
                else href.split("/")[-1]
            )

        if not matches_search(title, make, model):
            continue

        results.append({
            "url": full_url,
            "title": title,
            "source": "turbo",
        })

    return results, get_total_pages(soup)


def scrape_baku(url, make="", model=""):
    try:
        resp = scraper.get(url, timeout=(10, 20))
    except Exception as e:
        raise RuntimeError(f"AvtoBaku request failed: {e}")

    logging.info(f"AvtoBaku status: {resp.status_code}")

    if resp.status_code != 200:
        raise RuntimeError(f"AvtoBaku HTTP {resp.status_code}")

    soup = BeautifulSoup(resp.text, "html.parser")

    listing_re = re.compile(r"^/(en/)?vehicle_listings/[^/]+$")
    results = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").split("?")[0].rstrip("/")

        if not href or not listing_re.match(href):
            continue

        full_url = "https://www.avtobaku.com" + href

        if full_url in seen:
            continue

        seen.add(full_url)

        title = ""

        h4 = a.find("h4")
        if h4:
            title = h4.get_text(" ", strip=True)

        if not title:
            parent = a

            for _ in range(5):
                parent = getattr(parent, "parent", None)

                if not parent:
                    break

                h4 = parent.find("h4")

                if h4:
                    title = h4.get_text(" ", strip=True)
                    break

        if not title:
            slug = href.split("/")[-1]
            title = slug.replace("-", " ").replace("_", " ").title()

        if not matches_search(title, make, model):
            continue

        results.append({
            "url": full_url,
            "title": title,
            "source": "baku",
        })

    logging.info(f"AvtoBaku results: {len(results)}")

    return results, get_total_pages(soup)


@app.route("/api/search", methods=["GET"])
def search():
    source = request.args.get("source", "turbo")

    params = dict(request.args)
    params["page"] = int(params.get("page", 1))

    logging.info(f"Search: source={source} params={params}")

    try:
        if source == "turbo":
            url = build_turbo_url(**params)

            listings, total_pages = scrape_turbo(
                url,
                params.get("make", ""),
                params.get("model", ""),
            )

            return jsonify({
                "ok": True,
                "source": "turbo",
                "search_url": url,
                "page": params["page"],
                "total_pages": total_pages,
                "count": len(listings),
                "listings": listings,
            })

        elif source == "baku":
            url = build_baku_url(**params)

            listings, total_pages = scrape_baku(
                url,
                params.get("make", ""),
                params.get("model", ""),
            )

            return jsonify({
                "ok": True,
                "source": "baku",
                "search_url": url,
                "page": params["page"],
                "total_pages": total_pages,
                "count": len(listings),
                "listings": listings,
            })

        elif source == "universal":
            city_name = ""

            if params.get("city"):
                city_name = next(
                    (n for n, v in AZE_CITIES.items() if v == params["city"]),
                    "",
                )

            turbo_url = build_turbo_url(**params)
            baku_url = build_baku_url_universal(
                city_name=city_name,
                **params,
            )

            turbo_result = {
                "listings": [],
                "total_pages": 1,
                "error": None,
                "url": turbo_url,
            }

            baku_result = {
                "listings": [],
                "total_pages": 1,
                "error": None,
                "url": baku_url,
            }

            def run_turbo():
                try:
                    listings, pages = scrape_turbo(
                        turbo_url,
                        params.get("make", ""),
                        params.get("model", ""),
                    )

                    turbo_result["listings"] = listings
                    turbo_result["total_pages"] = pages

                except Exception as e:
                    turbo_result["error"] = str(e)

            def run_baku():
                try:
                    listings, pages = scrape_baku(
                        baku_url,
                        params.get("make", ""),
                        params.get("model", ""),
                    )

                    baku_result["listings"] = listings
                    baku_result["total_pages"] = pages

                except Exception as e:
                    baku_result["error"] = str(e)

            with ThreadPoolExecutor(max_workers=2) as ex:
                futures = [
                    ex.submit(run_turbo),
                    ex.submit(run_baku),
                ]

                for _ in as_completed(futures):
                    pass

            t = turbo_result["listings"]
            b = baku_result["listings"]

            interleaved = []

            for i in range(max(len(t), len(b))):
                if i < len(t):
                    interleaved.append(t[i])

                if i < len(b):
                    interleaved.append(b[i])

            return jsonify({
                "ok": True,
                "source": "universal",
                "page": params["page"],
                "turbo_url": turbo_url,
                "baku_url": baku_url,
                "turbo_count": len(t),
                "baku_count": len(b),
                "turbo_pages": turbo_result["total_pages"],
                "baku_pages": baku_result["total_pages"],
                "turbo_error": turbo_result["error"],
                "baku_error": baku_result["error"],
                "count": len(interleaved),
                "listings": interleaved,
            })

        return jsonify({
            "ok": False,
            "error": f"Unknown source: {source}",
        }), 400

    except Exception as e:
        return jsonify({
            "ok": False,
            "error": str(e),
        }), 500


@app.route("/api/url", methods=["GET"])
def get_url():
    source = request.args.get("source", "turbo")

    params = dict(request.args)

    fn = {
        "turbo": build_turbo_url,
        "baku": build_baku_url,
    }.get(source, build_turbo_url)

    return jsonify({
        "url": fn(**params),
        "source": source,
    })


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "turbo_makes": len(TURBO_MAKES),
        "ab_makes": len(AB_MAKES),
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        threaded=True,
    )
