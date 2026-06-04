# Project Overview

This project is a Movie Quiz application written in Python. It includes a command-line interface (CLI) and a graphical user interface (GUI) version. The application uses movie data scraped from Letterboxd.

The project is structured as follows:

-   `extraer_datos_letterboxd_urls.py`: A script to scrape movie data from Letterboxd URLs. It reads CSV files from the `csv_lists` directory, scrapes the data, and saves it into new CSV files in the `csv_quiz` directory.
-   `movieQuiz.py`: A command-line based movie quiz game.
-   `movieQuiz_gui.py`: A GUI version of the quiz built with `tkinter`.
-   `csv_lists/`: Contains CSV files with lists of movies from Letterboxd, used as input for the scraping script.
-   `csv_quiz/`: Contains the generated CSV files with detailed movie information, used by the quiz applications.
-   `records/`: Stores the high scores for each quiz.

## Building and Running

### Dependencies

The project requires the following Python libraries:

-   `pandas`
-   `requests`
-   `beautifulsoup4`

You can install them using pip:

```bash
pip install pandas requests beautifulsoup4
```

### Generating Quiz Data

To generate the quiz data, run the `extraer_datos_letterboxd_urls.py` script. It will prompt you to choose a list from the `csv_lists` directory to process.

```bash
python extraer_datos_letterboxd_urls.py
```

### Running the Quiz

**CLI Version:**

To play the command-line version of the quiz, run `movieQuiz.py`:

```bash
python movieQuiz.py
```

The script will ask you to choose a quiz from the `csv_quiz` directory.

**GUI Version:**

To launch the graphical version of the quiz, run `movieQuiz_gui.py`:

```bash
python movieQuiz_gui.py
```

The GUI will automatically detect the available quizzes in the `csv_quiz` directory. You can also change the directory from the application.

## Development Conventions

-   The project is written in Python.
-   The GUI is built using the standard `tkinter` library.
-   Data is stored in CSV files.
-   The `movieQuiz_gui.py` application is designed to use `movieQuiz.py` as its engine, but it also includes fallback functions to work independently.
-   High scores are saved in `.record` files in the `records` directory.
