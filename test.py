import datetime
from bot import get_todays_bible_reading, BibleReadingScheduleEntry

TESTFILE = 'schedule_test.csv'

def test_get_todays_bible_reading():
    # Create a sample schedule.csv file
    with open(TESTFILE, 'w') as file:
        file.write("01-01-22,Matthew 1,Genesis 1\n")
        file.write("01-02-22,Matthew 2,Genesis 2\n")
        file.write('01-03-22,Matthew 3,"Genesis 3"\n')
        file.write(f"{datetime.date.today().strftime('%m-%d-%y')},Matthew 4,Genesis 4\n")
        file.close()

    # Test case: today's date is in the schedule
        expected_entry = BibleReadingScheduleEntry(datetime.date.today(), 'Genesis 4','Matthew 4')
        
        found_entry = get_todays_bible_reading(TESTFILE)
        
        assert found_entry == expected_entry, f"An error occurred: Expected entry is: {expected_entry}, but got {found_entry}"

        # Clean up the sample schedule.csv file
        #os.remove(TESTFILE)
        
if __name__ == '__main__':
    print('Start Testing')
    test_get_todays_bible_reading()
    print('All tests passed')
