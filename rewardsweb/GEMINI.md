# Project: Rewards Suite

## General Instructions

- When you generate new Python code, follow the existing coding style. Try to write Pythonic code whenever that's possible.

- Ensure all new functions and classes have docstrings. First line starts immediatelly after triple ".   For parameters use: 

    :param addresses: list of user addresses
    :type addresses: list

  For internal variables:

    :var atc: clear program source code
    :type atc: :class:`AtomicTransactionComposer`

  Start description with lowercase letter and don't add dot at the end of a description.

- Don't write docstrings in unit test functions, but let the unit test suite class have a docstring line.

## Unit tests

- Name unit test functions in the format   test_*package*_*module*_*lowercaseclassname*_*method_name*_action or test_*package*_*module*_*function_name*_action.

- Use pytest and pytest-mock. When you need to mock some function or argument, use `mocker` fixture as an argument in the test function. Create mocks like `mocker.MagicMock()` or `mocker.AsyncMock()`.

- Try to reach 100% test coverage whenever possible.

- Patch a function following this pattern (notice the name starts with mocked_ and continues with a single word):
    parsed_message = mocker.MagicMock()
    mocked_parse = mocker.patch("package.module.parse_message", return_value=parsed_message)

- When you need to ensure it is called once, use this:

    mocked_parse.assert_called_once_with(arg1, arg2)

- For multiple calls, use this:

    calls = [mocker.call(1, 0), mocker.call(2, 0)]
    mocked_parse.assert_has_calls(calls, any_order=True)
    assert mocked_parse.call_count == 2
