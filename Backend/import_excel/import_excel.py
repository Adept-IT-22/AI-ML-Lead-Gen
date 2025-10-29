from openpyxl import load_workbook

def excel_input(file: str):
    print("Starting file input...")
    
    #Load file
    workbook = load_workbook(file)

    #Get first worksheet (the one on the far left in the file)
    list_of_worksheets = workbook.worksheets
    desrired_sheet = list_of_worksheets[0]

    #Open and read the sheet
    x = {}
    for i, row in enumerate(desrired_sheet.iter_rows(values_only=True)):
        x[i] = row
    print(x[0])

    return

def main():
    with open('./import_excel/demo.xlsx', 'rb') as file:
        excel_input(file)

if __name__ == "__main__":
    main()    