from streaming.services.redis.compare_snapshots import compare_snapshots




oldData=[{"id": 1001013, "user_id": 20, "product_id": 87, "quantity": 12, "unit_price": "1.00",
  "total_price": "22.00", "status": "PENDING", "created_at": "2026-10-31T19:04:56.775538"},
 {"id": 1001012, "user_id": 20, "product_id": 87, "quantity": 11, "unit_price": "1.00", "total_price": "22.00",
  "status": "PENDING", "created_at": "2026-10-31T19:01:19.831615"}, {"id": 1001011, "user_id": 20, "product_id": 87,
"quantity": 6, "unit_price": "1.00", "total_price": "22.00", "status": "PENDING",
"created_at": "2026-10-31T18:55:05.785024"}]

newData=[{"id": 1001014, "user_id": 20, "product_id": 87, "quantity": 12, "unit_price": "1.00",
  "total_price": "22.00", "status": "PENDING", "created_at": "2026-10-31T19:04:56.775538"},
 {"id": 1001012, "user_id": 20, "product_id": 87, "quantity": 11, "unit_price": "1.00", "total_price": "22.00",
  "status": "PENDING", "created_at": "2026-10-31T19:01:19.831615"}, {"id": 1001011, "user_id": 20, "product_id": 87,
"quantity": 6, "unit_price": "1.00", "total_price": "22.00", "status": "PENDING",
"created_at": "2026-10-31T18:55:05.785024"}]

oldData1=[{"id": 1001013, "user_id": 20, "product_id": 87, "quantity": 12, "unit_price": "1.00",
  "total_price": "22.00", "status": "PENDING", "created_at": "2026-10-31T19:04:56.775538"},
 {"id": 1001012, "user_id": 20, "product_id": 87, "quantity": 11, "unit_price": "1.00", "total_price": "22.00",
  "status": "PENDING", "created_at": "2026-10-31T19:01:19.831615"}, {"id": 1001011, "user_id": 20, "product_id": 87,
"quantity": 6, "unit_price": "1.00", "total_price": "22.00", "status": "PENDING",
"created_at": "2026-10-31T18:55:05.785024"}]

newData2=[{"id": 1001013, "user_id": 20, "product_id": 87, "quantity": 12, "unit_price": "1.00",
  "total_price": "22.00", "status": "PENDING", "created_at": "2026-10-31T19:04:56.775538"},
 {"id": 1001012, "user_id": 20, "product_id": 87, "quantity": 11, "unit_price": "1.00", "total_price": "22.00",
  "status": "PENDING", "created_at": "2026-10-31T19:01:19.831615"}, {"id": 1001011, "user_id": 20, "product_id": 87,
"quantity": 6, "unit_price": "1.00", "total_price": "22.00", "status": "PENDING",
"created_at": "2026-10-31T18:55:05.785024"}]




def test_compare_snapshots_detects_new_row():
    assert compare_snapshots(oldData, newData) == [1001014]



def test_compare_snapshots_no_new_rows():
    assert compare_snapshots(oldData1, newData2) == []
