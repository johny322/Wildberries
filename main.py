from castom_driver.driver import Driver
from wb.parser import Wildberries, SortKinds

if __name__ == '__main__':
    d = Driver(force=True)
    wb = Wildberries(d)
    try:
        wb.search_by_max_items('рубашка мужская', start_page=1, sort=SortKinds.priceup, items=100)
        wb.write_json_data('test.json')
        wb.write_csv_data('test.csv')
    finally:
        d.close()
        d.quit()
