def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def find_duplicates(items):
    duplicates = []
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if items[i] == items[j] and items[i] not in duplicates:
                duplicates.append(items[i])
    return duplicates


def sort_and_rank(records):
    n = len(records)
    for i in range(n):
        for j in range(n - i - 1):
            if records[j]["score"] < records[j + 1]["score"]:
                records[j], records[j + 1] = records[j + 1], records[j]
    return records


if __name__ == "__main__":
    print(fibonacci(30))
    print(find_duplicates([1, 2, 3, 2, 4, 3, 5]))
    records = [{"name": f"item_{i}", "score": i % 7} for i in range(500)]
    print(sort_and_rank(records)[0])
