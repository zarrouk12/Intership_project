/**
 * Graphiques du portefeuille.
 *
 * Palette : imposee par la charte Medicacom (vert #157F5C, teal #1C6B7D, ambre #A66A16).
 * Le couple vert / teal reste sous le seuil de separation chromatique recommande, donc la
 * couleur n'est jamais le seul porteur d'identite : chaque bulle notable est etiquetee
 * directement, la legende est toujours affichee, et le type de solution est repris en
 * toutes lettres dans les tableaux.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

import type { MatrixPoint } from "../api/types";
import { aiTypeColor, formatEuro, formatPercent } from "../lib/format";

const AXIS = { stroke: "#E1E8E4", tick: { fill: "#5E6F67", fontSize: 12 } };

/* ------------------------------------------------------ matrice impact x faisabilite */

interface BubbleDatum extends MatrixPoint {
  radius: number;
  showLabel: boolean;
  shortLabel: string[];
}

const STOPWORDS = new Set([
  "de", "des", "du", "la", "le", "les", "un", "une", "et", "en", "sur", "pour",
  "par", "au", "aux", "dans", "avec", "sans", "sa", "son", "ses",
]);

/** Reduit un titre a deux mots significatifs, assez courts pour tenir dans une bulle. */
function shorten(title: string): string[] {
  const words = title
    .replace(/\s*[-–—]\s*/g, " ")
    .replace(/[’']/g, " ")
    .split(/\s+/)
    .filter((word) => word.length > 1 && !STOPWORDS.has(word.toLowerCase()))
    .slice(0, 2);
  const clip = (value: string) => (value.length > 11 ? `${value.slice(0, 10)}.` : value);
  return words.map(clip);
}

function BubbleTooltip({ active, payload }: { active?: boolean; payload?: { payload: BubbleDatum }[] }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div
      style={{
        background: "#fff",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "10px 13px",
        fontSize: 13,
        maxWidth: 260,
        boxShadow: "0 4px 14px rgba(16,35,28,0.09)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4 }}>{point.title}</div>
      <div style={{ color: "var(--muted)" }}>{point.ai_type_label ?? "Non qualifié"}</div>
      <div style={{ marginTop: 6 }}>
        Impact métier <b>{point.impact}</b> · Faisabilité <b>{point.feasibility}</b>
      </div>
      <div>
        Bénéfice attendu <b>{formatEuro(point.benefit)}</b>
      </div>
    </div>
  );
}

export function ImpactMatrix({ points }: { points: MatrixPoint[] }) {
  if (!points.length) return <div className="state">Aucune opportunité à positionner.</div>;

  const benefits = points.map((p) => p.benefit);
  const min = Math.min(...benefits);
  const max = Math.max(...benefits);
  const span = max - min || 1;

  // Etiquetage direct selectif. On parcourt les opportunites du score de priorite le plus
  // eleve au plus faible - ce sont celles que la direction doit pouvoir nommer d'un coup
  // d'oeil - et on n'etiquette que celles assez eloignees des precedentes, pour qu'aucun
  // libelle n'en recouvre un autre. Les autres restent identifiables au survol.
  const MIN_GAP = 17; // en unites du repere 0-100, soit environ 60 px a l'ecran
  const MAX_LABELS = 5;
  const anchors: { impact: number; feasibility: number }[] = [];
  const labelled = new Set<number>();

  for (const point of [...points].sort((a, b) => b.priority_score - a.priority_score)) {
    if (labelled.size >= MAX_LABELS) break;
    const collides = anchors.some(
      (a) => Math.hypot(a.impact - point.impact, a.feasibility - point.feasibility) < MIN_GAP,
    );
    if (collides) continue;
    anchors.push({ impact: point.impact, feasibility: point.feasibility });
    labelled.add(point.id);
  }

  const data: BubbleDatum[] = points
    .map((p) => ({
      ...p,
      radius: 16 + ((p.benefit - min) / span) * 17,
      showLabel: labelled.has(p.id),
      shortLabel: shorten(p.title),
    }))
    // Les bulles etiquetees sont tracees en dernier : aucun libelle n'est recouvert.
    .sort((a, b) => Number(a.showLabel) - Number(b.showLabel));

  return (
    <div>
      <div style={{ display: "flex", gap: 10 }}>
        <div className="axis-y" style={{ height: 420 }}>
          Impact métier →
        </div>
        <div className="matrix" style={{ flex: 1, height: 420 }}>
          <span className="matrix-label" style={{ top: 14, left: 16 }}>
            Réfléchir
          </span>
          <span className="matrix-label prio" style={{ top: 14, right: 16 }}>
            Prioritaire
          </span>
          <span className="matrix-label" style={{ bottom: 14, left: 16 }}>
            Écarter
          </span>
          <span className="matrix-label" style={{ bottom: 14, right: 16 }}>
            Quick win
          </span>

          <ResponsiveContainer width="100%" height="100%">
            <ScatterChart margin={{ top: 34, right: 34, bottom: 34, left: 34 }}>
              <CartesianGrid stroke="transparent" />
              <XAxis
                type="number"
                dataKey="feasibility"
                domain={[0, 100]}
                hide
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="number"
                dataKey="impact"
                domain={[0, 100]}
                hide
                axisLine={false}
                tickLine={false}
              />
              <ZAxis type="number" dataKey="radius" range={[80, 80]} />
              <ReferenceLine x={50} stroke="#E1E8E4" strokeWidth={1} />
              <ReferenceLine y={50} stroke="#E1E8E4" strokeWidth={1} />
              <Tooltip content={<BubbleTooltip />} cursor={false} />
              <Scatter
                data={data}
                isAnimationActive={false}
                shape={(props: unknown) => {
                  const { cx, cy, payload } = props as {
                    cx: number;
                    cy: number;
                    payload: BubbleDatum;
                  };
                  const color = aiTypeColor(payload.ai_type);
                  const r = payload.radius;
                  return (
                    <g>
                      {/* Anneau blanc : separe les bulles qui se recouvrent */}
                      <circle
                        cx={cx}
                        cy={cy}
                        r={r}
                        fill={color}
                        fillOpacity={0.16}
                        stroke="#FFFFFF"
                        strokeWidth={3.2}
                      />
                      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={1.6} />
                      {payload.showLabel &&
                        payload.shortLabel.map((line, index) => (
                          <text
                            key={line + index}
                            x={cx}
                            y={cy + (index - (payload.shortLabel.length - 1) / 2) * 12 + 4}
                            textAnchor="middle"
                            fontSize={10.8}
                            fontWeight={600}
                            fill="#16241E"
                          >
                            {line}
                          </text>
                        ))}
                    </g>
                  );
                }}
              />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="axis-x">Faisabilité technique →</div>
    </div>
  );
}

export function MatrixLegend({ points }: { points: MatrixPoint[] }) {
  const seen = new Map<string, string>();
  points.forEach((p) => {
    if (p.ai_type && p.ai_type_label && !seen.has(p.ai_type)) seen.set(p.ai_type, p.ai_type_label);
  });
  const entries = [...seen.entries()];
  return (
    <div className="legend">
      {entries.map(([code, label]) => (
        <span className="legend-item" key={code}>
          <span className="legend-dot" style={{ background: aiTypeColor(code) }} />
          {label}
        </span>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------- jauge readiness */

export function ReadinessGauge({ score, max = 100 }: { score: number; max?: number }) {
  const size = 212;
  const stroke = 15;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const ratio = Math.max(0, Math.min(1, score / max));

  return (
    <div className="gauge-wrap">
      <svg width={size} height={size} role="img" aria-label={`Readiness ${Math.round(score)} sur ${max}`}>
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#24493B"
            strokeWidth={stroke}
          />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="#1E9C72"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${circumference * ratio} ${circumference}`}
          />
        </g>
        <text x="50%" y="48%" textAnchor="middle" className="gauge-value">
          {Math.round(score)}
        </text>
        <text x="50%" y="62%" textAnchor="middle" className="gauge-unit">
          / {max}
        </text>
      </svg>
    </div>
  );
}

/* ---------------------------------------------------------- valeur par departement */

export function DepartmentValueChart({
  data,
}: {
  data: { department: string; annual_benefit_eur: number; tco_eur: number }[];
}) {
  if (!data.length) return <div className="state">Aucun business case chiffré.</div>;
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, data.length * 46)}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 58, bottom: 4, left: 4 }}>
        <CartesianGrid horizontal={false} stroke="#EEF3F0" />
        <XAxis type="number" tickFormatter={(v: number) => formatEuro(v)} {...AXIS} />
        <YAxis type="category" dataKey="department" width={156} {...AXIS} />
        <Tooltip
          cursor={{ fill: "rgba(21,127,92,0.05)" }}
          formatter={(value: number) => [formatEuro(value), "Gains annuels"]}
          contentStyle={{ borderRadius: 10, border: "1px solid #E1E8E4", fontSize: 13 }}
        />
        <Bar dataKey="annual_benefit_eur" radius={[0, 4, 4, 0]} barSize={16} fill="#157F5C" />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* --------------------------------------------------------- classement ROI par projet */

export function RoiRankingChart({
  data,
}: {
  data: { title: string; roi_percent: number }[];
}) {
  if (!data.length) return <div className="state">Aucun projet chiffré.</div>;
  const rows = data.slice(0, 8).map((d) => ({
    ...d,
    short: d.title.length > 26 ? `${d.title.slice(0, 25)}…` : d.title,
  }));
  return (
    <ResponsiveContainer width="100%" height={Math.max(220, rows.length * 42)}>
      <BarChart data={rows} layout="vertical" margin={{ top: 4, right: 52, bottom: 4, left: 4 }}>
        <CartesianGrid horizontal={false} stroke="#EEF3F0" />
        <XAxis type="number" tickFormatter={(v: number) => formatPercent(v)} {...AXIS} />
        <YAxis type="category" dataKey="short" width={212} {...AXIS} />
        <Tooltip
          cursor={{ fill: "rgba(21,127,92,0.05)" }}
          formatter={(value: number) => [formatPercent(value, 1), "ROI 3 ans"]}
          contentStyle={{ borderRadius: 10, border: "1px solid #E1E8E4", fontSize: 13 }}
        />
        <Bar dataKey="roi_percent" radius={[0, 4, 4, 0]} barSize={15}>
          {rows.map((row) => (
            <Cell key={row.title} fill={row.roi_percent >= 100 ? "#157F5C" : "#1C6B7D"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
