# Time

Converts the provided `<number>` into a collection of time units.  
The returned time units depend on if the number can be converted into such a time unit after subtracting any higher ones first and if zero values are displayed.

## Placeholder Patterns

- `%formatter_number_time_<number>%`
- `%formatter_number_time_<time_unit>_<number>%`

## Options

### `time_unit`

| Type   | Required | Conditions | Default       |
|--------|----------|------------|---------------|
| String | No       |            | `fromSeconds` |

Sets the time unit that `<number>` should be seen as.

Supported options:

- `fromMilliseconds`/`fromMs` - Treat `<number>` as milliseconds.
- `fromSeconds`/`fromSecs` - Treat `<number>` as seconds.
- `fromMinutes`/`fromMins` - Treat `<number>` as minutes.
- `fromHours`/`fromHrs` - Treat `<number>` as hours.

### `number`

| Type   | Required | Conditions | Default       |
|--------|----------|------------|---------------|
| Number | Yes      | `0 ≤ x`    |               |

The Number to convert.  
Any number that is less than zero will return whatever has been set for [`time.belowZeroOutput`](index.md#timebelowzerooutput).

## Examples

```
/papi parse me %formatter_number_time_100%          -> 1m 40s
/papi parse me %formatter_number_time_fromMs_1200%  -> 1s 200ms
/papi parse me %formatter_number_time_fromSecs_100% -> 1m 40s
/papi parse me %formatter_number_time_fromMins_100% -> 1h 40m
/papi parse me %formatter_number_time_fromHrs_100%  -> 4d 4h
```