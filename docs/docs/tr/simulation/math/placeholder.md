# Placeholder

Evaluates the provided Expression to return a number.

## Placeholder Patterns

- `%math_<expression>%`
- `%math_[decimals]:[rounding_mode]_<expression>%`

## Options

### `decimals`

| Type   | Required | Default                                       |
|--------|----------|-----------------------------------------------|
| Number | No       | [Config option `Decimals`](index.md#decimals) |

Sets the number of decimal places to display on the final number.

### `rounding_mode`

| Type   | Required | Default                                       |
|--------|----------|-----------------------------------------------|
| String | No       | [Config option `Rounding`](index.md#rounding) |

Sets the rounding mode to use.

--8<-- "rounding-modes.md"

### `expression`

| Type   | Required | Default |
|--------|----------|---------|
| String | Yes      |         |

## Examples

```
%math_1+2%          -> 3
%math_6:_1/3%       -> 0.333333 # Rounding is half-up
%math_:ceiling_1/3% -> 0.334    # Decimals is 3
%math_22[prc]4%     -> 2        # Equal to '22 % 4'
```