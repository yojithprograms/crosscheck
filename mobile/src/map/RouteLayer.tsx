import { memo, useMemo } from "react";
import { Polyline } from "react-native-maps";

import type { RouteComparison, RouteKind } from "@/api/types";
import { colors } from "@/theme/colors";
import { toLatLng } from "@/utils/geo";

const FASTEST_WIDTH = 5;
const LOWER_RISK_WIDTH = 6;
const FASTEST_DASH = [12, 8];

type Props = { comparison: RouteComparison; selected: RouteKind };

/**
 * The two routes. Lower-risk is a solid blue line and fastest is a gray dashed one, so they differ by
 * more than color. The selected route is drawn last so it sits on top (DESIGN.md §8.6). When the fastest
 * route is also the lower-risk one, only the blue line is drawn.
 */
export const RouteLayer = memo(function RouteLayer({ comparison, selected }: Props) {
  const fastest = useMemo(() => comparison.fastest.polyline.map(toLatLng), [comparison]);
  const lowerRisk = useMemo(() => comparison.lower_risk.polyline.map(toLatLng), [comparison]);

  if (comparison.same_route) {
    return <Polyline coordinates={lowerRisk} strokeColor={colors.routeLower} strokeWidth={LOWER_RISK_WIDTH} />;
  }

  const lines = [
    { kind: "fastest" as const, points: fastest, color: colors.routeFast, width: FASTEST_WIDTH, dash: FASTEST_DASH },
    { kind: "lower_risk" as const, points: lowerRisk, color: colors.routeLower, width: LOWER_RISK_WIDTH, dash: undefined },
  ].sort((a, b) => Number(a.kind === selected) - Number(b.kind === selected)); // the selected line goes last

  return (
    <>
      {lines.map(({ kind, points, color, width, dash }) => (
        <Polyline
          key={kind}
          coordinates={points}
          strokeColor={color}
          strokeWidth={width}
          lineDashPattern={dash}
          lineCap={dash ? "butt" : "round"} // round caps would fill in the gaps between dashes
          zIndex={kind === selected ? 2 : 1}
        />
      ))}
    </>
  );
});
