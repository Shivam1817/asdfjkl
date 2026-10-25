import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export default function WindChart({ data }) {
  const byTime = new Map(data.comparison.map((row) => [Date.parse(row.startTime), row]));
  const start = Date.parse(`${data.deliveryDate}T00:00:00Z`);
  const points = Array.from({ length: data.expectedForecastCount }, (_, hour) => {
    const row = byTime.get(start + hour * 60 * 60 * 1000);
    return { hour, forecastMW: row?.forecastMW ?? null, actualMW: row?.actualMW ?? null };
  });
  const hourLabel = (hour) => `${String(hour).padStart(2, "0")}:00`;

  return (
    <div className="chart-canvas" aria-label="Hourly wind forecasts and matching half-hour actuals">
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart data={points} margin={{ top: 16, right: 12, left: -12, bottom: 8 }} accessibilityLayer>
          <CartesianGrid vertical={false} stroke="#e7ece8" strokeDasharray="3 4" />
          <XAxis dataKey="hour" ticks={[0, 3, 6, 9, 12, 15, 18, 21, 23]} tickFormatter={hourLabel}
            tickLine={false} axisLine={false} minTickGap={24} tick={{ fill: "#69776f", fontSize: 11 }} dy={10} />
          <YAxis domain={[0, "auto"]} tickFormatter={(value) => (value / 1000).toLocaleString("en-GB")}
            tickLine={false} axisLine={false} width={54} tick={{ fill: "#69776f", fontSize: 11 }} />
          <Tooltip labelFormatter={(hour) => `${hourLabel(hour)} UK / UTC`}
            formatter={(value, name) => [`${Number(value).toLocaleString("en-GB", { maximumFractionDigits: 0 })} MW`, name]}
            contentStyle={{ border: "1px solid #dce4df", borderRadius: 10, fontSize: 13 }}
            labelStyle={{ color: "#233c32", fontWeight: 600 }} />
          <Line type="linear" dataKey="forecastMW" name="Forecast" stroke="#247b66" strokeWidth={2.5}
            strokeDasharray="6 5" dot={{ r: 2, strokeWidth: 0, fill: "#247b66" }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />
          <Line type="linear" dataKey="actualMW" name="Actual" stroke="#59677a" strokeWidth={2.5}
            dot={{ r: 2, strokeWidth: 0, fill: "#59677a" }} activeDot={{ r: 5 }} connectNulls={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
