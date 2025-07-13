# Format

Formats the provided number by "prettyfying" it (i.e. adding separators for thousands).

## Placeholder Patterns

- `%formatter_number_format_<number>%`
- `%formatter_number_format_[locale]:[pattern]_<number>%`

## Options

### `locale`

| Type   | Required | Conditions | Default                                                        |
|--------|----------|------------|----------------------------------------------------------------|
| String | No       |            | [Config Option `formatting.locale`](index.md#formattinglocale) |

The locale that should be used.  
Formatting can be influenced by the locale used. As an example, german uses `'` to separate thousands while english uses `,`.

The locale can be one of two formats: A single language identifier (i.e. `en`) or a language identifier with country code (i.e. `en-US`).

/// warning
You have to use `-` instead of `_` for the country code option (i.e. `en-US` instead of `en_US`).
///

### `pattern`

| Type   | Required | Conditions | Default                                                         |
|--------|----------|------------|-----------------------------------------------------------------|
| String | No       |            | [Config Option `formatting.format`](index.md#formattingpattern) |

The Number pattern that should be used for the number.  
Uses the [special Pattern Characters](https://docs.oracle.com/en/java/javase/17/docs/api/java.base/java/text/DecimalFormat.html#special_pattern_character) of the DecimalFormat class in Java.

### `number`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| Number | Yes      |            |         |

The number that should be formatted.

## Examples

```
/papi parse me %formatter_number_format_1000%             -> 1,000
/papi parse me %formatter_number_format_de-CH:_1000%      -> 1'000
/papi parse me %formatter_number_format_:##,##_1000%      -> 10,00
/papi parse me %formatter_number_format_de-CH:##,##_1000% -> 10'00
```