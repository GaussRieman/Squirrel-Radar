"use client";

export function MonthSelector({ months, currentMonth }: { months: string[]; currentMonth: string }) {
  return (
    <select
      className="month-select"
      value={currentMonth}
      aria-label="选择月份"
      onChange={(event) => {
        const params = new URLSearchParams(window.location.search);
        params.set("month", event.target.value);
        window.location.href = `/?${params.toString()}`;
      }}
    >
      {months.map((month) => (
        <option value={month} key={month}>
          {month}
        </option>
      ))}
    </select>
  );
}
