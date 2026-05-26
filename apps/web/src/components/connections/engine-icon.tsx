// Per-engine SVG glyphs. Keep in sync with ENGINES list in engine-card.tsx.

type IconProps = { size?: number; className?: string };

export function BigQueryIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#4285F4" />
      <path
        d="M16 5L25 10.5V21.5L16 27L7 21.5V10.5L16 5Z"
        fill="white"
        fillOpacity="0.95"
      />
      <path
        d="M10 16H22M10 19.5H22M10 12.5H22"
        stroke="#4285F4"
        strokeWidth="1.8"
        strokeLinecap="square"
      />
      <circle cx="22" cy="22" r="4.5" fill="#34A853" />
      <path d="M21 24.5L23.5 22L21 24.5Z" stroke="white" strokeWidth="1.5" strokeLinecap="square" />
      <circle cx="22" cy="22" r="2.2" fill="none" stroke="white" strokeWidth="1.4" />
      <line x1="23.5" y1="23.5" x2="25.5" y2="25.5" stroke="white" strokeWidth="1.5" strokeLinecap="square" />
    </svg>
  );
}

export function PostgreSQLIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#336791" />
      {/* Simplified Slonik elephant */}
      <ellipse cx="15" cy="15" rx="7" ry="8" fill="white" fillOpacity="0.9" />
      <ellipse cx="22" cy="12" rx="3" ry="4" fill="white" fillOpacity="0.9" />
      {/* Trunk */}
      <path d="M8 17C6 18 5 21 7 23" stroke="white" strokeWidth="2" strokeLinecap="round" fill="none" />
      {/* Eye */}
      <circle cx="17" cy="13" r="1" fill="#336791" />
      {/* Tusk */}
      <path d="M10 20L8 23" stroke="white" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function MySQLIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#00758F" />
      {/* Dolphin silhouette */}
      <path
        d="M6 18C6 13 10 8 16 8C21 8 25 11 26 15C26 17 25 19 23 20C21 21 20 20 20 18C20 16 22 15 22 13C22 11 20 10 18 10C14 10 10 14 10 18C10 21 12 24 16 25C18 25.5 20 25 21 24"
        stroke="white"
        strokeWidth="1.8"
        strokeLinecap="round"
        fill="none"
      />
      {/* Tail */}
      <path d="M22 23L25 26M22 23L25 21" stroke="white" strokeWidth="1.8" strokeLinecap="round" />
      {/* Eye */}
      <circle cx="17" cy="13" r="1.2" fill="white" />
    </svg>
  );
}

export function SnowflakeIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#29B5E8" />
      {/* Central cross */}
      <line x1="16" y1="5" x2="16" y2="27" stroke="white" strokeWidth="2.5" strokeLinecap="square" />
      <line x1="5" y1="16" x2="27" y2="16" stroke="white" strokeWidth="2.5" strokeLinecap="square" />
      {/* Diagonal arms */}
      <line x1="8.5" y1="8.5" x2="23.5" y2="23.5" stroke="white" strokeWidth="2.5" strokeLinecap="square" />
      <line x1="23.5" y1="8.5" x2="8.5" y2="23.5" stroke="white" strokeWidth="2.5" strokeLinecap="square" />
      {/* End diamonds */}
      {[[16,5],[16,27],[5,16],[27,16],[8.5,8.5],[23.5,23.5],[8.5,23.5],[23.5,8.5]].map(([cx,cy], i) => (
        <circle key={i} cx={cx} cy={cy} r="1.8" fill="#29B5E8" stroke="white" strokeWidth="1.2" />
      ))}
    </svg>
  );
}

export function ClickHouseIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#1C1C1C" />
      {/* Three vertical bars — actual ClickHouse logo */}
      <rect x="5" y="8" width="5" height="16" fill="#FACC15" />
      <rect x="13.5" y="8" width="5" height="16" fill="#FACC15" />
      <rect x="22" y="8" width="5" height="8" fill="#FACC15" />
    </svg>
  );
}

export function RedshiftIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#8C4FFF" />
      {/* AWS Redshift - cylinder / stacked discs */}
      <ellipse cx="16" cy="10" rx="9" ry="3" fill="white" fillOpacity="0.9" />
      <rect x="7" y="10" width="18" height="12" fill="white" fillOpacity="0.75" />
      <ellipse cx="16" cy="22" rx="9" ry="3" fill="white" fillOpacity="0.9" />
      {/* Center line */}
      <line x1="7" y1="16" x2="25" y2="16" stroke="#8C4FFF" strokeWidth="1" />
    </svg>
  );
}

export function DatabricksIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#FF3621" />
      {/* Delta / spark logo */}
      <path d="M16 5L26 21H6L16 5Z" fill="white" fillOpacity="0.95" />
      <path d="M16 11L22 21H10L16 11Z" fill="#FF3621" />
      <line x1="7" y1="25" x2="25" y2="25" stroke="white" strokeWidth="2.5" strokeLinecap="square" />
    </svg>
  );
}

export function DuckDBIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#FCD34D" />
      {/* Simple duck */}
      <ellipse cx="16" cy="19" rx="8" ry="7" fill="white" />
      {/* Head */}
      <circle cx="22" cy="12" r="5" fill="white" />
      {/* Bill */}
      <path d="M26 12L29 12L27 14Z" fill="#F59E0B" />
      {/* Eye */}
      <circle cx="23.5" cy="11" r="1" fill="#1C1C1C" />
      {/* Wing */}
      <path d="M10 18C10 15 13 13 16 14" stroke="#FCD34D" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

export function TrinoIcon({ size = 32, className }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill="#DD00A1" />
      {/* Trino T */}
      <line x1="7" y1="9" x2="25" y2="9" stroke="white" strokeWidth="3.5" strokeLinecap="square" />
      <line x1="16" y1="9" x2="16" y2="24" stroke="white" strokeWidth="3.5" strokeLinecap="square" />
    </svg>
  );
}

export function GenericEngineIcon({ initial, color, size = 32, className }: IconProps & { initial: string; color: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none" className={className}>
      <rect width="32" height="32" fill={color} />
      <text
        x="16" y="21"
        textAnchor="middle"
        fill="white"
        fontSize="13"
        fontWeight="500"
        fontFamily="monospace"
      >
        {initial}
      </text>
    </svg>
  );
}

const ICON_MAP: Record<string, (props: IconProps) => JSX.Element> = {
  bigquery: BigQueryIcon,
  postgres: PostgreSQLIcon,
  postgresql: PostgreSQLIcon,
  mysql: MySQLIcon,
  snowflake: SnowflakeIcon,
  clickhouse: ClickHouseIcon,
  redshift: RedshiftIcon,
  databricks: DatabricksIcon,
  duckdb: DuckDBIcon,
  trino: TrinoIcon,
};

const FALLBACK_COLORS: Record<string, string> = {
  bigquery: "#4285F4",
  postgres: "#336791",
  postgresql: "#336791",
  mysql: "#00758F",
  snowflake: "#29B5E8",
  clickhouse: "#1C1C1C",
  redshift: "#8C4FFF",
  databricks: "#FF3621",
  duckdb: "#FCD34D",
  trino: "#DD00A1",
};

export function EngineIcon({ engine, size = 32, className }: { engine: string; size?: number; className?: string }) {
  const key = engine.toLowerCase();
  const Icon = ICON_MAP[key];
  if (Icon) return <Icon size={size} className={className} />;
  const color = FALLBACK_COLORS[key] ?? "#555";
  const initial = engine.slice(0, 2).toUpperCase();
  return <GenericEngineIcon initial={initial} color={color} size={size} className={className} />;
}
