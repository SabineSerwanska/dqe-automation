*** Settings ***
Library           SeleniumLibrary
Library           helper.py
Library           Collections
Test Teardown     Close All Browsers

*** Variables ***
${REPORT_FILE}       ${CURDIR}${/}..${/}Selenium Introduction${/}generated_report${/}report.html
${PARQUET_FOLDER}    ${CURDIR}${/}parquet_data${/}facility_type_avg_time_spent_per_visit_date
${FILTER_DATE}       2026-10-02
${BROWSER}           Chrome
${WAIT_TIMEOUT}      15 seconds

*** Test Cases ***
HTML Report Table Matches Filtered Parquet Dataset
	${REPORT_URI}=    Get File Uri    ${REPORT_FILE}
	Open Browser    ${REPORT_URI}    ${BROWSER}
	Wait Until Element Is Visible    css:.table    ${WAIT_TIMEOUT}
	${TABLE}=    Get WebElement    css:.table
	${REPORT_DATA}=    Read Html Table Data    ${TABLE}
	${REPORT_DATA}=    Filter Dataframe By Date    ${REPORT_DATA}    ${FILTER_DATE}    Visit Date
	${PARQUET_DATA}=    Read Partitioned Parquet    ${PARQUET_FOLDER}    ${FILTER_DATE}
	${COMPARISON}=    Compare Dataframes Exact    ${REPORT_DATA}    ${PARQUET_DATA}
	${MATCHES}=    Get From Dictionary    ${COMPARISON}    matches
	${SUMMARY}=    Get From Dictionary    ${COMPARISON}    summary
	Log    ${SUMMARY}
	Should Be True    ${MATCHES}    ${SUMMARY}
