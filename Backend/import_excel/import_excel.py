from openpyxl import load_workbook

def excel_input(file: str):
    workbook = load_workbook(file)
    list_of_worksheets = workbook.worksheets
    print(list_of_worksheets)
    return

if __name__ == "__main__":
    pass