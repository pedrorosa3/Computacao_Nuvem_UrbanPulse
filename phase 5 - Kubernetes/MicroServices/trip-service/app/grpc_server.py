import grpc
from concurrent import futures
from app import trip_service_pb2
from app import trip_service_pb2_grpc
from app.database import execute_query


class TripServicer(trip_service_pb2_grpc.TripServiceServicer):

    # ── UC14 — Payment Service ────────────────────────────────────────────────
    def GetPassengerCounts(self, request, context):
        trip_ids = list(request.trip_ids)

        if not trip_ids:
            return trip_service_pb2.PassengerCountResponse(trip_passengers={})

        placeholders = ",".join(["%s"] * len(trip_ids))
        rows = execute_query(
            f"SELECT id, passenger_count FROM trips WHERE id IN ({placeholders})",
            tuple(trip_ids)
        )

        passengers_map = {
            row["id"]: int(row["passenger_count"])
            for row in rows
            if row["passenger_count"] is not None
        }

        return trip_service_pb2.PassengerCountResponse(trip_passengers=passengers_map)

    # ── UC10 — Revenue Service ────────────────────────────────────────────────
    def GetDistanceByZone(self, request, context):
        zone_type = request.zone_type if request.zone_type in ("pickup", "dropoff") else "pickup"
        zone_col  = f"{zone_type}_zone_id"

        conditions = ["trip_distance_km > 0"]
        params     = []

        if request.year and request.year > 0:
            conditions.append("EXTRACT(YEAR  FROM pickup_datetime) = %s")
            params.append(request.year)

        if request.month and request.month > 0:
            conditions.append("EXTRACT(MONTH FROM pickup_datetime) = %s")
            params.append(request.month)

        where = " AND ".join(conditions)

        query = f"""
            SELECT
                {zone_col}            AS zone_id,
                AVG(trip_distance_km) AS avg_distance,
                COUNT(*)              AS trip_count
            FROM trips
            WHERE {where}
            GROUP BY {zone_col}
        """

        try:
            rows = execute_query(query, tuple(params))
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"DB error: {e}")
            return trip_service_pb2.DistanceByZoneResponse()

        zones = [
            trip_service_pb2.ZoneDistanceInfo(
                zone_id      = int(row["zone_id"]),
                avg_distance = float(row["avg_distance"]),
                trip_count   = int(row["trip_count"]),
            )
            for row in rows
        ]

        return trip_service_pb2.DistanceByZoneResponse(zones=zones)

    # ── UC18 — Analytics Service ──────────────────────────────────────────────
    def GetTripDurations(self, request, context):
        trip_ids = list(request.trip_ids)

        if not trip_ids:
            return trip_service_pb2.TripDurationResponse(trips=[])

        placeholders = ",".join(["%s"] * len(trip_ids))
        rows = execute_query(
            f"""
            SELECT
                id,
                EXTRACT(EPOCH FROM (dropoff_datetime - pickup_datetime)) / 60.0 AS duration_min,
                trip_distance_km,
                time_class
            FROM trips
            WHERE id IN ({placeholders})
            """,
            tuple(trip_ids)
        )

        trips = [
            trip_service_pb2.TripDurationInfo(
                trip_id      = row["id"],
                duration_min = float(row["duration_min"])    if row["duration_min"]    else 0.0,
                distance_km  = float(row["trip_distance_km"]) if row["trip_distance_km"] else 0.0,
                time_class   = row["time_class"] or "",
            )
            for row in rows
        ]

        return trip_service_pb2.TripDurationResponse(trips=trips)

    # ── UC20 — Analytics Service ──────────────────────────────────────────────
    def GetSuspiciousTrips(self, request, context):
        min_score  = request.min_suspicion_score or 1
        start_date = request.start_date
        end_date   = request.end_date
        limit      = request.limit or 100

        filters = ["suspicion_score >= %s"]
        params  = [min_score]

        if start_date:
            filters.append("DATE(pickup_datetime) >= %s")
            params.append(start_date)
        if end_date:
            filters.append("DATE(pickup_datetime) <= %s")
            params.append(end_date)

        where = "WHERE " + " AND ".join(filters)

        count_rows = execute_query(
            f"SELECT COUNT(*) AS total FROM trips {where}",
            tuple(params)
        )
        total = int(count_rows[0]["total"]) if count_rows else 0

        rows = execute_query(
            f"""
            SELECT
                id,
                trip_distance_km,
                fare_amount,
                deviation_index,
                deviation_class,
                suspicion_score,
                pickup_zone_name,
                dropoff_zone_name
            FROM trips
            {where}
            ORDER BY suspicion_score DESC
            LIMIT %s
            """,
            tuple(params) + (limit,)
        )

        trips = [
            trip_service_pb2.SuspiciousTrip(
                trip_id          = row["id"],
                trip_distance_km = float(row["trip_distance_km"]) if row["trip_distance_km"] else 0.0,
                fare_amount      = float(row["fare_amount"])       if row["fare_amount"]       else 0.0,
                deviation_index  = float(row["deviation_index"])   if row["deviation_index"]   else 0.0,
                deviation_class  = row["deviation_class"]          or "",
                suspicion_score  = int(row["suspicion_score"])     if row["suspicion_score"]   else 0,
                pickup_zone      = row["pickup_zone_name"]         or "",
                dropoff_zone     = row["dropoff_zone_name"]        or "",
            )
            for row in rows
        ]

        return trip_service_pb2.SuspiciousTripsResponse(trips=trips, total_found=total)


def serve_grpc():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    trip_service_pb2_grpc.add_TripServiceServicer_to_server(TripServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    return server
