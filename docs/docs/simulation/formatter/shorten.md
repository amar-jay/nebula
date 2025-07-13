# Shorten

"Shortens" the number by dividing it through 1,000, 10,000, etc. where applicable and attaches a text at the end based on the number it divided it through.  
As an example, `1000` will become `10K` while `1000000` will become `1M`.

## Placeholder Patterns

- `%formatter_number_shorten_<number>%`
- `%formatter_number_shorten_<rounding_mode>_<number>%`

## Options

### `rounding_mode`

| Type   | Required | Conditions | Default                                                                |
|--------|----------|------------|------------------------------------------------------------------------|
| String | No       |            | [Config Option `shorten.rounding_mode`](index.md#shortenrounding_mode) |

What Rounding mode should be used.

--8<-- "rounding-modes.md"

### `number`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| Number | Yes      |            |         |

The number that should be shortened.

## Examples

```
/papi parse me %formatter_number_shorten_999%     -> 999
/papi parse me %formatter_number_shorten_1000%    -> 1K
/papi parse me %formatter_number_shorten_10000%   -> 10K
/papi parse me %formatter_number_shorten_100000%  -> 100K
/papi parse me %formatter_number_shorten_1000000% -> 1M
```