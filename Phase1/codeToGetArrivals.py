import json
import requests

# TfL API endpoint for arrivals on Line 244
URL = "https://api.tfl.gov.uk/Line/244/Arrivals"


def get_tfl_arrivals():
    try:
        response = requests.get(URL, timeout=10)
        response.raise_for_status()
        arrivals = response.json()

        # Modern best practice: Use the 'with' statement for file handling
        with open("line_244_arrivals.json", "w", encoding="utf-8") as file:
            json.dump(arrivals, file, indent=4)

        print("File created successfully.")

    except requests.exceptions.RequestException as e:
        print(f"Network or API error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    get_tfl_arrivals()