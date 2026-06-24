
import json
from datetime import datetime, timedelta


# ---------------- Convert day range ----------------
def parse_days(day_string):
    days_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    if not day_string:
        return []

    if "to" in day_string:
        try:
            start, end = [x.strip() for x in day_string.split("to")]
            start_index = days_order.index(start)
            end_index = days_order.index(end)

            return days_order[start_index:end_index + 1]

        except:
            print(f"Could not parse days: {day_string}")
            return []

    return [day_string]


# ---------------- Convert time range to slots ----------------
def generate_slots(time_range, interval=30):

    if not time_range:
        return []

    time_range = time_range.strip()

    # Case 1 → proper range
    if "-" in time_range:

        try:
            parts = time_range.split("-")

            start_str = parts[0].strip()
            end_str = parts[1].strip()

            # handle "10 AM" instead of "10:00 AM"
            if ":" not in start_str:
                start_str = start_str.replace(" AM", ":00 AM").replace(" PM", ":00 PM")

            if ":" not in end_str:
                end_str = end_str.replace(" AM", ":00 AM").replace(" PM", ":00 PM")

            start = datetime.strptime(start_str, "%I:%M %p")
            end = datetime.strptime(end_str, "%I:%M %p")

            slots = []

            while start < end:
                slots.append(start.strftime("%I:%M %p").lstrip("0"))
                start += timedelta(minutes=interval)

            return slots

        except Exception as e:
            print(f"Could not parse time range: {time_range}")
            return []

    # Case 2 → single time only
    else:

        try:
            single = time_range

            if ":" not in single:
                single = single.replace(" AM", ":00 AM").replace(" PM", ":00 PM")

            datetime.strptime(single, "%I:%M %p")

            return [single]

        except:
            print(f"Skipping invalid time value: {time_range}")
            return []


# ---------------- Main conversion ----------------
def convert_json():

    input_file = "data/hospital_data.json"
    output_file = "data/hospital_data_converted.json"

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    doctors = data["doctors"]

    skipped = 0

    for doctor in doctors:

        # convert availability_days → working_days
        if "availability_days" in doctor:

            doctor["working_days"] = parse_days(
                doctor["availability_days"]
            )

            del doctor["availability_days"]

        # convert available_time → available_slots
        if "available_time" in doctor:

            slots = generate_slots(
                doctor["available_time"]
            )

            if not slots:
                skipped += 1
                print(
                    f"Skipping bad time for doctor: "
                    f"{doctor.get('name')} → {doctor['available_time']}"
                )

            doctor["available_slots"] = slots

            del doctor["available_time"]

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print("\n Conversion completed successfully.")
    print(f"Output file: {output_file}")
    print(f"Doctors processed: {len(doctors)}")
    print(f"Doctors with bad timing skipped: {skipped}")


if __name__ == "__main__":
    convert_json()
