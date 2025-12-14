def clean_isbn(isbn_str: str) -> str:
    # Strip invalid characters: keep digits and 'X'
    return ''.join(c for c in isbn_str.upper() if c.isdigit() or c == 'X')

def validate_isbn(isbn: str) -> bool:
    isbn = clean_isbn(isbn)
    if len(isbn) == 10:
        # ISBN-10 validation
        check = 0
        for i in range(9):
            check += int(isbn[i]) * (10 - i)
        check_digit = 11 - (check % 11)
        if check_digit == 11:
            check_digit = 0
        elif check_digit == 10:
            check_digit = 'X'
        return isbn[9] == str(check_digit)
    elif len(isbn) == 13:
        # ISBN-13 validation
        check = 0
        for i in range(12):
            check += int(isbn[i]) * (1 if i % 2 == 0 else 3)
        check_digit = 10 - (check % 10) if check % 10 != 0 else 0
        return int(isbn[12]) == check_digit
    return False

