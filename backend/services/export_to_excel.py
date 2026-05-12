from utils.set_conversion import convert_sets
from openpyxl import Workbook
from typing import Dict, List, Any
import logging
import datetime

logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)

def make_excel_safe(value):
    #Lists and sets aren't allowed
    if isinstance(value, (list, set)):
        return ", ".join(map(str, value))
    #Dicts have to be strings too
    elif isinstance(value, dict):
        return str(value)
    elif isinstance(value, datetime.datetime):
        # Remove timezone info
        return value.replace(tzinfo=None)
    return value

async def export_to_excel(lead_data: List[Dict[str, Any]], filename="Lead Gen Leads.xlsx"):
    logger.info("Export to excel...")
    #Create Excel Workbook
    lead_data = convert_sets(lead_data)
    workbook = Workbook()

    #Create a work sheet
    worksheet = workbook.active
    worksheet.title = 'Lead Gen Leads'

    if not lead_data:
        logger.warning('No lead data to export')
        return None

    #Write headers (keys from lead data)
    headers = list(lead_data[0].keys())
    worksheet.append(headers)

    #Write each lead as row
    for lead in lead_data:
        row = []
        for key in headers:
            value = lead.get(key, "")
            value = make_excel_safe(value)
            row.append(value)
        worksheet.append(row)

    #Save workbook to file
    workbook.save(filename)
    logger.info(f"Excel file saved as {filename}")
    return filename

