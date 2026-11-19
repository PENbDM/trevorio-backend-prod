from trevorio.redis_client import rPerformance
from time import perf_counter


def generate_100_sessions():
    start = perf_counter()

    for i in range(1, 10001):
        group_id = (i - 1) // 100 + 1
        print(group_id)
        rPerformance.hset(f'user-session:{i}', mapping={
            'user_id': i,
            'table_id': f'table-{group_id}',
            'datasource_id': f'datasource-{group_id}'
        })

    generation_time = perf_counter() - start

    return "10000 sessions created successfully", generation_time


def get_unique_tables():
    # Step 1: Measure Redis SCAN
    start_scan = perf_counter()

    keys = list(rPerformance.scan_iter('user-session:*'))

    scan_time = perf_counter() - start_scan

    # Step 2: Measure Redis HGETALL pipeline
    start_hgetall = perf_counter()

    pipe = rPerformance.pipeline()

    for key in keys:
        pipe.hgetall(key)

    sessions = pipe.execute()

    hgetall_time = perf_counter() - start_hgetall

    # Step 3: Measure deduplication
    start_dedup = perf_counter()

    sets = set()

    for session in sessions:
        pair = (session["datasource_id"], session["table_id"])
        sets.add(pair)

    dedup_time = perf_counter() - start_dedup

    return sets, scan_time, hgetall_time, dedup_time


def main():
    # Generate sessions only once if Redis is empty.
    # print(generate_100_sessions())

    unique_tables, scan_time, hgetall_time, dedup_time = get_unique_tables()

    total_time = scan_time + hgetall_time + dedup_time

    print("Unique tables:", len(unique_tables))
    print(f"SCAN time: {scan_time:.6f}s")
    print(f"HGETALL time: {hgetall_time:.6f}s")
    print(f"Deduplication time: {dedup_time:.6f}s")
    print(f"Total processing time: {total_time:.6f}s")


if __name__ == '__main__':
    main()