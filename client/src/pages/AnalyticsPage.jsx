import {
  BarChart,
  Bar,
  XAxis,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";

const queryData = [
  { day: "Mon", queries: 120 },
  { day: "Tue", queries: 180 },
  { day: "Wed", queries: 260 },
  { day: "Thu", queries: 190 },
  { day: "Fri", queries: 310 },
];

const docsData = [
  { month: "Jan", docs: 200 },
  { month: "Feb", docs: 380 },
  { month: "Mar", docs: 540 },
  { month: "Apr", docs: 720 },
];

export default function AnalyticsPage() {
  return (
    <div className="p-10">
      <div className="mb-10">
        <h1 className="text-4xl font-bold">
          Analytics
        </h1>

        <p className="text-slate-500 mt-2">
          Understand how your AI ecosystem performs.
        </p>
      </div>

      {/* KPI ROW */}

      <div className="grid lg:grid-cols-4 gap-6 mb-8">
        {[
          {
            title: "Agents",
            value: "12",
          },
          {
            title: "Documents",
            value: "1,248",
          },
          {
            title: "Queries",
            value: "84,291",
          },
          {
            title: "Embeddings",
            value: "2.4M",
          },
        ].map((item) => (
          <div
            key={item.title}
            className="
            bg-white
            rounded-3xl
            border
            border-slate-200
            p-6
          "
          >
            <div className="text-slate-500">
              {item.title}
            </div>

            <div className="text-4xl font-bold mt-3">
              {item.value}
            </div>
          </div>
        ))}
      </div>

      {/* CHARTS */}

      <div className="grid lg:grid-cols-2 gap-6">
        <div
          className="
          bg-white
          rounded-3xl
          border
          border-slate-200
          p-6
        "
        >
          <h3 className="font-semibold mb-5">
            Queries Per Day
          </h3>

          <ResponsiveContainer
            width="100%"
            height={300}
          >
            <BarChart data={queryData}>
              <XAxis dataKey="day" />
              <Tooltip />
              <Bar
                dataKey="queries"
                fill="#4f46e5"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div
          className="
          bg-white
          rounded-3xl
          border
          border-slate-200
          p-6
        "
        >
          <h3 className="font-semibold mb-5">
            Documents Indexed
          </h3>

          <ResponsiveContainer
            width="100%"
            height={300}
          >
            <AreaChart data={docsData}>
              <XAxis dataKey="month" />
              <Tooltip />

              <Area
                type="monotone"
                dataKey="docs"
                stroke="#4f46e5"
                fill="#c7d2fe"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}