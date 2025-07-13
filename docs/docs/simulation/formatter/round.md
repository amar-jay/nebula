# Round

Rounds the provided `<number>` with an optional `[precision]` and `[rounding_mode]`.

## Placeholder Patterns

- `%formatter_number_round_<number>%`
- `%formatter_number_round_[precision]:[rounding_mode]_<number>%`

## Options

### `precision`

| Type   | Required | Conditions | Default                                                          |
|--------|----------|------------|------------------------------------------------------------------|
| Number | No       | `0 ≤ x`    | [Config Option `rounding.precision`](index.md#roundingprecision) |

How many digits after the decimal point should be displayed.

### `rounding_mode`

| Type   | Required | Conditions | Default                                                |
|--------|----------|------------|--------------------------------------------------------|
| String | No       |            | [Config Option `rounding.mode`](index.md#roundingmode) |

What Rounding mode should be used.

--8<-- "rounding-modes.md"

### `number`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| Number | Yes      |            |         |

The number that should be rounded.

## Examples

```
/papi parse me %formatter_number_round_1.5%             -> 2     # Default is half-up
/papi parse me %formatter_number_round_3:_1.5%          -> 2.000 # Default is half-up
/papi parse me %formatter_number_round_:half-down_1.5%  -> 1
/papi parse me %formatter_number_round_3:half-down_1.5% -> 1.000
```