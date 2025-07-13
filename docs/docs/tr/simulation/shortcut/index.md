# Shortcut

The Shortcut expansion allows you to parse larger strings and multiple placeholders by having them in separate TXT files.  
This system can be used as a very basic workaround for nested placeholder support.

/// download | Download expansion
```
/papi ecloud download shortcut
```
///

## Statistics

<span data-md-component="expansion-shortcut">Fetching data...<br>If this text doesn't change, check that you allow javascript to be executed.</span>

## Source Code

The Source code of this expansion is available on [:simple-github: GitHub](https://github.com/Andre601/Shortcut-Expansion){ target="_blank" rel="nofollow" }

## Placeholders

- [`%shortcut_<file>[:<replacements>]%`](placeholder.md)

## External Placeholders support

Placeholders from other expansions can be used by using the `{<identifier>_<value>}` pattern instead of the usual `%<identifier>_<value>%` pattern.

## Custom value replacements

You can define placeholders in the form of `{n}` where `n` would be a 0-indexed number corresponding to the replacement within the placeholder. This means `0` is the first entry, `1` the second and so on.

As an example, assume the file `example.txt` exists with the following content in the `shortcuts` folder:

```
My favourite fruit is {0}.
My second favourite fruit is {1}.
```

If you now use `%shortcut_example:apple:banana%` would the result be:

```
My favourite fruit is apple.
My second favourite fruit is banana.
```

...and if we use `%shortcut_example:banana:apple%` would it be this instead:

```
My favourite fruit is banana.
My second favourite fruit is apple.
```

If there are not enough replacements available to cover all placeholders will any placeholder with a higher index value remain unchanged.