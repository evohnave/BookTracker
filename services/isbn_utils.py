"""
Code for book stuff

For isbn related info, see https://isbn-information.com/

@author: Eric
"""
from typing import Union

ISBN13_CHECKS = [1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1, 3, 1]
ISBN10_CHECKS = [10, 9, 8, 7, 6, 5, 4, 3, 2]
VALID_PREFIX_ELEMENTS = ["978", "979"]
VALIDATION_ERRORS = {
    "length": "Input is not of the correct length.",
    "invalid": "Input has invalid characters.",
    "13X": "ISBN 13 has invalid 'X' character",
    "prefix": "ISBN 13 starts with invalid Prefix Element {}",
    }

def is_valid(isbn: str) -> bool:
    """
    Validates an ISBN 10 or 13

    Parameters
    ----------
    isbn : str
        An ISBN code (10 or 13)

    Returns
    -------
    bool
        True, if valid.

    Raises
    ------
    ValueError
        If isbn has invalid characters or is not of proper length

    """
    stripped = isbn.replace("-", " ").replace(" ", "")
    if len(stripped) not in [10, 13]:
        raise ValueError(VALIDATION_ERRORS["length"])
    if any(char.upper() not in '01234567890X' for char in stripped):
        raise ValueError(VALIDATION_ERRORS["invalid"])
    if "X" in stripped and len(stripped) == 13:
        raise ValueError(VALIDATION_ERRORS["13X"])
    if stripped[:3] not in VALID_PREFIX_ELEMENTS and len(stripped) == 13:
        raise ValueError(VALIDATION_ERRORS["prefix"].format(stripped[:3]))
    if len(stripped) == 13:
        return sum(a * int(b)
                   for (a, b) in zip(ISBN13_CHECKS, stripped)) % 10 == 0
    return (sum(a * int(b)
                for (a, b) in zip(ISBN10_CHECKS, stripped[:-1])) \
                + int([stripped[-1], '10'][stripped[-1] == "X"])) % 11 == 0

def to_isbn13(isbn: str) -> str:
    """
    Converts an ISBN 10 to an ISBN 13

    Parameters
    ----------
    isbn : str
        The ISBN 10

    Returns
    -------
    str
        The ISBN 13

    Raises
    ------
    ValueError
        If the input is an invalid ISBN10

    """

    # Remove all spaces and dashses
    isbn10 = isbn.replace(" ", "").replace("-", "")
    if is_valid(isbn10):
        if len(isbn10) == 13:
            return isbn10
        if len(isbn10) != 10:
            raise ValueError(VALIDATION_ERRORS['length'])
        isbn13 = "978" + isbn10[:-1]
        check_digit = str(10 - sum(a * int(b)
                                   for (a, b) in zip(ISBN13_CHECKS[:-1], isbn13)) % 10)
        return isbn13 + check_digit
    return None

def to_isbn10(isbn: str) -> Union[str, None]:
    """
    Converts an ISBN 13 to an ISBN 10

    Parameters
    ----------
    isbn : str
        The ISBN 13.

    Returns
    -------
    str or None
        The ISBN 10.
        Will return None if the Prefix element is not 978 since only 978
          maps to ISBN 10

    Raises
    ------
    ValueError
        If the input is an invalid ISBN13

    """
    isbn13 = isbn.replace(" ","").replace("-","")
    if is_valid(isbn13):
        if len(isbn13) == 10:
            return isbn13
        if len(isbn13) != 13:
            raise ValueError(VALIDATION_ERRORS['length'])
        if isbn13[:3] != "978":
            return None
        isbn10 = isbn13[3:-1]
        check_digit = str(11 - sum(a * int(b)
                                   for (a, b) in zip(ISBN10_CHECKS, isbn10)) % 11)
        return isbn10 + check_digit
    return None
