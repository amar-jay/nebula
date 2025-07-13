# From-to

Converts the provided `<number>` from the `<old_time_unit>` time unit to the `<new_time_unit>` time unit.

## Placeholder Patterns

- `%formatter_number_from:<old_time_unit>_to:<new_time_unit>_<number>%`

## Options

### `old_time_unit`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The time unit to understand the provided number as.  
[See below](#supported-time-units) for a list of supported time units and their identifiers.

### `old_time_unit`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| String | Yes      |            |         |

The new time unit to convert the number into.  
[See below](#supported-time-units) for a list of supported time units and their identifiers.

### `number`

| Type   | Required | Conditions | Default |
|--------|----------|------------|---------|
| Number | Yes      |            |         |

The number to convert from one time unit to another.

## Supported time units

| Time Unit   | Identifiers                                   |
|-------------|-----------------------------------------------|
| Day         | `days`, `day`                                 |
| Hour        | `hours`, `hour`, `hrs`                        |
| Minute      | `minutes`, `minute`, `mins`, `min`            |
| Second      | `seconds`, `second`, `secs`, `sec`            |
| Millisecond | `milliseconds`, `millisecond`, `millis`, `ms` |

## Examples

```
/papi parse me %formatter_number_from:secs_to:mins_120% -> 2m
/papi parse me %formatter_number_from:mins_to:hrs_119%  -> 1h
```