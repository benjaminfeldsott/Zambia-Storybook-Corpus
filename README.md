# Zambia-Storybook-Corpus
The Zambia Storybook Corpus is a structured, bilingual parallel dataset of classic children's literature in Zambian languages: Icibemba, Chinyanja, Sitonga, and Silozi. I worked with Zambian translators to produce this project to inspire educators and learners worldwide. I hope these translations will be published along with many others someday.

Developed as part of an independent non-profit initiative for educational equity by Books & Friends Publishing House Inc., this corpus aligns English public domain source texts—such as The Tale of Peter Rabbit, Hansel and Gretel, and Little Red Riding-Hood—with their respective translations in four major Zambian languages: Icibemba, Chinyanja, Silozi, and Chitonga.

## Data Structure

The corpus has been computationally extracted from foundational `.docx` translation manuscripts and serialized into highly queryable JSON files.

Each JSON document is partitioned into two distinct sections:
* **Header:** Contains standardized document metadata, including the source title, target language, original author, and credited translators.
* **Body:** Contains an array of sequentially numbered verse blocks. Each verse block encapsulates the aligned text segments using a standardized tagging schema:
  * `S1`, `S2`, etc.: English Source text iterations.
  * `T1`, `T2`, etc.: Target language translation iterations.

This nested verse structure explicitly preserves translation variants and human-in-the-loop editing iterations, making it highly suitable for Statistical Machine Translation (SMT) evaluation, BLEU metric testing, and parallel corpora alignment.

## Project Mission

This dataset was compiled to bridge the gap in machine-readable linguistic resources for Zambian languages, fostering both technological accessibility and educational equity.

Special acknowledgment is given to the dedicated translation team—including Musonda Chikula, Yowela Mayeba, Malambo Albert K., Chilufya Kasonde, Agnes Nankhoma Singine Nyendwa, Clarence K. Phiri, Sepiso Sepiso, Sir. Uyoya Wamuwi, Sir. Muleta Mubita, and Edina N. Kazadi — for their formative work in localizing these subjects.

## Data Access & Source Files

The parallel corpus is provided in parsed JSON format in this repository for immediate NLP and programmatic use.

If you require the original `.docx` translation manuscripts to review formatting or raw text boundaries, please contact me directly.
