"use client";

export function MonthSelector({ months, currentMonth }: { months: string[]; currentMonth: string }) {
  return (
    <select
      className="month-select"
      value={currentMonth}
      aria-label="选择月份"
      onChange={(event) => {
        window.dispatchEvent(
          new CustomEvent("agent-navigate-month", { detail: { month: event.target.value } })
        );
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
