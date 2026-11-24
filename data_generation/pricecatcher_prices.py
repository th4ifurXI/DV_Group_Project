"""
Match the shop's products to real prices from KPDN PriceCatcher (open.dosm.gov.my / data.gov.my).

Input (download from https://open.dosm.gov.my/data-catalogue/pricecatcher, not stored in the repo):
  pricecatcher_2026-11.parquet, lookup_item.csv, lookup_premise.csv
Output:
  data/reference/pricecatcher_perak_2026-11.csv - median November 2026 price of each matched item across
  mini-markets, grocery shops and supermarkets in Perak, converted to the shop's pack size.

Run:  python data_generation/pricecatcher_prices.py <folder with the three PriceCatcher files>
"""

import sys
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "reference" / "pricecatcher_perak_2026-11.csv"
SHOP_TYPES = ["Pasar Mini", "Kedai Runcit", "Pasar Raya / Supermarket"]

# shop product name -> (PriceCatcher item_code, pack factor = shop pack / PriceCatcher pack)
MATCH = {
    "Beras Wangi 5kg": (2068, 0.5),                 # Beras Cap Jasmine Super 5 Special 10 kg
    "Beras Super Tempatan 10kg": (992, 1),          # Beras Cap Jati 10 kg
    "Oat Segera 500g": (1964, 0.5),                 # Quaker Oats Instant 1 kg
    "Bihun 400g": (1584, 1),                        # Bihun kering tempatan 400 g
    "Minyak Masak 5kg": (1939, 1),                  # Minyak masak tulen Cap Saji 5 kg
    "Minyak Masak Paket 1kg": (918, 1),
    "Gula Pasir 1kg": (1589, 1),
    "Tepung Gandum 1kg": (917, 1),
    "Garam Halus 350g": (1605, 1),
    "Kicap Manis 345ml": (214, 1),
    "Sos Cili 340g": (1070, 1),
    "Serbuk Kari Daging 250g": (1572, 1),
    "Santan Kotak 200ml": (1611, 1),
    "Bawang Merah 1kg": (131, 1),
    "Bawang Putih 500g": (1564, 0.5),
    "Mi Segera Kari 5x79g": (1976, 1),
    "Sardin Tin 425g": (193, 1),
    "Milo Serbuk 900g": (2114, 1),
    "Teh 100 Uncang": (180, 1),
    "Kopi 3 dalam 1 25 paket": (2019, 1),
    "100 Plus 1.5L": (1355, 1),
    "Coca-Cola 320ml": (1507, 1),
    "Kordial Oren 2L": (910, 1),
    "Jus Oren 1L": (235, 1),
    "Telur Gred A 30 biji": (1109, 1),
    "Telur Gred C 10 biji": (1111, 1 / 3),
    "Susu Segar 1L": (224, 1),
    "Krimer Manis Pekat 500g": (883, 1),
    "Yogurt Strawberi 130g": (1955, 1),
    "Mentega 227g": (1615, 1),
    "Ayam Bersih 1kg": (1, 1),
    "Sayur Sawi 500g": (1558, 0.5),
    "Tomato 500g": (114, 0.5),
    "Cili Merah 200g": (94, 0.2),
    "Pisang Berangan 1kg": (18, 1),
    "Kentang 1kg": (1131, 1),
    "Limau Kasturi 250g": (1928, 0.25),
    "Sabun Cuci Pinggan 800ml": (2112, 1),
    "Serbuk Pencuci 2.1kg": (2109, 1),
    "Pelembut Fabrik 800ml": (1876, 1),
    "Syampu 330ml": (1984, 1),
    "Sabun Mandi Cecair 920ml": (2102, 1),
    "Ubat Gigi 250g": (292, 1),
    "Berus Gigi": (1524, 1),
    "Deodoran Roll-On 50ml": (1990, 1),
}


def main(folder):
    folder = Path(folder)
    prices = pd.read_parquet(folder / "pricecatcher_2026-11.parquet")
    items = pd.read_csv(folder / "lookup_item.csv")
    shops = pd.read_csv(folder / "lookup_premise.csv")
    shops = shops[(shops.state == "Perak") & shops.premise_type.str.strip().isin(SHOP_TYPES)]
    p = prices[prices.premise_code.isin(shops.premise_code)]
    stats = p.groupby("item_code").agg(median_price_rm=("price", "median"), shops=("premise_code", "nunique"),
                                       observations=("price", "size"))
    rows = []
    for name, (code, factor) in MATCH.items():
        it = items.set_index("item_code").loc[code]
        st = stats.loc[code]
        rows.append(dict(product_name=name, item_code=code, pricecatcher_item=it["item"], pricecatcher_unit=it["unit"],
                         perak_median_rm=round(st.median_price_rm, 2), perak_shops=int(st.shops),
                         observations=int(st.observations), pack_factor=round(factor, 4),
                         shop_price_rm=round(st.median_price_rm * factor, 2)))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False)
    print(f"{len(out)} products matched using {len(shops)} Perak shops, {len(p):,} price records -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
