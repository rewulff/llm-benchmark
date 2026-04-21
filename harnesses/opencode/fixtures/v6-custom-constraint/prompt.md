Write a file `solve.py` that contains a function with this exact signature:

    def find_sequences(n, target_sum, max_gap):

The function returns all lists of exactly `n` distinct positive integers between 1 and 50
(inclusive) such that:

1. Their sum equals `target_sum`
2. When sorted, the difference between any two consecutive values is at most `max_gap`
3. Each returned list is in sorted ascending order
4. Results are de-duplicated (e.g. `[3, 5, 7]` appears exactly once)

Include a `if __name__ == "__main__":` block that prints ONLY the integer result of
`len(find_sequences(4, 30, 5))` to stdout (no extra text, no labels).

When your implementation is complete and the file is saved, respond with just: DONE
Do NOT run the script yourself.
