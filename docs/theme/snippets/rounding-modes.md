

/// details | Available modes
    type: example

-   `up`  
    Rounds away from zero. Always increases the digit prior to a non-zero discarded fraction.  
    Examples:
    
    - `-1.5 -> -2`
    - `-1.1 -> -2`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 2`
    - `1.5 -> 2`

-   `down`  
    Rounds towards zero. Always decreases the digit prior to a non-zero discarded fraction.  
    Examples:
    
    - `-1.5 -> -1`
    - `-1.1 -> -1`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 1`
    - `1.5 -> 1`

-   `ceiling`  
    Rounds towards positive infinity. Always rounds up if number is positive, otherwise rounds down.  
    Examples:
    
    - `-1.5 -> -1`
    - `-1.1 -> -1`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 2`
    - `1.5 -> 2`

-   `floor`  
    Rounds towards negative infinity. Always rounds down if number is positive, otherwise rounds up.  
    Examples:
    
    - `-1.5 -> -2`
    - `-1.1 -> -2`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 1`
    - `1.5 -> 1`

-   `half-up`  
    Rounds to nearest neighbour unless both neighbours are equidistant in which case it rounds up. This is what you're commonly teached in school.  
    Examples:
    
    - `-1.5 -> -2`
    - `-1.1 -> -1`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 1`
    - `1.5 -> 2`

-   `half-down`  
    Rounds to nearest neighbour unless both neighbours are equidistant in which case it rounds down.  
    Examples:
    
    - `-1.5 -> -1`
    - `-1.1 -> -1`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 1`
    - `1.5 -> 1`

-   `half-even`  
    Rounds to nearest neighbour unless both neighbours are equidistant in which case it rounds to nearest even neighbour (Up if digit to the left is odd, else down).  
    Examples:
    
    - `-1.5 -> -2`
    - `-1.1 -> -1`
    - `-1.0 -> -1`
    - `1.0 -> 1`
    - `1.1 -> 1`
    - `1.5 -> 2`
///