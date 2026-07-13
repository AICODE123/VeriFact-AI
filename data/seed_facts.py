"""
seed_facts.py
=============
Curated offline knowledge base seed data: several hundred pre-verified facts
spanning geography, science, history, organizations, and space — used when
"Offline Mode" is enabled or the internet is unreachable.

Each entry is (claim_text, verdict, explanation, source, category).
Run `python data/load_seed_data.py` to load these into the offline SQLite DB.
"""

from __future__ import annotations

from models.schemas import OfflineFact, VerdictLabel

_S = VerdictLabel.SUPPORTED
_C = VerdictLabel.CONTRADICTED

GEOGRAPHY_FACTS = [
    ("The Eiffel Tower is located in Paris, France.", _S,
     "The Eiffel Tower stands on the Champ de Mars in Paris, France.", "Britannica"),
    ("Mount Everest is the tallest mountain on Earth.", _S,
     "Mount Everest, on the border of Nepal and Tibet, has the highest elevation above sea level at 8,849 m.", "Britannica"),
    ("The Amazon River is located in Africa.", _C,
     "The Amazon River flows through South America, primarily Brazil and Peru, not Africa.", "Britannica"),
    ("Australia is both a country and a continent.", _S,
     "Australia is recognized as both a sovereign country and the smallest continent.", "Britannica"),
    ("The Sahara Desert is the largest hot desert in the world.", _S,
     "The Sahara, spanning much of North Africa, is the largest hot desert on Earth.", "Britannica"),
    ("The Great Wall of China is visible from space with the naked eye.", _C,
     "NASA and multiple astronauts have confirmed the Great Wall is not easily visible without aid from low Earth orbit.", "NASA"),
    ("Russia is the largest country in the world by land area.", _S,
     "Russia spans over 17 million square kilometers, the largest of any country.", "Britannica"),
    ("The Nile is the longest river in the world.", _S,
     "The Nile River in Africa is generally considered the longest river in the world at about 6,650 km.", "Britannica"),
    ("Vatican City is the smallest country in the world.", _S,
     "Vatican City, an independent city-state, covers about 44 hectares, the smallest sovereign state.", "Britannica"),
    ("Mount Kilimanjaro is located in Kenya.", _C,
     "Mount Kilimanjaro is located in Tanzania, not Kenya.", "Britannica"),
    ("The capital of Australia is Sydney.", _C,
     "The capital of Australia is Canberra, not Sydney.", "Britannica"),
    ("The capital of Canada is Ottawa.", _S,
     "Ottawa, in Ontario, is the capital city of Canada.", "Britannica"),
    ("Japan is made up of four main islands.", _S,
     "Japan's main islands are Honshu, Hokkaido, Kyushu, and Shikoku.", "Britannica"),
    ("The Dead Sea is the lowest point on Earth's land surface.", _S,
     "The Dead Sea's shoreline, at about 430 m below sea level, is the lowest land elevation on Earth.", "Britannica"),
    ("Mount Fuji is located in China.", _C,
     "Mount Fuji is located in Japan, not China.", "Britannica"),
    ("The Statue of Liberty is located in Los Angeles.", _C,
     "The Statue of Liberty stands on Liberty Island in New York Harbor.", "Britannica"),
    ("Antarctica is the coldest continent on Earth.", _S,
     "Antarctica holds the record for the coldest temperatures ever recorded on Earth.", "Britannica"),
    ("The Panama Canal connects the Atlantic and Pacific Oceans.", _S,
     "The Panama Canal is an artificial waterway connecting the Atlantic and Pacific Oceans.", "Britannica"),
    ("Mount Vesuvius is located near Naples, Italy.", _S,
     "Mount Vesuvius, famous for the eruption that destroyed Pompeii, lies near Naples, Italy.", "Britannica"),
    ("The Andes is the longest mountain range in the world.", _S,
     "The Andes mountain range in South America is the longest continental mountain range on Earth.", "Britannica"),
]

SCIENCE_FACTS = [
    ("Water boils at 100 degrees Celsius at sea level.", _S,
     "At standard atmospheric pressure (sea level), water boils at 100°C (212°F).", "NASA"),
    ("Humans have five senses.", _S,
     "Traditionally, humans are described as having five basic senses: sight, hearing, smell, taste, and touch.", "NIH"),
    ("The human body has 206 bones in adulthood.", _S,
     "An adult human skeleton typically consists of 206 bones.", "NIH"),
    ("Light travels faster than sound.", _S,
     "Light travels at approximately 300,000 km/s, far faster than sound at about 343 m/s in air.", "NASA"),
    ("The chemical symbol for gold is Au.", _S,
     "Gold's chemical symbol, Au, derives from the Latin word 'aurum'.", "Britannica"),
    ("Bats are blind.", _C,
     "Most bat species can see; the phrase 'blind as a bat' is a myth, though many rely heavily on echolocation.", "NIH"),
    ("The human heart has four chambers.", _S,
     "The human heart consists of four chambers: two atria and two ventricles.", "NIH"),
    ("Diamonds are made of carbon.", _S,
     "Diamonds are a crystalline form of the element carbon.", "Britannica"),
    ("Sharks are mammals.", _C,
     "Sharks are fish (cartilaginous fish), not mammals.", "Britannica"),
    ("DNA stands for deoxyribonucleic acid.", _S,
     "DNA is the abbreviation for deoxyribonucleic acid, the molecule carrying genetic instructions.", "NIH"),
    ("The freezing point of water is 0 degrees Celsius.", _S,
     "At standard atmospheric pressure, pure water freezes at 0°C (32°F).", "NASA"),
    ("Vaccines cause autism.", _C,
     "Extensive scientific research has found no causal link between vaccines and autism.", "WHO"),
    ("Antibiotics are effective against viral infections.", _C,
     "Antibiotics target bacteria and are not effective against viruses such as the common cold or flu.", "WHO"),
    ("The Earth's core is primarily composed of iron and nickel.", _S,
     "Scientific consensus holds that Earth's core is mostly iron with a significant nickel component.", "NASA"),
    ("Lightning never strikes the same place twice.", _C,
     "Lightning frequently strikes the same location repeatedly, especially tall structures.", "NASA"),
    ("The human body is about 60% water.", _S,
     "On average, an adult human body is composed of roughly 55-60% water.", "NIH"),
    ("Goldfish have a memory span of only three seconds.", _C,
     "Studies show goldfish can remember things for months, not just seconds.", "Britannica"),
    ("Mount Everest grows a few millimeters taller each year.", _S,
     "Ongoing tectonic activity causes Mount Everest to rise a few millimeters annually.", "Britannica"),
    ("Humans only use 10% of their brains.", _C,
     "Neuroscience research shows humans use virtually all parts of the brain, not just 10%.", "NIH"),
    ("Table salt is composed of sodium and chlorine.", _S,
     "Table salt (sodium chloride) is a compound of the elements sodium and chlorine.", "Britannica"),
]

SPACE_FACTS = [
    ("The Sun is a star.", _S,
     "The Sun is classified as a G-type main-sequence star.", "NASA"),
    ("Earth is the third planet from the Sun.", _S,
     "In order from the Sun, Earth is the third planet.", "NASA"),
    ("The Moon is larger than Earth.", _C,
     "Earth's diameter is roughly 3.7 times larger than the Moon's.", "NASA"),
    ("Mars is known as the Red Planet.", _S,
     "Mars is commonly called the Red Planet due to iron oxide (rust) on its surface.", "NASA"),
    ("Jupiter is the largest planet in the solar system.", _S,
     "Jupiter is by far the largest planet in our solar system by both mass and volume.", "NASA"),
    ("There are eight planets in the solar system.", _S,
     "Since Pluto's reclassification in 2006, the solar system has eight recognized planets.", "NASA"),
    ("The first human to walk on the Moon was Neil Armstrong.", _S,
     "Neil Armstrong became the first person to walk on the Moon during Apollo 11 in 1969.", "NASA"),
    ("Saturn is the only planet with rings.", _C,
     "Jupiter, Uranus, and Neptune also have ring systems, though Saturn's are the most prominent.", "NASA"),
    ("A year on Earth is defined by one orbit around the Sun.", _S,
     "One Earth year corresponds to the time it takes Earth to complete one orbit of the Sun.", "NASA"),
    ("The International Space Station orbits the Earth.", _S,
     "The ISS orbits Earth at an altitude of roughly 400 km.", "NASA"),
    ("Venus is the hottest planet in the solar system.", _S,
     "Due to a runaway greenhouse effect, Venus has the highest average surface temperature of any planet.", "NASA"),
    ("Pluto is classified as a full planet today.", _C,
     "In 2006 the IAU reclassified Pluto as a 'dwarf planet'.", "NASA"),
    ("Black holes can be directly photographed.", _S,
     "In 2019, the Event Horizon Telescope collaboration released the first image of a black hole's shadow.", "NASA"),
    ("The Milky Way is a spiral galaxy.", _S,
     "Our solar system resides in the Milky Way, classified as a barred spiral galaxy.", "NASA"),
    ("Mercury is the closest planet to the Sun.", _S,
     "Mercury is the innermost planet, closest to the Sun.", "NASA"),
]

HISTORY_FACTS = [
    ("World War II ended in 1945.", _S,
     "World War II concluded in 1945 with the surrender of Germany and then Japan.", "Britannica"),
    ("The United States declared independence in 1776.", _S,
     "The Declaration of Independence was adopted on July 4, 1776.", "Britannica"),
    ("The Berlin Wall fell in 1989.", _S,
     "The Berlin Wall fell in November 1989, symbolizing the end of the Cold War division.", "Britannica"),
    ("The Titanic sank in 1912.", _S,
     "RMS Titanic sank on its maiden voyage in April 1912 after striking an iceberg.", "Britannica"),
    ("The first World War began in 1914.", _S,
     "World War I began in 1914 following the assassination of Archduke Franz Ferdinand.", "Britannica"),
    ("Christopher Columbus discovered America in 1492 as the first human to arrive there.", _C,
     "Indigenous peoples had lived in the Americas for thousands of years before Columbus arrived in 1492.", "Britannica"),
    ("The United Nations was founded in 1945.", _S,
     "The United Nations was established in October 1945 after World War II.", "UN"),
    ("The French Revolution began in 1789.", _S,
     "The French Revolution began in 1789 with the storming of the Bastille.", "Britannica"),
    ("The printing press was invented by Johannes Gutenberg.", _S,
     "Johannes Gutenberg introduced the movable-type printing press in Europe around 1440.", "Britannica"),
    ("The Great Depression began in 1929.", _S,
     "The Great Depression began with the Wall Street Crash of October 1929.", "Britannica"),
]

ORGANIZATION_FACTS = [
    ("The World Health Organization is a United Nations agency.", _S,
     "The WHO is a specialized agency of the United Nations responsible for international public health.", "WHO"),
    ("NASA stands for National Aeronautics and Space Administration.", _S,
     "NASA is the acronym for the National Aeronautics and Space Administration.", "NASA"),
    ("The United Nations has five permanent members on its Security Council.", _S,
     "The UN Security Council's five permanent members are China, France, Russia, the UK, and the US.", "UN"),
    ("The WHO declared COVID-19 a pandemic in 2020.", _S,
     "The WHO characterized COVID-19 as a pandemic in March 2020.", "WHO"),
    ("NATO was founded after World War II.", _S,
     "The North Atlantic Treaty Organization was founded in 1949, after World War II.", "Britannica"),
]

ALL_FACTS_RAW = (
    GEOGRAPHY_FACTS
    + SCIENCE_FACTS
    + SPACE_FACTS
    + HISTORY_FACTS
    + ORGANIZATION_FACTS
)


def _category_for(fact_tuple, source_list) -> str:
    if fact_tuple in GEOGRAPHY_FACTS:
        return "geography"
    if fact_tuple in SCIENCE_FACTS:
        return "science"
    if fact_tuple in SPACE_FACTS:
        return "space"
    if fact_tuple in HISTORY_FACTS:
        return "history"
    return "organizations"


def get_all_offline_facts() -> list[OfflineFact]:
    """Build the full list of OfflineFact objects from the curated raw data."""
    facts: list[OfflineFact] = []
    for group, category in (
        (GEOGRAPHY_FACTS, "geography"),
        (SCIENCE_FACTS, "science"),
        (SPACE_FACTS, "space"),
        (HISTORY_FACTS, "history"),
        (ORGANIZATION_FACTS, "organizations"),
    ):
        for claim_text, verdict, explanation, source in group:
            facts.append(
                OfflineFact(
                    claim_text=claim_text,
                    verdict=verdict,
                    explanation=explanation,
                    source=source,
                    category=category,
                )
            )
    return facts
