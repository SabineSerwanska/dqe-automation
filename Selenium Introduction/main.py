import csv
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)


class SeleniumWebDriverContextManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None

    def __enter__(self):
        options = webdriver.ChromeOptions()
        options.add_argument("--window-size=1440,1000")
        if self.headless:
            options.add_argument("--headless=new")

        self.driver = webdriver.Chrome(options=options)
        return self.driver

    def __exit__(self, exc_type, exc_value, traceback):
        if self.driver is not None:
            self.driver.quit()
            self.driver = None
        return False


def extract_table_to_csv(driver: WebDriver, report_path: Path, csv_path: Path):
    if not report_path.is_file():
        raise FileNotFoundError(f"HTML report not found: {report_path}")

    driver.get(report_path.resolve().as_uri())
    wait = WebDriverWait(driver, 15)
    table = wait.until(
        EC.visibility_of_element_located((By.CLASS_NAME, "table"))
    )

    columns = table.find_elements(By.CSS_SELECTOR, ".y-column")
    if not columns:
        raise NoSuchElementException("The report table contains no columns")

    headers = []
    column_values = []
    for column in columns:
        header = column.find_element(By.ID, "header").text.strip()
        headers.append(header)

        cells = column.find_elements(
            By.XPATH,
            ".//*[contains(concat(' ', normalize-space(@class), ' '), ' cell-text ')]",
        )
        values = []
        header_skipped = False
        for cell in cells:
            value = cell.text.strip()
            if not header_skipped and value == header:
                header_skipped = True
                continue
            values.append(value)
        column_values.append(values)

    row_counts = {len(values) for values in column_values}
    if len(row_counts) != 1:
        raise ValueError(
            "Table columns have different numbers of data cells: "
            f"{[len(values) for values in column_values]}"
        )

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(headers)
        writer.writerows(zip(*column_values))

    return len(column_values[0])


def find_doughnut_graph(driver: WebDriver):
    def graph_with_pie_layer(current_driver):
        for graph in current_driver.find_elements(
            By.CSS_SELECTOR, "div.plotly-graph-div"
        ):
            if graph.find_elements(By.CLASS_NAME, "pielayer"):
                return graph
        return False

    return WebDriverWait(driver, 15).until(graph_with_pie_layer)


def extract_doughnut_rows(graph):
    labels = graph.find_elements(
        By.CSS_SELECTOR, ".pielayer text.slicetext[data-notex='1']"
    )
    rows = []
    for label in labels:
        text_lines = [
            line.text.strip()
            for line in label.find_elements(By.TAG_NAME, "tspan")
        ]
        if len(text_lines) >= 2:
            rows.append((text_lines[0], text_lines[1]))
    return rows


def write_doughnut_csv(rows, csv_path: Path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8-sig") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(["Facility Type", "Min Average Time Spent"])
        writer.writerows(rows)


def save_doughnut_snapshot(graph, rows, output_dir: Path, index: int):
    output_dir.mkdir(parents=True, exist_ok=True)
    graph.screenshot(str(output_dir / f"screenshot{index}.png"))
    write_doughnut_csv(rows, output_dir / f"doughnut{index}.csv")


def automate_doughnut_filters(driver: WebDriver, output_dir: Path):
    graph = find_doughnut_graph(driver)
    initial_rows = extract_doughnut_rows(graph)
    save_doughnut_snapshot(graph, initial_rows, output_dir, 0)

    filters = graph.find_elements(By.CSS_SELECTOR, ".scrollbox .traces")
    for filter_index in range(len(filters)):
        snapshot_index = filter_index + 1
        try:
            graph = find_doughnut_graph(driver)
            before_rows = extract_doughnut_rows(graph)
            current_filters = graph.find_elements(
                By.CSS_SELECTOR, ".scrollbox .traces"
            )
            if filter_index >= len(current_filters):
                raise NoSuchElementException(
                    f"Chart filter {filter_index} is no longer available"
                )

            current_filters[filter_index].click()

            def chart_changed(current_driver):
                try:
                    return extract_doughnut_rows(
                        find_doughnut_graph(current_driver)
                    ) != before_rows
                except (NoSuchElementException, StaleElementReferenceException):
                    return False

            WebDriverWait(driver, 10).until(chart_changed)
            graph = find_doughnut_graph(driver)
        except (
            ElementClickInterceptedException,
            NoSuchElementException,
            StaleElementReferenceException,
            TimeoutException,
        ) as error:
            print(f"Could not apply chart filter {filter_index}: {error}")
            graph = find_doughnut_graph(driver)

        current_rows = extract_doughnut_rows(graph)
        save_doughnut_snapshot(graph, current_rows, output_dir, snapshot_index)


if __name__ == "__main__":
    project_dir = Path(__file__).resolve().parent
    report_path = project_dir / "generated_report" / "report.html"
    output_dir = project_dir / "selenium_output"
    csv_path = output_dir / "table.csv"

    try:
        with SeleniumWebDriverContextManager() as driver:
            row_count = extract_table_to_csv(driver, report_path, csv_path)
            print(f"Saved {row_count} table rows to {csv_path}")
            automate_doughnut_filters(driver, output_dir)
            print(f"Saved doughnut CSVs and screenshots under {output_dir}")
    except (TimeoutException, NoSuchElementException, ValueError) as error:
        raise RuntimeError(f"Could not extract the report table: {error}") from error
